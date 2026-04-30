from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
import markdownify as md_converter

from app.schemas.problem_import import ProblemUrlPreviewResponse
from app.services.providers.base import ProblemImportError, safe_request


_DIFFICULTY_MAP = {"Easy": 1, "Medium": 3, "Hard": 5}

_LEETCODE_GRAPHQL = "https://leetcode.com/graphql/"
_LEETCODE_CN_GRAPHQL = "https://leetcode.cn/graphql/"

_GQL_QUERY = (
    "query questionData($titleSlug: String!) {"
    "  question(titleSlug: $titleSlug) {"
    "    questionFrontendId title titleSlug difficulty content isPaidOnly"
    "    topicTags { name }"
    "  }"
    "}"
)


def _parse_leetcode_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in {"leetcode.com", "leetcode.cn"}:
        raise ProblemImportError("invalid_url", "URL must be a LeetCode problem link.", 400)
    match = re.search(r"/problems/([a-z0-9-]+)", parsed.path)
    if not match:
        raise ProblemImportError("invalid_url", "Could not extract problem slug from URL.", 400)
    slug = match.group(1)
    graphql_url = _LEETCODE_CN_GRAPHQL if host == "leetcode.cn" else _LEETCODE_GRAPHQL
    return slug, graphql_url


def _html_to_markdown(html: str) -> str:
    return md_converter.markdownify(html, heading_style="ATX").strip()


async def fetch_preview(url: str, client: httpx.AsyncClient) -> ProblemUrlPreviewResponse:
    slug, graphql_url = _parse_leetcode_url(url)
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; CodeRecall/1.0)",
        "Referer": f"https://{host}/problems/{slug}/",
    }
    payload = {
        "operationName": "questionData",
        "variables": {"titleSlug": slug},
        "query": _GQL_QUERY,
    }

    try:
        response = await safe_request(
            client, "POST", graphql_url, headers=headers, json=payload
        )
        if response.status_code >= 400:
            raise ProblemImportError("provider_forbidden", "LeetCode returned an error.", 502)
        data = response.json()
    except ProblemImportError:
        raise
    except httpx.TimeoutException as exc:
        raise ProblemImportError("provider_timeout", "LeetCode request timed out.", 504) from exc
    except httpx.HTTPError as exc:
        raise ProblemImportError("provider_unavailable", "Could not reach LeetCode.", 502) from exc
    except ValueError as exc:
        raise ProblemImportError("parse_failed", "Could not parse LeetCode response.", 502) from exc

    question = (data.get("data") or {}).get("question")
    if not question:
        raise ProblemImportError("problem_not_found", "Problem not found on LeetCode.", 404)
    if question.get("isPaidOnly"):
        raise ProblemImportError("premium_required", "This is a Premium problem and cannot be imported.", 423)

    content = question.get("content") or ""
    if not content:
        raise ProblemImportError("parse_failed", "Problem content is empty.", 502)

    stem_markdown = _html_to_markdown(content)
    difficulty_raw = question.get("difficulty") or "Medium"
    difficulty = _DIFFICULTY_MAP.get(difficulty_raw, 3)
    tags = [t["name"] for t in (question.get("topicTags") or [])]

    return ProblemUrlPreviewResponse(
        provider="leetcode",
        source_url=url,
        external_id=str(question.get("questionFrontendId") or ""),
        title=question.get("title") or "",
        difficulty_raw=difficulty_raw,
        difficulty=difficulty,
        tags=tags,
        stem_markdown=stem_markdown,
        warnings=[],
    )
