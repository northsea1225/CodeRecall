from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
import json
import logging
import time

from app.core.config import Settings, settings
from app.services.prompt_templates import SYSTEM_PROMPT, MistakePromptInput, build_user_prompt, build_variant_prompt


logger = logging.getLogger(__name__)

_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


def _review_result_value(result: object) -> str:
    if hasattr(result, "value"):
        return str(result.value).lower()
    return str(result).lower()


def _normalize_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _review_sort_key(log: object) -> datetime:
    for attr in ("answered_at", "shown_at"):
        dt = _normalize_dt(getattr(log, attr, None))
        if dt is not None:
            return dt
    return _MIN_DT


def _latest_reviewed_at(mistake: object, latest_log: object | None) -> datetime | None:
    candidates: list[datetime] = []
    stored = _normalize_dt(getattr(mistake, "last_reviewed_at", None))
    if stored is not None:
        candidates.append(stored)
    if latest_log is not None:
        log_dt = _review_sort_key(latest_log)
        if log_dt is not _MIN_DT:
            candidates.append(log_dt)
    return max(candidates) if candidates else None


def build_mistake_prompt_input(mistake: object) -> MistakePromptInput:
    category = getattr(mistake, "category", None)
    tags = getattr(mistake, "tags", None) or []
    review_logs = list(getattr(mistake, "review_logs", None) or [])
    review_logs.sort(key=_review_sort_key, reverse=True)

    stored_count = int(getattr(mistake, "review_count", 0) or 0)
    review_count = max(stored_count, len(review_logs))

    recent_results = [
        _review_result_value(getattr(log, "user_result"))
        for log in review_logs[:3]
        if getattr(log, "user_result", None) is not None
    ]

    recent_notes = [
        str(getattr(log, "note"))
        for log in review_logs[:2]
        if getattr(log, "note", None)
    ]

    latest_log = review_logs[0] if review_logs else None

    return {
        "title": getattr(mistake, "title"),
        "language": getattr(mistake, "language"),
        "difficulty": getattr(mistake, "difficulty"),
        "category_name": category.name if category else "未分类",
        "tag_names": [tag.name for tag in tags],
        "stem": getattr(mistake, "stem_markdown"),
        "wrong": getattr(mistake, "wrong_answer_markdown"),
        "correct": getattr(mistake, "correct_answer_markdown"),
        "reason": getattr(mistake, "error_reason_markdown"),
        "review_count": review_count,
        "last_review_result": recent_results[0] if recent_results else None,
        "recent_review_results": recent_results,
        "recent_review_notes": recent_notes,
        "last_reviewed_at": _latest_reviewed_at(mistake, latest_log),
    }


def resolve_model(requested: str | None, app_settings: Settings | None = None) -> str:
    s = app_settings or settings
    base = (requested or s.llm_model).strip()
    allowed_raw = s.llm_allowed_models.strip()
    if not allowed_raw:
        return base
    allowed = {m.strip() for m in allowed_raw.split(",") if m.strip()}
    if base not in allowed:
        raise AiAnalysisError(
            "ai_model_not_allowed",
            f"Model '{base}' is not in the allowed list.",
            400,
        )
    return base


def get_ai_capability() -> dict[str, str | bool | None]:
    enabled = settings.enable_ai_analysis and bool(settings.llm_api_key.strip())
    model = settings.llm_model.strip() or None
    return {
        "enabled": enabled,
        "model": model,
    }


class AiAnalysisProvider:
    def __init__(self, app_settings: Settings) -> None:
        self.settings = app_settings

    async def analyze_stream(self, mistake: object, *, model: str | None = None) -> AsyncIterator[str]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - environment/setup issue
            raise AiAnalysisError(
                code="ai_dependency_missing",
                message="AI analysis dependency is missing.",
                status_code=500,
            ) from exc

        api_key = self.settings.llm_api_key.strip()
        resolved_model = resolve_model(model, self.settings)
        if not resolved_model:
            raise AiAnalysisError("ai_model_not_configured", "No AI model configured.", 500)
        if not api_key:
            raise AiAnalysisError("ai_auth_failed", "AI API key is missing.", 401)

        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(build_mistake_prompt_input(mistake))},
            ],
            "stream": True,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        started_at = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code >= 400:
                        response_text = await response.aread()
                        raise map_ai_http_error(response.status_code, response_text.decode("utf-8", errors="ignore"))

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue

                        chunk = line.removeprefix("data:").strip()
                        if chunk == "[DONE]":
                            break

                        try:
                            data = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices") or []
                        if not choices:
                            continue

                        delta = choices[0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield content
        except AiAnalysisError:
            raise
        except httpx.TimeoutException as exc:
            raise AiAnalysisError("ai_timeout", "AI request timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise AiAnalysisError("ai_service_unavailable", "AI service is unavailable.", 503) from exc
        finally:
            duration = time.perf_counter() - started_at
            logger.info(
                "ai_analysis_stream_finished mistake_id=%s model=%s duration_seconds=%.2f",
                getattr(mistake, "id", "unknown"),
                resolved_model,
                duration,
            )

    async def generate_variant(self, mistake: object, *, model: str | None = None) -> dict[str, str]:
        try:
            import httpx
        except ImportError as exc:
            raise AiAnalysisError("ai_dependency_missing", "AI analysis dependency is missing.", 500) from exc

        api_key = self.settings.llm_api_key.strip()
        resolved_model = resolve_model(model, self.settings)
        if not resolved_model:
            raise AiAnalysisError("ai_model_not_configured", "No AI model configured.", 500)
        if not api_key:
            raise AiAnalysisError("ai_auth_failed", "AI API key is missing.", 401)

        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        prompt_input = build_mistake_prompt_input(mistake)
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": "你是一位 OI/ACM 竞赛题目出题专家，擅长设计变体题。只输出合法 JSON，不输出任何其他内容。"},
                {"role": "user", "content": build_variant_prompt(prompt_input)},
            ],
            "stream": False,
            "max_tokens": 4096,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code >= 400:
                    raise map_ai_http_error(response.status_code, response.text)
                data = response.json()
                content: str = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    lines = content.splitlines()
                    end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                    content = "\n".join(lines[1:end])
                return json.loads(content)
        except AiAnalysisError:
            raise
        except json.JSONDecodeError as exc:
            raise AiAnalysisError("ai_invalid_response", "AI returned invalid JSON.", 502) from exc
        except httpx.TimeoutException as exc:
            raise AiAnalysisError("ai_timeout", "AI request timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise AiAnalysisError("ai_service_unavailable", "AI service is unavailable.", 503) from exc


    async def generate_correct_answer(
        self,
        *,
        stem_markdown: str,
        language: str,
        model: str | None = None,
    ) -> str:
        """Inline AI generation of a correct-answer code block for a new mistake.

        Returns a markdown string. Designed for the MistakeEditor "AI 生成答案"
        button: the editor has not persisted a mistake yet, so we can't reuse
        analyze_stream / generate_variant (both require a Mistake row).
        """
        try:
            import httpx
        except ImportError as exc:
            raise AiAnalysisError("ai_dependency_missing", "AI analysis dependency is missing.", 500) from exc

        api_key = self.settings.llm_api_key.strip()
        resolved_model = resolve_model(model, self.settings)
        if not resolved_model:
            raise AiAnalysisError("ai_model_not_configured", "No AI model configured.", 500)
        if not api_key:
            raise AiAnalysisError("ai_auth_failed", "AI API key is missing.", 401)

        normalized_stem = (stem_markdown or "").strip()
        normalized_language = (language or "").strip() or "cpp"
        if not normalized_stem:
            raise AiAnalysisError("ai_invalid_input", "Stem is empty.", 422)

        # Escape the stem so a stem containing literal backticks or XML doesn't
        # break the prompt envelope. The model sees the raw text inside CDATA-ish
        # delimiters so it can't be confused about where the problem ends.
        safe_stem = normalized_stem.replace("</PROBLEM_STEM>", "</ PROBLEM_STEM>")
        system_prompt = (
            "你是一位高级算法竞赛工程师，擅长用多种编程语言写出简洁、可编译、可 AC 的标准解答。"
            "仅返回代码，不解释、不复述题目、不要测试用例。"
        )
        user_prompt = (
            f"下面是一道编程题，请用 **{normalized_language}** 语言给出 AC 标准解答。\n\n"
            f"<PROBLEM_STEM>\n{safe_stem}\n</PROBLEM_STEM>\n\n"
            f"要求：\n"
            f"1. 仅返回代码块（用 ``` 包裹并标注语言 `{normalized_language}`），代码块外不要任何文本。\n"
            f"2. 代码必须可编译/可运行，含必要的 include / import。\n"
            f"3. 风格简洁，仅在关键步骤加 1-2 行行内注释。\n"
            f"4. 不要打印多余调试信息，不要测试 main，除非题目要求。\n"
        )

        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "max_tokens": 4096,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        started_at = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code >= 400:
                    raise map_ai_http_error(response.status_code, response.text)
                data = response.json()
                content: str = data["choices"][0]["message"]["content"].strip()
                # Some models wrap the code block with surrounding prose despite
                # the instruction. Extract the first fenced block defensively.
                fence_start = content.find("```")
                if fence_start >= 0:
                    after = content[fence_start:]
                    # Strip optional opening language tag.
                    lines = after.splitlines()
                    if lines[0].strip().startswith("```"):
                        lines = lines[1:]
                    fence_end_idx = None
                    for i, line in enumerate(lines):
                        if line.strip().startswith("```"):
                            fence_end_idx = i
                            break
                    code_body = "\n".join(lines[:fence_end_idx]) if fence_end_idx is not None else "\n".join(lines)
                    return f"```{normalized_language}\n{code_body.rstrip()}\n```"
                # No fence found — wrap the whole reply.
                return f"```{normalized_language}\n{content}\n```"
        except AiAnalysisError:
            raise
        except httpx.TimeoutException as exc:
            raise AiAnalysisError("ai_timeout", "AI request timed out.", 504) from exc
        except httpx.HTTPError as exc:
            raise AiAnalysisError("ai_service_unavailable", "AI service is unavailable.", 503) from exc
        finally:
            duration = time.perf_counter() - started_at
            logger.info(
                "ai_generate_correct_answer_finished language=%s model=%s duration_seconds=%.2f",
                normalized_language,
                resolved_model,
                duration,
            )


def build_provider(app_settings: Settings | None = None) -> AiAnalysisProvider:
    return AiAnalysisProvider(app_settings or settings)


class AiAnalysisError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def map_ai_http_error(status_code: int, _: str = "") -> AiAnalysisError:
    if status_code == 401:
        return AiAnalysisError("ai_auth_failed", "AI authentication failed.", 401)
    if status_code in {402, 429}:
        return AiAnalysisError("ai_quota_or_rate_limit", "AI quota exceeded or rate limited.", status_code)
    if status_code in {408, 504}:
        return AiAnalysisError("ai_timeout", "AI request timed out.", status_code)
    if status_code >= 500:
        return AiAnalysisError("ai_service_unavailable", "AI service is unavailable.", status_code)
    return AiAnalysisError("ai_service_unavailable", "AI request failed.", status_code)
