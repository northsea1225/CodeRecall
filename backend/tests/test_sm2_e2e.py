"""
SM-2 到期调度 e2e 测试
验证 due-first 策略的完整流程，包括队列排序、状态转换、间隔计算
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from tests.test_api_contract_day3 import APIServerTestCase


class SM2E2ETests(APIServerTestCase):
    def _database_path(self) -> str:
        return self.database_url.removeprefix("sqlite:///")

    def _execute(self, sql: str, params: tuple = ()) -> None:
        with sqlite3.connect(self._database_path()) as conn:
            conn.execute(sql, params)
            conn.commit()

    def _store_datetime(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")

    def _create_category(self) -> dict:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {
                "name": "SM-2测试",
                "description": "到期调度测试",
            },
        )
        self.assertEqual(status, 201, category)
        return category

    def _create_mistake(self, *, category_id: int, title: str) -> dict:
        status, mistake, _ = self.request(
            "POST",
            "/api/v1/mistakes",
            {
                "title": title,
                "stem_markdown": "题干",
                "wrong_answer_markdown": "错误答案",
                "correct_answer_markdown": "正确答案",
                "error_reason_markdown": "错因",
                "language": "python",
                "difficulty": 2,
                "source": "LeetCode",
                "status": "learning",
                "category_id": category_id,
                "tags": [],
            },
        )
        self.assertEqual(status, 201, mistake)
        return mistake

    def _set_next_review_at(self, mistake_id: int, value: datetime | None) -> None:
        self._execute(
            "UPDATE mistakes SET next_review_at = ? WHERE id = ?",
            (self._store_datetime(value) if value else None, mistake_id),
        )

    def _get_mistake_fields(self, mistake_id: int) -> dict:
        """获取 mistake 的关键字段用于验证"""
        with sqlite3.connect(self._database_path()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT next_review_at, status, ease_factor, interval_days, repetition
                FROM mistakes WHERE id = ?
                """,
                (mistake_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {}
            fields = dict(row)
            if isinstance(fields.get("status"), str):
                fields["status"] = fields["status"].lower()
            return fields

    def test_due_count_returns_seven_for_seven_due_mistakes(self) -> None:
        """Case 1: due-count 返回 7（前 7 条都 <= now）"""
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)

        # 3 条过期 1 天
        for i in range(3):
            mistake = self._create_mistake(category_id=category["id"], title=f"过期1天-{i}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=1))

        # 2 条过期 3 天
        for i in range(2):
            mistake = self._create_mistake(category_id=category["id"], title=f"过期3天-{i}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=3))

        # 2 条过期 5 天
        for i in range(2):
            mistake = self._create_mistake(category_id=category["id"], title=f"过期5天-{i}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=5))

        # 2 条未来到期
        for i in range(2):
            mistake = self._create_mistake(category_id=category["id"], title=f"未来到期-{i}")
            self._set_next_review_at(mistake["id"], now + timedelta(days=1))

        # 1 条无 next_review_at
        mistake = self._create_mistake(category_id=category["id"], title="无到期时间")
        self._set_next_review_at(mistake["id"], None)

        status, payload, _ = self.request("GET", "/api/v1/review/due-count")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["due_count"], 7)

    def test_due_first_returns_seven_sorted_by_next_review_at(self) -> None:
        """Case 2: start_session strategy=due_first limit=10 返回 7 条按 next_review_at asc 排序"""
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)

        # 创建 10 条 mistake，7 条到期，3 条未到期/无时间
        due_mistakes = []

        # 过期 5 天（最早）
        for i in range(2):
            mistake = self._create_mistake(category_id=category["id"], title=f"过期5天-{i}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=5, hours=i))
            due_mistakes.append(mistake["id"])

        # 过期 3 天
        for i in range(2):
            mistake = self._create_mistake(category_id=category["id"], title=f"过期3天-{i}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=3, hours=i))
            due_mistakes.append(mistake["id"])

        # 过期 1 天（最近）
        for i in range(3):
            mistake = self._create_mistake(category_id=category["id"], title=f"过期1天-{i}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=1, hours=i))
            due_mistakes.append(mistake["id"])

        # 未来到期（不应出现）
        for i in range(2):
            mistake = self._create_mistake(category_id=category["id"], title=f"未来-{i}")
            self._set_next_review_at(mistake["id"], now + timedelta(days=1))

        # 无时间（不应出现）
        mistake = self._create_mistake(category_id=category["id"], title="无时间")
        self._set_next_review_at(mistake["id"], None)

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "due_first",
                "limit": 10,
            },
        )

        self.assertEqual(status, 201, session)
        self.assertEqual(session["total_count"], 7)

        # 验证第一题是最早到期的
        first_item = session["next_item"]
        self.assertIn(first_item["mistake_id"], due_mistakes[:2])  # 应该是过期5天的其中一个

    def test_three_good_reviews_progress_status_to_mastered(self) -> None:
        """Case 3: 连续 submit good 3 次，next_review_at 前移，status 从 learning 到 reviewing 到 mastered"""
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)

        mistake = self._create_mistake(category_id=category["id"], title="状态转换测试")
        self._set_next_review_at(mistake["id"], now - timedelta(hours=1))

        # 开始 session
        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "spaced_repetition",
                "limit": 1,
            },
        )
        self.assertEqual(status, 201)
        session_id = session["id"]
        self.assertIn("mistake_id", session["next_item"])
        item_id = session["next_item"]["mistake_id"]

        # 第一次 good
        status, _, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {"mistake_id": item_id, "user_result": "good"},
        )
        self.assertEqual(status, 200)

        fields = self._get_mistake_fields(mistake["id"])
        self.assertEqual(fields["status"], "learning")
        self.assertEqual(fields["repetition"], 1)
        self.assertEqual(fields["interval_days"], 1)

        # 第二次 good（需要重新开始 session）
        self._set_next_review_at(mistake["id"], now - timedelta(hours=1))
        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {"strategy": "spaced_repetition", "limit": 1},
        )
        self.assertEqual(status, 201)
        session_id = session["id"]
        self.assertIn("mistake_id", session["next_item"])
        item_id = session["next_item"]["mistake_id"]

        status, _, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {"mistake_id": item_id, "user_result": "good"},
        )
        self.assertEqual(status, 200)

        fields = self._get_mistake_fields(mistake["id"])
        self.assertEqual(fields["status"], "reviewing")
        self.assertEqual(fields["repetition"], 2)
        self.assertEqual(fields["interval_days"], 3)

        # 第三次 good
        self._set_next_review_at(mistake["id"], now - timedelta(hours=1))
        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {"strategy": "spaced_repetition", "limit": 1},
        )
        self.assertEqual(status, 201)
        session_id = session["id"]
        self.assertIn("mistake_id", session["next_item"])
        item_id = session["next_item"]["mistake_id"]

        status, _, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {"mistake_id": item_id, "user_result": "good"},
        )
        self.assertEqual(status, 200)

        fields = self._get_mistake_fields(mistake["id"])
        self.assertEqual(fields["status"], "mastered")
        self.assertEqual(fields["repetition"], 3)
        # interval_days 应该是 3 * ease_factor，约 7-8 天
        self.assertGreaterEqual(fields["interval_days"], 7)

    def test_again_resets_repetition_and_interval(self) -> None:
        """Case 4: submit again 1 次，next_review_at 重置为 1 天后，repetition=0"""
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)

        mistake = self._create_mistake(category_id=category["id"], title="Again重置测试")
        self._set_next_review_at(mistake["id"], now - timedelta(hours=1))

        # 先设置一些进度
        self._execute(
            "UPDATE mistakes SET repetition = 3, interval_days = 7, status = 'REVIEWING' WHERE id = ?",
            (mistake["id"],),
        )

        # 开始 session
        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {"strategy": "spaced_repetition", "limit": 1},
        )
        self.assertEqual(status, 201)
        session_id = session["id"]
        self.assertIn("mistake_id", session["next_item"])
        item_id = session["next_item"]["mistake_id"]

        # Submit again
        status, _, _ = self.request(
            "POST",
            f"/api/v1/review/sessions/{session_id}/submit",
            {"mistake_id": item_id, "user_result": "again"},
        )
        self.assertEqual(status, 200)

        fields = self._get_mistake_fields(mistake["id"])
        self.assertEqual(fields["repetition"], 0)
        self.assertEqual(fields["interval_days"], 1)
        self.assertEqual(fields["status"], "learning")

    def test_future_mistakes_not_in_due_first_session(self) -> None:
        """Case 5: 未来到期的题不应该出现在 due_first session 里"""
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)

        # 1 条到期
        due = self._create_mistake(category_id=category["id"], title="已到期")
        self._set_next_review_at(due["id"], now - timedelta(hours=1))

        # 5 条未来到期
        for i in range(5):
            future = self._create_mistake(category_id=category["id"], title=f"未来-{i}")
            self._set_next_review_at(future["id"], now + timedelta(days=i + 1))

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {"strategy": "due_first", "limit": 10},
        )

        self.assertEqual(status, 201)
        self.assertEqual(session["total_count"], 1)
        self.assertEqual(session["next_item"]["mistake_id"], due["id"])

    def test_mistakes_without_next_review_at_not_in_due_first(self) -> None:
        """Case 6: 无 next_review_at 的题不出现在 due_first"""
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)

        # 1 条到期
        due = self._create_mistake(category_id=category["id"], title="已到期")
        self._set_next_review_at(due["id"], now - timedelta(hours=1))

        # 3 条无 next_review_at
        for i in range(3):
            unset = self._create_mistake(category_id=category["id"], title=f"无时间-{i}")
            self._set_next_review_at(unset["id"], None)

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {"strategy": "due_first", "limit": 10},
        )

        self.assertEqual(status, 201)
        self.assertEqual(session["total_count"], 1)
        self.assertEqual(session["next_item"]["mistake_id"], due["id"])
