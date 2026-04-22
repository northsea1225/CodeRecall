from typing import Optional
from urllib import parse
import sqlite3

from tests.test_api_contract_day3 import APIServerTestCase


class ReviewAPISmokeTests(APIServerTestCase):
    def _update_schedule_fields(
        self,
        mistake_id: int,
        *,
        next_review_at: str,
        ease_factor: float = 2.5,
        interval_days: int = 0,
        repetition: int = 0,
    ) -> None:
        database_path = self.database_url.removeprefix("sqlite:///")
        with sqlite3.connect(database_path) as conn:
            conn.execute(
                """
                UPDATE mistakes
                SET next_review_at = ?, ease_factor = ?, interval_days = ?, repetition = ?
                WHERE id = ?
                """,
                (next_review_at, ease_factor, interval_days, repetition, mistake_id),
            )
            conn.commit()

    def _create_category(self) -> dict:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {
                "name": "数组",
                "description": "数组与双指针",
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
        wrong_answer_markdown: str,
        correct_answer_markdown: str,
        error_reason_markdown: str,
        language: str = "python",
        difficulty: int = 2,
        tags: Optional[list[str]] = None,
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
                "source": "LeetCode",
                "status": "new",
                "category_id": category_id,
                "tags": tags or [],
            },
        )
        self.assertEqual(status, 201, mistake)
        return mistake

    def test_review_flow_smoke_covers_start_next_submit_summary_and_reveal(self) -> None:
        category = self._create_category()
        mistake_one = self._create_mistake(
            category_id=category["id"],
            title="两数之和哈希遗漏",
            stem_markdown="给定数组 nums 和 target。",
            wrong_answer_markdown="for i in range(len(nums)): pass",
            correct_answer_markdown="seen = {}",
            error_reason_markdown="没有先判断补数。",
            tags=["哈希", "边界"],
        )
        mistake_two = self._create_mistake(
            category_id=category["id"],
            title="滑动窗口边界错位",
            stem_markdown="求最短覆盖子串。",
            wrong_answer_markdown="left += 1",
            correct_answer_markdown="while matched == need: ...",
            error_reason_markdown="窗口收缩条件错了。",
            language="javascript",
            difficulty=3,
            tags=["滑动窗口"],
        )

        status, capability, _ = self.request("GET", "/api/v1/review/capability")
        self.assertEqual(status, 200, capability)
        self.assertEqual(capability, {"ai_analysis_enabled": False})

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "random",
                "limit": 2,
            },
        )
        self.assertEqual(status, 201, session)
        self.assertEqual(session["strategy"], "random")
        self.assertEqual(session["total_count"], 2)
        self.assertEqual(session["completed_count"], 0)
        self.assertIsNotNone(session["next_item"])

        session_id = session["id"]
        first_item = session["next_item"]
        self.assertIn(first_item["mistake_id"], {mistake_one["id"], mistake_two["id"]})
        self.assertNotIn("wrong_answer_markdown", first_item)
        self.assertEqual(first_item["category_name"], category["name"])

        status, reveal, _ = self.request("GET", f"/api/v1/review/items/{first_item['mistake_id']}/reveal")
        self.assertEqual(status, 200, reveal)
        self.assertEqual(reveal["mistake_id"], first_item["mistake_id"])
        self.assertIn("wrong_answer_markdown", reveal)
        self.assertIn("correct_answer_markdown", reveal)
        self.assertIn("error_reason_markdown", reveal)

        status, submit, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {
                "mistake_id": first_item["mistake_id"],
                "user_result": "good",
                "time_spent_ms": 42000,
                "note": "第一轮可接受",
            },
        )
        self.assertEqual(status, 200, submit)
        self.assertEqual(submit["mistake_id"], first_item["mistake_id"])
        self.assertEqual(submit["user_result"], "good")
        self.assertEqual(submit["time_spent_ms"], 42000)
        self.assertEqual(submit["progress"], {"completed": 1, "total": 2})

        status, first_detail, _ = self.request("GET", f"/api/v1/mistakes/{first_item['mistake_id']}")
        self.assertEqual(status, 200, first_detail)
        self.assertEqual(first_detail["review_count"], 1)
        self.assertEqual(first_detail["status"], "learning")
        self.assertIsNotNone(first_detail["last_reviewed_at"])

        status, duplicate_submit, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {
                "mistake_id": first_item["mistake_id"],
                "user_result": "easy",
                "time_spent_ms": 3000,
                "note": "重复提交应幂等",
            },
        )
        self.assertEqual(status, 200, duplicate_submit)
        self.assertEqual(duplicate_submit["id"], submit["id"])
        self.assertEqual(duplicate_submit["user_result"], "good")
        self.assertEqual(duplicate_submit["time_spent_ms"], 42000)
        self.assertEqual(duplicate_submit["progress"], {"completed": 1, "total": 2})

        status, detail_after_duplicate, _ = self.request("GET", f"/api/v1/mistakes/{first_item['mistake_id']}")
        self.assertEqual(status, 200, detail_after_duplicate)
        self.assertEqual(detail_after_duplicate["review_count"], 1)
        self.assertEqual(detail_after_duplicate["last_reviewed_at"], first_detail["last_reviewed_at"])

        status, next_payload, _ = self.request(
            "GET",
            f"/api/v1/review/sessions/{session_id}/next",
        )
        self.assertEqual(status, 200, next_payload)
        self.assertEqual(next_payload["progress"], {"completed": 1, "total": 2})
        self.assertIsNotNone(next_payload["next_item"])

        second_item = next_payload["next_item"]
        self.assertNotEqual(second_item["mistake_id"], first_item["mistake_id"])

        status, second_submit, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {
                "mistake_id": second_item["mistake_id"],
                "user_result": "again",
                "note": "需要重新练习",
            },
        )
        self.assertEqual(status, 200, second_submit)
        self.assertEqual(second_submit["progress"], {"completed": 2, "total": 2})

        status, completed_payload, _ = self.request(
            "GET",
            f"/api/v1/review/sessions/{session_id}/next",
        )
        self.assertEqual(status, 200, completed_payload)
        self.assertIsNone(completed_payload["next_item"])
        self.assertEqual(completed_payload["progress"], {"completed": 2, "total": 2})

        status, summary, _ = self.request(
            "GET",
            f"/api/v1/review/sessions/{session_id}/summary",
        )
        self.assertEqual(status, 200, summary)
        self.assertEqual(summary["total_count"], 2)
        self.assertEqual(summary["completed_count"], 2)
        self.assertEqual(
            summary["result_counts"],
            {
                "again": 1,
                "hard": 0,
                "good": 1,
                "easy": 0,
            },
        )
        self.assertGreaterEqual(summary["duration_ms"], 0)

    def test_review_session_returns_empty_queue_when_no_mistake_exists(self) -> None:
        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "random",
            },
        )
        self.assertEqual(status, 201, session)
        self.assertEqual(session["total_count"], 0)
        self.assertIsNone(session["next_item"])

        session_id = session["id"]
        status, next_payload, _ = self.request("GET", f"/api/v1/review/sessions/{session_id}/next")
        self.assertEqual(status, 200, next_payload)
        self.assertEqual(next_payload, {"next_item": None, "progress": {"completed": 0, "total": 0}})

    def test_submit_rejects_mistake_outside_session_queue(self) -> None:
        category = self._create_category()
        in_queue = self._create_mistake(
            category_id=category["id"],
            title="队列内题目",
            stem_markdown="队列内",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )
        outside_queue = self._create_mistake(
            category_id=category["id"],
            title="队列外题目",
            stem_markdown="队列外",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "random",
                "limit": 1,
            },
        )
        self.assertEqual(status, 201, session)
        self.assertEqual(session["total_count"], 1)
        self.assertIn(session["next_item"]["mistake_id"], {in_queue["id"], outside_queue["id"]})

        out_of_queue_id = outside_queue["id"] if session["next_item"]["mistake_id"] == in_queue["id"] else in_queue["id"]
        status, error_payload, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session['id']}/submit",
            {
                "mistake_id": out_of_queue_id,
                "user_result": "hard",
            },
        )
        self.assertEqual(status, 422, error_payload)
        self.assertEqual(error_payload["code"], "mistake_not_in_session")

    def test_spaced_repetition_updates_schedule_fields_without_breaking_review_flow(self) -> None:
        category = self._create_category()
        due_mistake = self._create_mistake(
            category_id=category["id"],
            title="到期的错题",
            stem_markdown="应优先复习。",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )
        fresh_mistake = self._create_mistake(
            category_id=category["id"],
            title="未到期的错题",
            stem_markdown="后续再复习。",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )
        self._update_schedule_fields(
            due_mistake["id"],
            next_review_at="2026-04-10T08:00:00+00:00",
            ease_factor=2.5,
            interval_days=0,
            repetition=0,
        )
        self._update_schedule_fields(
            fresh_mistake["id"],
            next_review_at="2026-05-20T08:00:00+00:00",
            ease_factor=2.5,
            interval_days=5,
            repetition=2,
        )

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "spaced_repetition",
                "limit": 1,
            },
        )
        self.assertEqual(status, 201, session)
        self.assertEqual(session["strategy"], "spaced_repetition")
        self.assertEqual(session["next_item"]["mistake_id"], due_mistake["id"])

        status, submit, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session['id']}/submit",
            {
                "mistake_id": due_mistake["id"],
                "user_result": "good",
            },
        )
        self.assertEqual(status, 200, submit)
        self.assertEqual(submit["progress"], {"completed": 1, "total": 1})

        status, detail, _ = self.request("GET", f"/api/v1/mistakes/{due_mistake['id']}")
        self.assertEqual(status, 200, detail)
        self.assertEqual(detail["review_count"], 1)
        self.assertEqual(detail["interval_days"], 1)
        self.assertEqual(detail["repetition"], 1)
        self.assertEqual(detail["ease_factor"], 2.5)
        self.assertIsNotNone(detail["next_review_at"])

    def test_due_first_returns_only_due_items_without_random_backfill(self) -> None:
        category = self._create_category()
        due_mistake = self._create_mistake(
            category_id=category["id"],
            title="先复习我",
            stem_markdown="已到期。",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )
        future_mistake = self._create_mistake(
            category_id=category["id"],
            title="未来再复习",
            stem_markdown="未到期。",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )
        self._update_schedule_fields(
            due_mistake["id"],
            next_review_at="2026-04-10T08:00:00+00:00",
        )
        self._update_schedule_fields(
            future_mistake["id"],
            next_review_at="2026-05-20T08:00:00+00:00",
        )

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "due_first",
                "limit": 2,
            },
        )
        self.assertEqual(status, 201, session)
        self.assertEqual(session["strategy"], "due_first")
        self.assertEqual(session["total_count"], 1)
        self.assertEqual(session["next_item"]["mistake_id"], due_mistake["id"])

    def test_ai_stream_route_returns_503_when_capability_disabled(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/ai/analyze/stream?mistake_id=1")
        self.assertEqual(status, 503, payload)
        self.assertEqual(payload["code"], "ai_analysis_disabled")

    def test_mistake_progress_fields_are_ignored_on_patch(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(
            category_id=category["id"],
            title="进度字段受 review 控制",
            stem_markdown="不能由 PATCH 改进度字段。",
            wrong_answer_markdown="wrong",
            correct_answer_markdown="correct",
            error_reason_markdown="reason",
        )

        status, updated, _ = self.request(
            "PATCH",
            f"/api/v1/mistakes/{mistake['id']}",
            {
                "title": "允许改标题",
                "status": "mastered",
                "review_count": 99,
                "last_reviewed_at": "2026-04-26T10:00:00Z",
                "next_review_at": "2026-04-27T10:00:00Z",
                "ease_factor": 9.9,
                "interval_days": 30,
                "repetition": 10,
            },
        )
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated["title"], "允许改标题")
        self.assertEqual(updated["status"], "new")
        self.assertEqual(updated["review_count"], 0)
        self.assertIsNone(updated["last_reviewed_at"])
        self.assertIsNone(updated["next_review_at"])
        self.assertEqual(updated["ease_factor"], 2.5)
        self.assertEqual(updated["interval_days"], 0)
        self.assertEqual(updated["repetition"], 0)

    def test_ai_analysis_route_returns_503_when_feature_disabled(self) -> None:
        status, payload, _ = self.request(
            "GET",
            "/api/v1/ai/analyze/stream?mistake_id=1",
        )
        self.assertEqual(status, 503, payload)
        self.assertEqual(payload["code"], "ai_analysis_disabled")


class ReviewAIEnabledTests(APIServerTestCase):
    def extra_env(self) -> dict[str, str]:
        return {
            "ENABLE_AI_ANALYSIS": "true",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "gpt-5.4-mini",
        }

    def test_review_capability_reflects_ai_env_flags(self) -> None:
        status, capability, _ = self.request("GET", "/api/v1/review/capability")
        self.assertEqual(status, 200, capability)
        self.assertEqual(
            capability,
            {
                "ai_analysis_enabled": True,
                "model": "gpt-5.4-mini",
            },
        )

    def test_ai_analysis_route_returns_404_for_missing_mistake_when_enabled(self) -> None:
        status, payload, _ = self.request(
            "GET",
            "/api/v1/ai/analyze/stream?mistake_id=1",
        )
        self.assertEqual(status, 404, payload)
        self.assertEqual(payload["code"], "mistake_not_found")
