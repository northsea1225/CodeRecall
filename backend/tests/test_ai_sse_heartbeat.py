from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from app.api.routes.ai import analyze_stream_route


class _FakeDBSession:
    def __init__(self, mistake: object) -> None:
        self._mistake = mistake

    def scalar(self, _query: object) -> object:
        return self._mistake


class _SilentProvider:
    async def analyze_stream(self, mistake: object, *, model: str | None = None):
        await asyncio.sleep(30)
        if False:
            yield mistake, model


def test_ai_stream_emits_keepalive_comment_when_provider_is_silent() -> None:
    async def run_test() -> None:
        fake_db = _FakeDBSession(SimpleNamespace(id=1))

        with (
            patch("app.api.routes.ai.SSE_KEEPALIVE_SECONDS", 0.01),
            patch("app.api.routes.ai.get_ai_capability", return_value={"enabled": True, "model": "mock-model"}),
            patch("app.api.routes.ai.build_provider", return_value=_SilentProvider()),
        ):
            response = await analyze_stream_route(mistake_id=1, db=fake_db)
            chunks: list[str] = []
            try:
                async for chunk in response.body_iterator:
                    text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                    chunks.append(text)
                    if ": keepalive\n\n" in text:
                        break
            finally:
                if hasattr(response.body_iterator, "aclose"):
                    await response.body_iterator.aclose()

            assert any(": keepalive\n\n" in chunk for chunk in chunks)

    asyncio.run(run_test())
