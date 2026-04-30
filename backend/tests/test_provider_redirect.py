from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import patch

from app.services.problem_import_service import fetch_problem_preview
from app.services.providers.base import ProblemImportError, safe_request


class _Resp:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class _ScriptedClient:
    def __init__(self, scripts: list[_Resp]) -> None:
        self._scripts = list(scripts)
        self.calls: list[tuple[str, str]] = []

    async def __aenter__(self) -> "_ScriptedClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def request(self, method: str, url: str, **kwargs: Any) -> _Resp:
        self.calls.append((method.upper(), url))
        if not self._scripts:
            raise AssertionError("No more scripted responses")
        return self._scripts.pop(0)


def _patch_client(client: _ScriptedClient):
    return patch(
        "app.services.problem_import_service.httpx.AsyncClient",
        lambda *args, **kwargs: client,
    )


class CrossHostRedirectBlockedTests(unittest.TestCase):
    def test_codeforces_redirect_to_evil_host_blocked(self) -> None:
        client = _ScriptedClient(
            [_Resp(302, {"location": "https://evil.example.com/x"})]
        )
        with _patch_client(client):
            with self.assertRaises(ProblemImportError) as ctx:
                asyncio.run(
                    fetch_problem_preview(
                        "https://codeforces.com/problemset/problem/1/A"
                    )
                )
        self.assertEqual(ctx.exception.code, "redirect_blocked")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_redirect_to_localhost_blocked(self) -> None:
        client = _ScriptedClient(
            [_Resp(302, {"location": "http://127.0.0.1:8000/admin"})]
        )
        with _patch_client(client):
            with self.assertRaises(ProblemImportError) as ctx:
                asyncio.run(
                    fetch_problem_preview(
                        "https://codeforces.com/problemset/problem/1/A"
                    )
                )
        self.assertEqual(ctx.exception.code, "redirect_blocked")

    def test_redirect_to_non_http_scheme_blocked(self) -> None:
        client = _ScriptedClient(
            [_Resp(302, {"location": "file:///etc/passwd"})]
        )
        with _patch_client(client):
            with self.assertRaises(ProblemImportError) as ctx:
                asyncio.run(
                    fetch_problem_preview(
                        "https://codeforces.com/problemset/problem/1/A"
                    )
                )
        self.assertEqual(ctx.exception.code, "redirect_blocked")


class SameHostRedirectAllowedTests(unittest.TestCase):
    def test_same_host_trailing_slash_redirect_followed(self) -> None:
        problem_html = """
        <html><body>
          <div class="problem-statement">
            <div class="title">A. Watermelon</div>
            <p>Statement body.</p>
          </div>
        </body></html>
        """
        client = _ScriptedClient(
            [
                _Resp(302, {"location": "https://codeforces.com/problemset/problem/1/A/"}),
                _Resp(200, text=problem_html),
            ]
        )
        with _patch_client(client):
            response = asyncio.run(
                fetch_problem_preview("https://codeforces.com/problemset/problem/1/A")
            )
        self.assertEqual(response.provider, "codeforces")
        self.assertEqual(response.external_id, "1A")
        self.assertEqual(len(client.calls), 2)

    def test_www_prefixed_host_treated_as_same(self) -> None:
        problem_html = (
            '<html><body><div class="problem-statement">'
            '<div class="title">A. T</div><p>x</p></div></body></html>'
        )
        client = _ScriptedClient(
            [
                _Resp(301, {"location": "https://www.codeforces.com/problemset/problem/1/A/"}),
                _Resp(200, text=problem_html),
            ]
        )
        with _patch_client(client):
            response = asyncio.run(
                fetch_problem_preview("https://codeforces.com/problemset/problem/1/A")
            )
        self.assertEqual(response.provider, "codeforces")


class TooManyRedirectsTests(unittest.TestCase):
    def test_chain_exceeds_max_redirects(self) -> None:
        chain = [
            _Resp(302, {"location": f"https://codeforces.com/problemset/problem/1/A?step={i}"})
            for i in range(5)
        ]
        client = _ScriptedClient(chain)
        with _patch_client(client):
            with self.assertRaises(ProblemImportError) as ctx:
                asyncio.run(
                    fetch_problem_preview(
                        "https://codeforces.com/problemset/problem/1/A"
                    )
                )
        self.assertEqual(ctx.exception.code, "too_many_redirects")


class SafeRequestUnitTests(unittest.TestCase):
    def test_returns_immediately_on_2xx(self) -> None:
        client = _ScriptedClient([_Resp(200, text="ok")])
        result = asyncio.run(
            safe_request(client, "GET", "https://codeforces.com/x")
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(client.calls, [("GET", "https://codeforces.com/x")])

    def test_no_location_header_returns_redirect_response(self) -> None:
        client = _ScriptedClient([_Resp(302, headers={})])
        result = asyncio.run(
            safe_request(client, "GET", "https://codeforces.com/x")
        )
        self.assertEqual(result.status_code, 302)
