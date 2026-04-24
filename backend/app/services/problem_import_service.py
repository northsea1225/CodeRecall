from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.schemas.problem_import import ProblemUrlPreviewResponse
from app.services.providers import codeforces, leetcode
from app.services.providers.base import ProblemImportError, ProblemPreviewProvider


_PROVIDERS_BY_HOST: dict[str, ProblemPreviewProvider] = {
    "leetcode.com": leetcode,
    "leetcode.cn": leetcode,
    "codeforces.com": codeforces,
}


async def fetch_problem_preview(url: str) -> ProblemUrlPreviewResponse:
    stripped = url.strip()
    parsed = urlparse(stripped)
    if parsed.scheme not in {"http", "https"}:
        raise ProblemImportError("invalid_url", "Invalid URL scheme.", 400)

    host = parsed.netloc.lower().removeprefix("www.")
    provider = _PROVIDERS_BY_HOST.get(host)
    if provider is None:
        raise ProblemImportError("invalid_url", "Only LeetCode and Codeforces URLs are supported.", 400)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=True,
    ) as client:
        return await provider.fetch_preview(stripped, client)
