from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from tests.test_api_contract_day3 import APIServerTestCase


class StatsAPITests(APIServerTestCase):
    def _database_path(self) -> str:
        return self.database_url.removeprefix("sqlite:///")

    def _execute(self, sql: str, params: tuple = ()) -> None:
        with sqlite3.connect(self._database_path()) as conn:
            conn.execute(sql, params)
            conn.commit()

    def _create_category(self, name: str = "数组") -> dict:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {
                "name": name,
                "description": f"{name}相关错题",
            },
        )
        self.assertEqual(status, 201, category)
        return category

    def _create_mistake(
        self,
        *,
        category_id: int,
        title: str,
        language: str = "python",
        status_value: str = "reviewing",
    ) -> dict:
        status, mistake, _ = self.request(
            "POST",
            "/api/v1/mistakes",
            {
                "title": title,
                "stem_markdown": "题干",
                "wrong_answer_markdown": "错误答案",
                "correct_answer_markdown": "正确答案",
                "error_reason_markdown": "错因",
                "language": language,
                "difficulty": 2,
                "source": "LeetCode",
                "status": status_value,
                "category_id": category_id,
                "tags": [],
            },
        )
        self.assertEqual(status, 201, mistake)
        return mistake

    def _store_datetime(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")

    def _local_today_moment_utc(self, tz_offset_minutes: int, hour: int = 0, minute: int = 0) -> datetime:
        local_tz = timezone(timedelta(minutes=tz_offset_minutes))
        now_local = datetime.now(local_tz)
        local_moment = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local_moment > now_local:
            local_moment -= timedelta(days=1)
        return local_moment.astimezone(timezone.utc)

    def _utc_vs_utc8_boundary_case(self) -> tuple[datetime, int, int]:
        now_utc = datetime.now(timezone.utc).replace(microsecond=0)
        utc_today_start = now_utc.replace(hour=0, minute=0, second=0)
        utc8_today_start = self._local_today_moment_utc(480, hour=0, minute=0)

        if utc8_today_start < utc_today_start:
            return utc8_today_start, 0, 1

        return utc_today_start + timedelta(hours=1), 1, 0

    def _insert_review_log(
        self,
        *,
        mistake_id: int,
        shown_at: datetime,
        user_result: str = "good",
        note: str = "",
    ) -> None:
        stored = self._store_datetime(shown_at)
        self._execute(
            """
            INSERT INTO review_logs (
              mistake_id, session_id, review_mode, user_result, shown_at, answered_at, note
            ) VALUES (?, NULL, 'manual', ?, ?, ?, ?)
            """,
            (mistake_id, user_result.upper(), stored, stored, note),
        )

    def _update_mistake(
        self,
        mistake_id: int,
        *,
        created_at: datetime | None = None,
        status_value: str | None = None,
        next_review_at: datetime | None = None,
        ease_factor: float | None = None,
        is_archived: bool | None = None,
    ) -> None:
        assignments: list[str] = []
        params: list[object] = []

        if created_at is not None:
            assignments.append("created_at = ?")
            params.append(self._store_datetime(created_at))
        if status_value is not None:
            assignments.append("status = ?")
            params.append(status_value)
        if next_review_at is not None:
            assignments.append("next_review_at = ?")
            params.append(self._store_datetime(next_review_at))
        if ease_factor is not None:
            assignments.append("ease_factor = ?")
            params.append(ease_factor)
        if is_archived is not None:
            assignments.append("is_archived = ?")
            params.append(1 if is_archived else 0)

        if not assignments:
            return

        params.append(mistake_id)
        self._execute(
            f"UPDATE mistakes SET {', '.join(assignments)} WHERE id = ?",
            tuple(params),
        )

    def test_overview_returns_zero_values_for_empty_database(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/stats/overview")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["total_mistakes"], 0)
        self.assertEqual(payload["active_mistakes"], 0)
        self.assertEqual(payload["due_today"], 0)
        self.assertEqual(payload["reviewed_today"], 0)
        self.assertEqual(payload["reviewed_7d"], 0)
        self.assertEqual(payload["streak_days"], 0)

    def test_overview_counts_today_review_for_single_log(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(category_id=category["id"], title="今日有复习记录")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self._insert_review_log(mistake_id=mistake["id"], shown_at=now - timedelta(minutes=5))

        status, payload, _ = self.request("GET", "/api/v1/stats/overview")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["reviewed_today"], 1)
        self.assertEqual(payload["reviewed_7d"], 1)
        self.assertEqual(payload["avg_accuracy_7d"], 1.0)

    def test_overview_respects_local_day_boundary_for_timezone_offset(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(category_id=category["id"], title="跨时区统计")
        boundary_log, expected_utc_today, expected_cst_today = self._utc_vs_utc8_boundary_case()
        self._insert_review_log(mistake_id=mistake["id"], shown_at=boundary_log, user_result="hard")

        status_utc, utc_payload, _ = self.request("GET", "/api/v1/stats/overview?tz_offset_minutes=0")
        status_cst, cst_payload, _ = self.request("GET", "/api/v1/stats/overview?tz_offset_minutes=480")

        self.assertEqual(status_utc, 200, utc_payload)
        self.assertEqual(status_cst, 200, cst_payload)
        self.assertEqual(utc_payload["reviewed_today"], expected_utc_today)
        self.assertEqual(cst_payload["reviewed_today"], expected_cst_today)

    def test_trend_default_range_returns_items_sorted_by_date(self) -> None:
        category = self._create_category()
        older = self._create_mistake(category_id=category["id"], title="更早创建")
        newer = self._create_mistake(category_id=category["id"], title="较新创建")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self._update_mistake(older["id"], created_at=now - timedelta(days=3))
        self._update_mistake(newer["id"], created_at=now - timedelta(days=1))
        self._insert_review_log(mistake_id=older["id"], shown_at=now - timedelta(days=2), user_result="again")
        self._insert_review_log(mistake_id=newer["id"], shown_at=now - timedelta(days=1), user_result="good")

        status, payload, _ = self.request("GET", "/api/v1/stats/trend")

        self.assertEqual(status, 200, payload)
        dates = [item["date"] for item in payload["items"]]
        self.assertEqual(payload["range"]["bucket"], "day")
        self.assertIn("from", payload["range"])
        self.assertIn("to", payload["range"])
        self.assertNotIn("from_date", payload["range"])
        self.assertNotIn("to_date", payload["range"])
        self.assertEqual(len(payload["items"]), 30)
        self.assertEqual(dates, sorted(dates))

    def test_overview_returns_streak_for_consecutive_three_local_days(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(category_id=category["id"], title="连续三天复习")
        now = datetime.now(timezone.utc).replace(microsecond=0, hour=12, minute=0, second=0)
        for days_ago in range(3):
            self._insert_review_log(mistake_id=mistake["id"], shown_at=now - timedelta(days=days_ago))

        status, payload, _ = self.request("GET", "/api/v1/stats/overview")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["streak_days"], 3)

    def test_overview_differs_between_utc_and_utc_plus_eight(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(category_id=category["id"], title="UTC 日界线差异")
        boundary_log, _, _ = self._utc_vs_utc8_boundary_case()
        self._insert_review_log(mistake_id=mistake["id"], shown_at=boundary_log, user_result="again")

        _, utc_payload, _ = self.request("GET", "/api/v1/stats/overview?tz_offset_minutes=0")
        _, utc8_payload, _ = self.request("GET", "/api/v1/stats/overview?tz_offset_minutes=480")

        self.assertNotEqual(utc_payload["reviewed_today"], utc8_payload["reviewed_today"])

    def test_heatmap_returns_zero_cells_for_empty_database(self) -> None:
        status, payload, _ = self.request("GET", "/api/v1/stats/heatmap")

        self.assertEqual(status, 200, payload)
        self.assertIn("from", payload["range"])
        self.assertIn("to", payload["range"])
        self.assertNotIn("from_date", payload["range"])
        self.assertNotIn("to_date", payload["range"])
        self.assertEqual(payload["max_count"], 0)
        self.assertEqual(len(payload["cells"]), 90)
        self.assertTrue(all(cell["count"] == 0 and cell["level"] == 0 for cell in payload["cells"]))

    def test_heatmap_level_mapping_uses_max_count_scale(self) -> None:
        category = self._create_category()
        mistake = self._create_mistake(category_id=category["id"], title="热力图等级")
        now = datetime.now(timezone.utc).replace(microsecond=0, hour=12, minute=0, second=0)
        for days_ago in range(3):
            self._insert_review_log(mistake_id=mistake["id"], shown_at=now - timedelta(days=days_ago))

        status, payload, _ = self.request("GET", "/api/v1/stats/heatmap?days=3")

        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["max_count"], 1)
        self.assertEqual([cell["count"] for cell in payload["cells"]], [1, 1, 1])
        self.assertEqual([cell["level"] for cell in payload["cells"]], [4, 4, 4])

    def test_top_weak_sorts_items_by_weak_score_desc(self) -> None:
        category = self._create_category()
        stronger = self._create_mistake(category_id=category["id"], title="更弱的题")
        weaker = self._create_mistake(category_id=category["id"], title="次弱的题")
        now = datetime.now(timezone.utc).replace(microsecond=0)

        self._update_mistake(stronger["id"], next_review_at=now - timedelta(days=4), ease_factor=1.9)
        self._update_mistake(weaker["id"], next_review_at=now - timedelta(days=1), ease_factor=2.2)

        self._insert_review_log(mistake_id=stronger["id"], shown_at=now - timedelta(days=1), user_result="again")
        self._insert_review_log(mistake_id=stronger["id"], shown_at=now - timedelta(hours=10), user_result="again")
        self._insert_review_log(mistake_id=weaker["id"], shown_at=now - timedelta(days=1), user_result="hard")

        status, payload, _ = self.request("GET", "/api/v1/stats/top-weak?limit=2&days=30")

        self.assertEqual(status, 200, payload)
        self.assertEqual([item["title"] for item in payload["items"]], ["更弱的题", "次弱的题"])
        self.assertGreater(payload["items"][0]["weak_score"], payload["items"][1]["weak_score"])

    def test_top_weak_only_includes_items_reviewed_within_requested_days(self) -> None:
        category = self._create_category()
        recent = self._create_mistake(category_id=category["id"], title="最近复习")
        stale = self._create_mistake(category_id=category["id"], title="过期日志")
        now = datetime.now(timezone.utc).replace(microsecond=0)

        self._insert_review_log(mistake_id=recent["id"], shown_at=now - timedelta(days=3), user_result="again")
        self._insert_review_log(mistake_id=stale["id"], shown_at=now - timedelta(days=40), user_result="again")

        status, payload, _ = self.request("GET", "/api/v1/stats/top-weak?days=30")

        self.assertEqual(status, 200, payload)
        self.assertEqual([item["title"] for item in payload["items"]], ["最近复习"])
