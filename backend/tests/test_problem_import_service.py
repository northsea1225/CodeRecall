from __future__ import annotations

import asyncio
import unittest
from typing import Any, Optional
from unittest.mock import patch

import httpx

from app.services.problem_import_service import fetch_problem_preview
from app.services.providers.base import ProblemImportError


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        json_data: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self._json_data = json_data or {}

    def json(self) -> dict[str, Any]:
        return self._json_data


class FakeAsyncClient:
    instance: "FakeAsyncClient"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.get_response = FakeResponse()
        self.post_response = FakeResponse()
        self.get_exception: Optional[Exception] = None
        self.post_exception: Optional[Exception] = None
        self.get_calls: list[dict[str, Any]] = []
        self.post_calls: list[dict[str, Any]] = []
        FakeAsyncClient.instance = self

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, "kwargs": kwargs})
        if self.get_exception is not None:
            raise self.get_exception
        return self.get_response

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.post_calls.append({"url": url, "kwargs": kwargs})
        if self.post_exception is not None:
            raise self.post_exception
        return self.post_response

    async def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        method_upper = method.upper()
        if method_upper == "GET":
            return await self.get(url, **kwargs)
        if method_upper == "POST":
            return await self.post(url, **kwargs)
        raise NotImplementedError(f"FakeAsyncClient.request unsupported method: {method}")


class ProblemImportServiceTests(unittest.TestCase):
    def _run_with_client(self, url: str, configure: Optional[Any] = None):
        with patch("app.services.problem_import_service.httpx.AsyncClient", FakeAsyncClient):
            if configure is not None:
                original_init = FakeAsyncClient.__init__

                def configured_init(client_self: FakeAsyncClient, *args: Any, **kwargs: Any) -> None:
                    original_init(client_self, *args, **kwargs)
                    configure(client_self)

                with patch.object(FakeAsyncClient, "__init__", configured_init):
                    return asyncio.run(fetch_problem_preview(url)), FakeAsyncClient.instance

            return asyncio.run(fetch_problem_preview(url)), FakeAsyncClient.instance

    def test_leetcode_success_dispatches_provider_and_returns_preview(self) -> None:
        def configure(client: FakeAsyncClient) -> None:
            client.post_response = FakeResponse(
                json_data={
                    "data": {
                        "question": {
                            "questionFrontendId": "1",
                            "title": "Two Sum",
                            "difficulty": "Easy",
                            "content": "<p>Find two numbers.</p>",
                            "isPaidOnly": False,
                            "topicTags": [{"name": "Array"}, {"name": "Hash Table"}],
                        }
                    }
                }
            )

        preview, client = self._run_with_client("https://leetcode.com/problems/two-sum/", configure)

        self.assertEqual(preview.provider, "leetcode")
        self.assertEqual(preview.external_id, "1")
        self.assertEqual(preview.title, "Two Sum")
        self.assertEqual(preview.difficulty, 1)
        self.assertIn("Find two numbers", preview.stem_markdown)
        self.assertEqual(preview.tags, ["Array", "Hash Table"])
        self.assertEqual(client.post_calls[0]["url"], "https://leetcode.com/graphql/")

    def test_codeforces_problemset_success_with_mathjax(self) -> None:
        html = """
        <html>
          <body>
            <div class="problem-statement">
              <div class="header"><div class="title">A. Watermelon</div></div>
              <p>Given <script type="math/tex">n</script>.</p>
              <p><script type="math/tex; mode=display">a+b=c</script></p>
            </div>
            <span class="tag-box">math</span>
            <span class="tag-box">implementation</span>
            <span class="tag-box">*800</span>
          </body>
        </html>
        """

        def configure(client: FakeAsyncClient) -> None:
            client.get_response = FakeResponse(text=html)

        preview, client = self._run_with_client(
            "https://codeforces.com/problemset/problem/1234/A",
            configure,
        )

        self.assertEqual(preview.provider, "codeforces")
        self.assertEqual(preview.source_url, "Codeforces 1234A")
        self.assertEqual(preview.external_id, "1234A")
        self.assertEqual(preview.difficulty, 1)
        self.assertEqual(preview.tags, ["math", "implementation"])
        self.assertIn("$n$", preview.stem_markdown)
        self.assertIn("$$a+b=c$$", preview.stem_markdown)
        self.assertEqual(client.get_calls[0]["url"], "https://codeforces.com/problemset/problem/1234/A")

    def test_codeforces_contest_success_maps_1600_to_difficulty_3(self) -> None:
        html = """
        <div class="problem-statement">
          <div class="header"><div class="title">B. Queue</div></div>
          <p>Statement</p>
        </div>
        <span class="tag-box">data structures</span>
        <span class="tag-box">*1600</span>
        """

        def configure(client: FakeAsyncClient) -> None:
            client.get_response = FakeResponse(text=html)

        preview, _client = self._run_with_client(
            "https://codeforces.com/contest/1234/problem/b",
            configure,
        )

        self.assertEqual(preview.external_id, "1234B")
        self.assertEqual(preview.difficulty_raw, "1600")
        self.assertEqual(preview.difficulty, 3)

    def test_codeforces_gym_403_returns_warning_response(self) -> None:
        def configure(client: FakeAsyncClient) -> None:
            client.get_response = FakeResponse(status_code=403)

        preview, _client = self._run_with_client(
            "https://codeforces.com/gym/123456/problem/A",
            configure,
        )

        self.assertEqual(preview.provider, "codeforces")
        self.assertEqual(preview.source_url, "Codeforces Gym123456A")
        self.assertEqual(preview.external_id, "gym123456A")
        self.assertEqual(preview.stem_markdown, "")
        self.assertTrue(preview.warnings)

    def test_codeforces_404_raises_problem_not_found(self) -> None:
        def configure(client: FakeAsyncClient) -> None:
            client.get_response = FakeResponse(status_code=404)

        with self.assertRaises(ProblemImportError) as ctx:
            self._run_with_client("https://codeforces.com/problemset/problem/1234/A", configure)

        self.assertEqual(ctx.exception.code, "problem_not_found")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_codeforces_timeout_raises_provider_timeout(self) -> None:
        def configure(client: FakeAsyncClient) -> None:
            client.get_exception = httpx.TimeoutException("timeout")

        with self.assertRaises(ProblemImportError) as ctx:
            self._run_with_client("https://codeforces.com/contest/1234/problem/A", configure)

        self.assertEqual(ctx.exception.code, "provider_timeout")
        self.assertEqual(ctx.exception.status_code, 504)

    def test_codeforces_parse_failed_returns_warning_response(self) -> None:
        def configure(client: FakeAsyncClient) -> None:
            client.get_response = FakeResponse(text="<html><body>No statement</body></html>")

        preview, _client = self._run_with_client(
            "https://codeforces.com/problemset/problem/1234/A",
            configure,
        )

        self.assertEqual(preview.provider, "codeforces")
        self.assertEqual(preview.source_url, "Codeforces 1234A")
        self.assertEqual(preview.stem_markdown, "")
        self.assertTrue(preview.warnings)

    def test_unknown_domain_raises_invalid_url(self) -> None:
        with self.assertRaises(ProblemImportError) as ctx:
            self._run_with_client("https://example.com/problem/1")

        self.assertEqual(ctx.exception.code, "invalid_url")
        self.assertEqual(ctx.exception.status_code, 400)
