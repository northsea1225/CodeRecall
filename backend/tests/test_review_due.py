from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from tests.test_api_contract_day3 import APIServerTestCase


class ReviewDueTests(APIServerTestCase):
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
                "name": "复习队列",
                "description": "到期复习测试",
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
                "status": "reviewing",
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

    def test_due_count_returns_zero_for_empty_database(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/review/due-count")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["due_count"], 0)
        self.assertIn("as_of", payload)

    def test_due_count_returns_three_for_three_due_mistakes(self) -> None:
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        for index in range(3):
            mistake = self._create_mistake(category_id=category["id"], title=f"到期题 {index}")
            self._set_next_review_at(mistake["id"], now - timedelta(days=index + 1))

        future = self._create_mistake(category_id=category["id"], title="未到期题")
        self._set_next_review_at(future["id"], now + timedelta(days=1))

        status, payload, _ = self.request("GET", "/api/v1/review/due-count")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["due_count"], 3)

    def test_due_first_only_returns_due_mistakes_without_random_backfill(self) -> None:
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        due = self._create_mistake(category_id=category["id"], title="已到期")
        future = self._create_mistake(category_id=category["id"], title="未到期")
        unset = self._create_mistake(category_id=category["id"], title="未设置到期")
        self._set_next_review_at(due["id"], now - timedelta(hours=1))
        self._set_next_review_at(future["id"], now + timedelta(hours=1))
        self._set_next_review_at(unset["id"], None)

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "due_first",
                "limit": 10,
            },
        )

        self.assertEqual(status, 201, session)
        self.assertEqual(session["total_count"], 1)
        self.assertEqual(session["next_item"]["mistake_id"], due["id"])

    def test_spaced_repetition_is_alias_of_due_first(self) -> None:
        category = self._create_category()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        due = self._create_mistake(category_id=category["id"], title="间隔复习到期")
        future = self._create_mistake(category_id=category["id"], title="间隔复习未到期")
        self._set_next_review_at(due["id"], now - timedelta(minutes=30))
        self._set_next_review_at(future["id"], now + timedelta(days=2))

        status, session, _ = self.request(
            "POST",
            "/api/v1/review/sessions",
            {
                "strategy": "spaced_repetition",
                "limit": 10,
            },
        )

        self.assertEqual(status, 201, session)
        self.assertEqual(session["total_count"], 1)
        self.assertEqual(session["next_item"]["mistake_id"], due["id"])
