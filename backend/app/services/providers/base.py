from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx

from app.schemas.problem_import import ProblemUrlPreviewResponse


class ProblemImportError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProblemPreviewProvider(Protocol):
    async def fetch_preview(
        self, url: str, client: httpx.AsyncClient
    ) -> ProblemUrlPreviewResponse: ...


ALLOWED_REDIRECT_HOSTS: frozenset[str] = frozenset(
    {
        "leetcode.com",
        "leetcode.cn",
        "codeforces.com",
    }
)


_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def _normalise_host(netloc: str) -> str:
    return netloc.lower().split("@")[-1].split(":")[0].removeprefix("www.")


async def safe_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_redirects: int = 3,
    **kwargs: Any,
) -> httpx.Response:
    """Issue an HTTP request that only follows redirects to allow-listed hosts.

    Per RFC 7231: 303 forces a GET on the next hop; 307/308 preserve method+body;
    301/302 historically degrade POST→GET (we follow that legacy behaviour).
    Any redirect to a host outside ALLOWED_REDIRECT_HOSTS raises redirect_blocked.
    """
    current_method = method.upper()
    current_url = url
    current_kwargs = dict(kwargs)

    for _ in range(max_redirects + 1):
        response = await client.request(current_method, current_url, **current_kwargs)
        if response.status_code not in _REDIRECT_STATUSES:
            return response

        location = response.headers.get("location")
        if not location:
            return response

        next_url = urljoin(current_url, location)
        parsed = urlparse(next_url)
        if parsed.scheme not in {"http", "https"}:
            raise ProblemImportError(
                "redirect_blocked",
                "Redirect to non-http(s) scheme is not allowed.",
                400,
            )
        if _normalise_host(parsed.netloc) not in ALLOWED_REDIRECT_HOSTS:
            raise ProblemImportError(
                "redirect_blocked",
                f"Redirect to {parsed.hostname} is not in the allow-list.",
                400,
            )

        if response.status_code == 303 or (
            response.status_code in {301, 302} and current_method == "POST"
        ):
            current_method = "GET"
            current_kwargs.pop("json", None)
            current_kwargs.pop("data", None)
            current_kwargs.pop("content", None)
            current_kwargs.pop("files", None)
        current_url = next_url

    raise ProblemImportError(
        "too_many_redirects",
        f"Too many redirects (>{max_redirects}).",
        400,
    )
