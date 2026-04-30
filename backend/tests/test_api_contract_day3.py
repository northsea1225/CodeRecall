import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib import error, parse, request


BACKEND_DIR = Path(__file__).resolve().parents[1]


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class APIServerTestCase(unittest.TestCase):
    def extra_env(self) -> Dict[str, str]:
        return {
            "ENABLE_AI_ANALYSIS": "false",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
        }

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.port = find_free_port()
        self.database_url = f"sqlite:///{Path(self.tempdir.name) / 'test.db'}"
        self.server = self._start_server()
        self.auth_token = self._login_old_user()

    def tearDown(self) -> None:
        if hasattr(self, "server") and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=5)

        self.tempdir.cleanup()

    def _start_server(self) -> subprocess.Popen:
        env = os.environ.copy()
        env["APP_ENV"] = "test"
        env["DATABASE_URL"] = self.database_url
        env["PYTHONPATH"] = str(BACKEND_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        env.update(self.extra_env())

        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._wait_until_healthy(server)
        return server

    def _wait_until_healthy(self, server: subprocess.Popen) -> None:
        deadline = time.time() + 15
        last_error: Optional[Exception] = None

        while time.time() < deadline:
            if server.poll() is not None:
                output = server.stdout.read() if server.stdout else ""
                raise RuntimeError(f"Uvicorn exited early:\n{output}")

            try:
                status, payload, _ = self.request("GET", "/health")
                if status == 200 and payload["status"] == "ok":
                    return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.2)

        output = server.stdout.read() if server.stdout else ""
        raise RuntimeError(f"Timed out waiting for server: {last_error}\n{output}")

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[Any] = None,
    ) -> Tuple[int, Optional[Union[Dict, List]], Dict[str, str]]:
        url = f"http://127.0.0.1:{self.port}{path}"
        headers = {"Accept": "application/json"}
        if hasattr(self, "auth_token"):
            headers["Authorization"] = f"Bearer {self.auth_token}"
        body = None

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url, data=body, headers=headers, method=method)

        try:
            with request.urlopen(req, timeout=5) as response:
                status_code = response.status
                raw_body = response.read().decode("utf-8")
                response_headers = dict(response.headers)
        except error.HTTPError as exc:
            status_code = exc.code
            raw_body = exc.read().decode("utf-8")
            response_headers = dict(exc.headers)

        parsed_body = json.loads(raw_body) if raw_body else None
        return status_code, parsed_body, response_headers

    def _login_old_user(self) -> str:
        url = f"http://127.0.0.1:{self.port}/api/v1/auth/token"
        body = parse.urlencode({"username": "old_user", "password": "coderecall"}).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["access_token"]


class Day3APIContractTests(APIServerTestCase):
    def _create_category(self, *, name: str = "哈希表", description: str = "查找与映射") -> dict:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {
                "name": name,
                "description": description,
            },
        )
        self.assertEqual(status, 201, category)
        return category

    def _create_mistake(
        self,
        *,
        category_id: int,
        title: str,
        stem_markdown: str,
        wrong_answer_markdown: str = "错误代码",
        correct_answer_markdown: str = "正确代码",
        error_reason_markdown: str = "没有处理边界条件。",
        language: str = "python",
        difficulty: int = 2,
        source: str = "LeetCode",
        status_value: str = "new",
        tags: Optional[List[str]] = None,
    ) -> dict:
        status, mistake, _ = self.request(
            "POST",
            "/api/v1/mistakes",
            {
                "title": title,
                "stem_markdown": stem_markdown,
                "wrong_answer_markdown": wrong_answer_markdown,
                "correct_answer_markdown": correct_answer_markdown,
                "error_reason_markdown": error_reason_markdown,
                "language": language,
                "difficulty": difficulty,
                "source": source,
                "status": status_value,
                "category_id": category_id,
                "tags": tags or [],
            },
        )
        self.assertEqual(status, 201, mistake)
        return mistake

    def test_mistake_crud_supports_nested_category_and_auto_created_tags(self) -> None:
        category = self._create_category()

        mistake_payload = {
            "title": "两数之和遗漏重复元素边界",
            "stem_markdown": "给定数组 nums 和 target。",
            "wrong_answer_markdown": "错误代码",
            "correct_answer_markdown": "正确代码",
            "error_reason_markdown": "没有处理任意位置补数匹配。",
            "language": "python",
            "difficulty": 2,
            "source": "LeetCode",
            "status": "new",
            "category_id": category["id"],
            "tags": ["边界条件", "哈希表"],
        }
        status, mistake, _ = self.request("POST", "/api/v1/mistakes", mistake_payload)
        self.assertEqual(status, 201, mistake)
        self.assertEqual(mistake["category"]["name"], "哈希表")
        self.assertEqual([tag["name"] for tag in mistake["tags"]], ["边界条件", "哈希表"])

        query = parse.urlencode(
            {
                "page": 1,
                "page_size": 10,
                "category_id": category["id"],
                "language": "python",
            }
        )
        status, listing, _ = self.request("GET", f"/api/v1/mistakes?{query}")
        self.assertEqual(status, 200, listing)
        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["pagination"]["page"], 1)
        self.assertEqual(listing["items"][0]["id"], mistake["id"])

        status, detail, _ = self.request("GET", f"/api/v1/mistakes/{mistake['id']}")
        self.assertEqual(status, 200, detail)
        self.assertEqual(detail["title"], mistake_payload["title"])

        status, updated, _ = self.request(
            "PATCH",
            f"/api/v1/mistakes/{mistake['id']}",
            {
                "title": "两数之和：边界遗漏",
                "difficulty": 3,
                "tags": ["边界条件", "双指针"],
            },
        )
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated["title"], "两数之和：边界遗漏")
        self.assertEqual(updated["difficulty"], 3)
        self.assertEqual([tag["name"] for tag in updated["tags"]], ["边界条件", "双指针"])

        status, _, _ = self.request("DELETE", f"/api/v1/mistakes/{mistake['id']}")
        self.assertEqual(status, 204)

        status, missing, _ = self.request("GET", f"/api/v1/mistakes/{mistake['id']}")
        self.assertEqual(status, 404, missing)
        self.assertEqual(
            missing,
            {
                "code": "mistake_not_found",
                "message": "Mistake not found.",
                "detail": {"mistake_id": mistake["id"]},
            },
        )

    def test_patch_status_field_is_ignored_when_schema_no_longer_accepts_it(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(
            category_id=category["id"],
            title="状态机不允许前端直改",
            stem_markdown="review 驱动 status。",
        )

        status, updated, _ = self.request(
            "PATCH",
            f"/api/v1/mistakes/{mistake['id']}",
            {
                "status": "mastered",
                "title": "状态字段应被忽略",
            },
        )
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated["title"], "状态字段应被忽略")
        self.assertEqual(updated["status"], "new")

    def test_category_and_tag_crud_endpoints_work(self) -> None:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {"name": "动态规划", "description": "DP / 状态转移"},
        )
        self.assertEqual(status, 201, category)

        status, categories, _ = self.request("GET", "/api/v1/categories")
        self.assertEqual(status, 200, categories)
        self.assertEqual(categories["total"], 1)

        status, category_detail, _ = self.request("GET", f"/api/v1/categories/{category['id']}")
        self.assertEqual(status, 200, category_detail)

        status, updated_category, _ = self.request(
            "PATCH",
            f"/api/v1/categories/{category['id']}",
            {"name": "动态规划 DP"},
        )
        self.assertEqual(status, 200, updated_category)
        self.assertEqual(updated_category["name"], "动态规划 DP")

        status, category_delete, _ = self.request("DELETE", f"/api/v1/categories/{category['id']}")
        self.assertEqual(status, 200, category_delete)
        self.assertEqual(category_delete, {"id": category["id"], "deleted": True})

        status, tag, _ = self.request("POST", "/api/v1/tags", {"name": "边界条件"})
        self.assertEqual(status, 201, tag)

        status, tags, _ = self.request("GET", "/api/v1/tags")
        self.assertEqual(status, 200, tags)
        self.assertEqual(tags["total"], 1)

        status, tag_detail, _ = self.request("GET", f"/api/v1/tags/{tag['id']}")
        self.assertEqual(status, 200, tag_detail)

        status, updated_tag, _ = self.request(
            "PATCH",
            f"/api/v1/tags/{tag['id']}",
            {"name": "边界条件检查"},
        )
        self.assertEqual(status, 200, updated_tag)
        self.assertEqual(updated_tag["name"], "边界条件检查")

        status, tag_delete, _ = self.request("DELETE", f"/api/v1/tags/{tag['id']}")
        self.assertEqual(status, 200, tag_delete)
        self.assertEqual(tag_delete, {"id": tag["id"], "deleted": True})

    def test_import_export_support_skip_existing_and_version_validation(self) -> None:
        import_payload = {
            "version": "v1",
            "categories": [
                {"name": "数组", "description": "数组与双指针"},
            ],
            "tags": [
                {"name": "边界条件"},
            ],
            "mistakes": [
                {
                    "title": "三数之和去重遗漏",
                    "stem_markdown": "给定数组 nums。",
                    "wrong_answer_markdown": "错误代码",
                    "correct_answer_markdown": "正确代码",
                    "error_reason_markdown": "没有处理去重。",
                    "language": "python",
                    "difficulty": 3,
                    "source": "LeetCode",
                    "status": "new",
                    "category_name": "数组",
                    "tag_names": ["边界条件"],
                }
            ],
        }

        status, imported, _ = self.request(
            "POST",
            "/api/v1/import?strategy=skip_existing",
            import_payload,
        )
        self.assertEqual(status, 200, imported)
        self.assertEqual(imported["imported"], {"mistakes": 1, "categories": 1, "tags": 1})
        self.assertEqual(imported["skipped"], [])

        status, duplicate_import, _ = self.request(
            "POST",
            "/api/v1/import?strategy=skip_existing",
            import_payload,
        )
        self.assertEqual(status, 200, duplicate_import)
        self.assertEqual(duplicate_import["imported"], {"mistakes": 0, "categories": 0, "tags": 0})
        self.assertEqual(len(duplicate_import["skipped"]), 3)

        status, exported, headers = self.request("GET", "/api/v1/export?include=mistakes")
        self.assertEqual(status, 200, exported)
        self.assertEqual(exported["version"], "v1")
        self.assertEqual(exported["schema_version"], "v2")
        self.assertEqual(len(exported["mistakes"]), 1)
        self.assertEqual(exported["mistakes"][0]["ease_factor"], 2.5)
        self.assertEqual(exported["mistakes"][0]["interval_days"], 0)
        self.assertEqual(exported["mistakes"][0]["repetition"], 0)
        self.assertEqual(exported["categories"], [])
        self.assertEqual(exported["tags"], [])
        normalized_headers = {key.lower(): value for key, value in headers.items()}
        self.assertIn("attachment;", normalized_headers.get("content-disposition", ""))

        status, invalid, _ = self.request(
            "POST",
            "/api/v1/import",
            {
                "version": "legacy",
                "categories": [],
                "tags": [],
                "mistakes": [],
            },
        )
        self.assertEqual(status, 400, invalid)
        self.assertEqual(
            invalid,
            {
                "code": "invalid_import_version",
                "message": "Import payload version must be 'v1'.",
                "detail": {"version": "legacy"},
            },
        )

    def test_mistakes_import_export_v2_round_trip_list_shape(self) -> None:
        category = self._create_category(name="滑动窗口")
        self._create_mistake(
            category_id=category["id"],
            title="窗口左边界更新遗漏",
            stem_markdown="给定字符串 s。",
            error_reason_markdown="收缩窗口时没有同步计数。",
            tags=["双指针"],
        )

        status, exported, _ = self.request("GET", "/api/v1/mistakes/export")
        self.assertEqual(status, 200, exported)
        self.assertIsInstance(exported, list)
        self.assertEqual(len(exported), 1)
        required_fields = {
            "id",
            "title",
            "stem",
            "error_reason",
            "wrong_answer_markdown",
            "correct_answer_markdown",
            "ease_factor",
            "interval_days",
            "next_review_at",
            "is_archived",
        }
        self.assertTrue(required_fields.issubset(exported[0].keys()))

        round_trip = [dict(exported[0], title="窗口左边界更新遗漏 round-trip")]
        status, imported, _ = self.request("POST", "/api/v1/mistakes/import", round_trip)
        self.assertEqual(status, 200, imported)
        self.assertEqual(imported["imported"]["mistakes"], 1)

    def test_import_v1_without_schema_version_remains_compatible(self) -> None:
        status, imported, _ = self.request(
            "POST",
            "/api/v1/import?strategy=skip_existing",
            {
                "version": "v1",
                "categories": [{"name": "动态规划", "description": ""}],
                "tags": [],
                "mistakes": [
                    {
                        "title": "状态转移初始化遗漏",
                        "stem_markdown": "初始化 dp。",
                        "wrong_answer_markdown": "wrong",
                        "correct_answer_markdown": "correct",
                        "error_reason_markdown": "base case 缺失。",
                        "language": "python",
                        "difficulty": 2,
                        "source": "",
                        "status": "new",
                        "category_name": "动态规划",
                        "tag_names": [],
                    }
                ],
            },
        )

        self.assertEqual(status, 200, imported)
        self.assertEqual(imported["imported"]["mistakes"], 1)
        status, listing, _ = self.request("GET", "/api/v1/mistakes?page=1&page_size=10")
        self.assertEqual(status, 200, listing)
        self.assertEqual(listing["items"][0]["ease_factor"], 2.5)
        self.assertEqual(listing["items"][0]["interval_days"], 0)
        self.assertEqual(listing["items"][0]["repetition"], 0)

    def test_import_v2_schema_version_accepts_sm2_fields(self) -> None:
        status, imported, _ = self.request(
            "POST",
            "/api/v1/import?strategy=skip_existing",
            {
                "version": "v1",
                "schema_version": "v2",
                "categories": [{"name": "图论", "description": ""}],
                "tags": [],
                "mistakes": [
                    {
                        "title": "BFS 层数重复入队",
                        "stem_markdown": "图遍历。",
                        "wrong_answer_markdown": "wrong",
                        "correct_answer_markdown": "correct",
                        "error_reason_markdown": "visited 时机错误。",
                        "language": "python",
                        "difficulty": 3,
                        "source": "",
                        "status": "reviewing",
                        "category_name": "图论",
                        "tag_names": [],
                        "ease_factor": 1.8,
                        "interval_days": 12,
                        "repetition": 4,
                    }
                ],
            },
        )

        self.assertEqual(status, 200, imported)
        self.assertEqual(imported["imported"]["mistakes"], 1)
        status, listing, _ = self.request("GET", "/api/v1/mistakes?page=1&page_size=10")
        self.assertEqual(status, 200, listing)
        imported_mistake = next(item for item in listing["items"] if item["title"] == "BFS 层数重复入队")
        self.assertEqual(imported_mistake["ease_factor"], 1.8)
        self.assertEqual(imported_mistake["interval_days"], 12)
        self.assertEqual(imported_mistake["repetition"], 4)

    def test_import_skips_mistake_when_ease_factor_is_out_of_range(self) -> None:
        status, imported, _ = self.request(
            "POST",
            "/api/v1/import?strategy=skip_existing",
            {
                "version": "v1",
                "schema_version": "v2",
                "categories": [{"name": "贪心", "description": ""}],
                "tags": [],
                "mistakes": [
                    {
                        "title": "区间排序策略错误",
                        "stem_markdown": "选择最少区间。",
                        "wrong_answer_markdown": "wrong",
                        "correct_answer_markdown": "correct",
                        "error_reason_markdown": "排序键错误。",
                        "language": "python",
                        "difficulty": 3,
                        "source": "",
                        "status": "new",
                        "category_name": "贪心",
                        "tag_names": [],
                        "ease_factor": 9.9,
                        "interval_days": 0,
                        "repetition": 0,
                    }
                ],
            },
        )

        self.assertEqual(status, 200, imported)
        self.assertEqual(imported["imported"]["mistakes"], 0)
        self.assertEqual(
            imported["skipped"],
            [{"entity": "mistake", "identifier": "区间排序策略错误", "reason": "invalid_ease_factor"}],
        )
        status, listing, _ = self.request("GET", "/api/v1/mistakes?page=1&page_size=10")
        self.assertEqual(status, 200, listing)
        self.assertEqual(listing["total"], 0)

    def test_list_mistakes_supports_keyword_search_across_multiple_fields(self) -> None:
        category = self._create_category()
        first = self._create_mistake(
            category_id=category["id"],
            title="Hash duplicate window",
            stem_markdown="slide the window over nums",
            wrong_answer_markdown="miss duplicate cleanup",
            error_reason_markdown="window 收缩时忘记同步 map。",
        )
        second = self._create_mistake(
            category_id=category["id"],
            title="Binary search off by one",
            stem_markdown="check left boundary carefully",
            wrong_answer_markdown="while left < right",
            error_reason_markdown="边界推进错误。",
        )
        self._create_mistake(
            category_id=category["id"],
            title="Prefix sum counting",
            stem_markdown="count subarrays with prefix map",
            wrong_answer_markdown="reuse stale sum",
            error_reason_markdown="map 初始化不完整。",
        )

        status, title_match, _ = self.request("GET", "/api/v1/mistakes?keyword=duplicate")
        self.assertEqual(status, 200, title_match)
        self.assertEqual(title_match["total"], 1)
        self.assertEqual(title_match["items"][0]["id"], first["id"])

        status, stem_match, _ = self.request("GET", "/api/v1/mistakes?keyword=boundary")
        self.assertEqual(status, 200, stem_match)
        self.assertEqual(stem_match["total"], 1)
        self.assertEqual(stem_match["items"][0]["id"], second["id"])

        status, multi_match, _ = self.request("GET", "/api/v1/mistakes?keyword=duplicate+window")
        self.assertEqual(status, 200, multi_match)
        self.assertEqual(multi_match["total"], 1)
        self.assertEqual(multi_match["items"][0]["id"], first["id"])

        status, blank_keyword, _ = self.request("GET", "/api/v1/mistakes?keyword=+++")
        self.assertEqual(status, 200, blank_keyword)
        self.assertEqual(blank_keyword["total"], 3)


if __name__ == "__main__":
    unittest.main()
