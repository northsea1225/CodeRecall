from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.test_api_contract_day3 import APIServerTestCase


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.init_db import initialize_database
from app.db.session import _connect_args
from app.models import Category, Mistake, ReviewLog, ReviewResult, ReviewSession, ReviewSessionItem, Tag, User
from app.services.import_export_service import export_data_v3, import_data_v3


class ExportDataV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{Path(self.tempdir.name) / 'export-v3.db'}"
        initialize_database(self.database_url, force_fallback=True)
        self.engine = create_engine(self.database_url, connect_args=_connect_args(self.database_url))
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.tempdir.cleanup()

    def _old_user_id(self, db) -> int:
        user_id = db.query(User.id).filter(User.username == "old_user").scalar()
        self.assertIsNotNone(user_id)
        return user_id

    def _seed_review_graph(self) -> tuple[int, int]:
        with self.SessionLocal() as db:
            user_id = self._old_user_id(db)
            category = Category(user_id=user_id, name="数组", description="数组与哈希")
            tag_a = Tag(user_id=user_id, name="哈希")
            tag_b = Tag(user_id=user_id, name="边界")
            db.add_all([category, tag_a, tag_b])
            db.flush()

            first = Mistake(
                user_id=user_id,
                title="两数之和补数顺序错",
                stem_markdown="给定 nums 和 target",
                wrong_answer_markdown="for i in nums: pass",
                correct_answer_markdown="seen = {}",
                error_reason_markdown="先插入后查询导致漏判",
                language="python",
                difficulty=2,
                source="LeetCode",
                category_id=category.id,
            )
            first.tags = [tag_a, tag_b]

            second = Mistake(
                user_id=user_id,
                title="滑动窗口收缩条件错",
                stem_markdown="最短覆盖子串",
                wrong_answer_markdown="left += 1",
                correct_answer_markdown="while matched == need: ...",
                error_reason_markdown="窗口满足条件时没有持续收缩",
                language="javascript",
                difficulty=3,
                source="LeetCode",
                category_id=category.id,
            )
            second.tags = [tag_b]
            db.add_all([first, second])
            db.flush()

            session = ReviewSession(
                user_id=user_id,
                started_at=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
                ended_at=datetime(2026, 4, 23, 12, 10, tzinfo=timezone.utc),
                strategy="random",
                total_count=2,
                completed_count=1,
            )
            db.add(session)
            db.flush()

            db.add_all(
                [
                    ReviewSessionItem(session_id=session.id, mistake_id=first.id, order_index=0),
                    ReviewSessionItem(session_id=session.id, mistake_id=second.id, order_index=1),
                    ReviewLog(
                        user_id=user_id,
                        mistake_id=first.id,
                        session_id=session.id,
                        review_mode="manual",
                        user_result=ReviewResult.GOOD,
                        shown_at=datetime(2026, 4, 23, 12, 1, tzinfo=timezone.utc),
                        answered_at=datetime(2026, 4, 23, 12, 2, tzinfo=timezone.utc),
                        old_interval_days=0,
                        new_interval_days=1,
                        old_ease_factor=2.5,
                        new_ease_factor=2.6,
                        time_spent_ms=12000,
                        note="首轮通过",
                    ),
                    ReviewLog(
                        user_id=user_id,
                        mistake_id=second.id,
                        session_id=session.id,
                        review_mode="manual",
                        user_result=ReviewResult.AGAIN,
                        shown_at=datetime(2026, 4, 23, 12, 3, tzinfo=timezone.utc),
                        answered_at=None,
                        old_interval_days=1,
                        new_interval_days=0,
                        old_ease_factor=2.4,
                        new_ease_factor=2.1,
                        time_spent_ms=None,
                        note="",
                    ),
                ]
            )
            db.commit()
            return first.id, second.id

    def _make_target_session_local(self, name: str = "import-v3.db"):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        database_url = f"sqlite:///{Path(tempdir.name) / name}"
        initialize_database(database_url, force_fallback=True)
        engine = create_engine(database_url, connect_args=_connect_args(database_url))
        self.addCleanup(engine.dispose)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def _export_seeded_payload(self):
        self._seed_review_graph()
        with self.SessionLocal() as db:
            return export_data_v3(db)

    def test_export_data_v3_contains_uuid_review_links_and_expected_shape(self) -> None:
        first_id, second_id = self._seed_review_graph()

        with self.SessionLocal() as db:
            payload = export_data_v3(db)

        self.assertEqual(payload.format, "coderecall")
        self.assertEqual(payload.schema_version, 3)
        self.assertEqual(len(payload.categories), 1)
        self.assertEqual(len(payload.tags), 2)
        self.assertEqual(len(payload.mistakes), 2)
        self.assertEqual(len(payload.review_sessions), 1)
        self.assertEqual(len(payload.review_session_items), 2)
        self.assertEqual(len(payload.review_logs), 2)

        uuids = [mistake.uuid for mistake in payload.mistakes]
        self.assertEqual(len(uuids), len(set(uuids)))
        self.assertTrue(all(uuid_value for uuid_value in uuids))

        exported_by_legacy_id = {mistake.legacy_id: mistake for mistake in payload.mistakes}
        self.assertEqual(exported_by_legacy_id[first_id].category_name, "数组")
        self.assertEqual(sorted(exported_by_legacy_id[first_id].tag_names), ["哈希", "边界"])
        self.assertEqual(sorted(exported_by_legacy_id[second_id].tag_names), ["边界"])

        uuid_by_legacy_id = {mistake.legacy_id: mistake.uuid for mistake in payload.mistakes}
        self.assertEqual(
            [item.mistake_uuid for item in payload.review_session_items],
            [uuid_by_legacy_id[first_id], uuid_by_legacy_id[second_id]],
        )
        self.assertEqual(
            [log.mistake_uuid for log in payload.review_logs],
            [uuid_by_legacy_id[first_id], uuid_by_legacy_id[second_id]],
        )
        self.assertEqual(payload.review_logs[0].user_result, "good")
        self.assertEqual(payload.review_logs[0].note, "首轮通过")
        self.assertEqual(payload.review_logs[1].user_result, "again")

    def test_mistake_uuid_column_is_backed_by_per_user_unique_index(self) -> None:
        self._seed_review_graph()
        database_path = self.database_url.removeprefix("sqlite:///")

        with sqlite3.connect(database_path) as conn:
            uuid_rows = conn.execute("SELECT uuid FROM mistakes ORDER BY id").fetchall()
            indexes = conn.execute("PRAGMA index_list('mistakes')").fetchall()
            index_columns = conn.execute("PRAGMA index_info('ix_mistakes_user_uuid')").fetchall()

        uuid_values = [row[0] for row in uuid_rows]
        self.assertEqual(len(uuid_values), len(set(uuid_values)))
        self.assertTrue(all(uuid_values))
        self.assertTrue(any(index[1] == "ix_mistakes_user_uuid" and index[2] == 1 for index in indexes))
        self.assertEqual([column[2] for column in index_columns], ["user_id", "uuid"])

    def test_round_trip_imports_full_review_graph(self) -> None:
        payload = self._export_seeded_payload()
        original_session_id = payload.review_sessions[0].id
        TargetSessionLocal = self._make_target_session_local()

        with TargetSessionLocal() as db:
            user_id = self._old_user_id(db)
            db.add(ReviewSession(user_id=user_id, strategy="placeholder", total_count=0, completed_count=0))
            db.commit()

        with TargetSessionLocal() as db:
            result = import_data_v3(db, payload, "skip_existing", user_id=self._old_user_id(db))

        self.assertEqual(result.imported.mistakes, 2)
        self.assertEqual(result.imported.review_sessions, 1)
        self.assertEqual(result.imported.review_session_items, 2)
        self.assertEqual(result.imported.review_logs, 2)

        with TargetSessionLocal() as db:
            mistakes = db.query(Mistake).order_by(Mistake.id).all()
            sessions = db.query(ReviewSession).filter(ReviewSession.strategy == "random").all()
            items = db.query(ReviewSessionItem).order_by(ReviewSessionItem.order_index).all()
            logs = db.query(ReviewLog).order_by(ReviewLog.shown_at).all()

        self.assertEqual([mistake.uuid for mistake in mistakes], [mistake.uuid for mistake in payload.mistakes])
        self.assertEqual(len(sessions), 1)
        self.assertNotEqual(sessions[0].id, original_session_id)
        self.assertEqual([item.session_id for item in items], [sessions[0].id, sessions[0].id])
        self.assertEqual([log.session_id for log in logs], [sessions[0].id, sessions[0].id])
        self.assertEqual([log.user_result for log in logs], [ReviewResult.GOOD, ReviewResult.AGAIN])

    def test_second_import_is_idempotent(self) -> None:
        payload = self._export_seeded_payload()
        TargetSessionLocal = self._make_target_session_local()

        with TargetSessionLocal() as db:
            first_result = import_data_v3(db, payload, "skip_existing", user_id=self._old_user_id(db))
        with TargetSessionLocal() as db:
            second_result = import_data_v3(db, payload, "skip_existing", user_id=self._old_user_id(db))

        self.assertEqual(first_result.imported.mistakes, 2)
        self.assertEqual(second_result.imported.mistakes, 0)
        self.assertEqual(second_result.imported.review_sessions, 0)
        self.assertEqual(second_result.imported.review_logs, 0)

        with TargetSessionLocal() as db:
            self.assertEqual(db.query(Mistake).count(), 2)
            self.assertEqual(db.query(ReviewSession).count(), 1)
            self.assertEqual(db.query(ReviewLog).count(), 2)

    def test_skip_review_records_with_missing_mistake_uuid(self) -> None:
        payload = self._export_seeded_payload()
        payload.review_logs[0].mistake_uuid = None
        payload.review_session_items[0].mistake_uuid = None
        TargetSessionLocal = self._make_target_session_local()

        with TargetSessionLocal() as db:
            result = import_data_v3(db, payload, "skip_existing", user_id=self._old_user_id(db))

        self.assertEqual(result.imported.mistakes, 2)
        self.assertEqual(result.imported.review_logs, 1)
        self.assertEqual(result.imported.review_session_items, 1)
        skipped_reasons = {(skip.entity, skip.reason) for skip in result.skipped}
        self.assertIn(("review_log", "missing_mistake_uuid"), skipped_reasons)
        self.assertIn(("review_session_item", "missing_mistake_uuid"), skipped_reasons)

    def test_skip_log_with_invalid_user_result(self) -> None:
        payload = self._export_seeded_payload()
        payload.review_logs[0].user_result = "INVALID_VALUE"
        TargetSessionLocal = self._make_target_session_local()

        with TargetSessionLocal() as db:
            result = import_data_v3(db, payload, "skip_existing", user_id=self._old_user_id(db))

        self.assertEqual(result.imported.mistakes, 2)
        self.assertEqual(result.imported.review_logs, 1)
        self.assertIn(
            ("review_log", "invalid_user_result"),
            {(skip.entity, skip.reason) for skip in result.skipped},
        )

    def test_log_with_null_session_id_is_imported(self) -> None:
        payload = self._export_seeded_payload()
        payload.review_logs[0].session_id = None
        TargetSessionLocal = self._make_target_session_local()

        with TargetSessionLocal() as db:
            result = import_data_v3(db, payload, "skip_existing", user_id=self._old_user_id(db))

        self.assertEqual(result.imported.review_logs, 2)
        self.assertNotIn(
            ("review_log", "missing_session"),
            {(skip.entity, skip.reason) for skip in result.skipped},
        )

        with TargetSessionLocal() as db:
            null_session_logs = db.query(ReviewLog).filter(ReviewLog.session_id.is_(None)).count()
        self.assertEqual(null_session_logs, 1)


class ExportV3RouteTests(APIServerTestCase):
    def test_export_v3_route_returns_attachment_payload(self) -> None:
        status, category, _ = self.request(
            "POST",
            "/api/v1/categories",
            {
                "name": "树",
                "description": "树与递归",
            },
        )
        self.assertEqual(status, 201, category)

        status, mistake, _ = self.request(
            "POST",
            "/api/v1/mistakes",
            {
                "title": "二叉树递归终止条件漏掉空节点",
                "stem_markdown": "给定一棵树",
                "wrong_answer_markdown": "dfs(node.left)",
                "correct_answer_markdown": "if not node: return",
                "error_reason_markdown": "缺少空节点返回",
                "language": "python",
                "difficulty": 2,
                "source": "LeetCode",
                "status": "new",
                "category_id": category["id"],
                "tags": ["递归"],
            },
        )
        self.assertEqual(status, 201, mistake)

        status, payload, headers = self.request("GET", "/api/v1/export/v3")
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["format"], "coderecall")
        self.assertEqual(payload["schema_version"], 3)
        self.assertIn("mistakes", payload)
        self.assertIn("review_sessions", payload)
        self.assertIn("review_session_items", payload)
        self.assertIn("review_logs", payload)
        self.assertEqual(len(payload["mistakes"]), 1)
        self.assertEqual(payload["mistakes"][0]["legacy_id"], mistake["id"])
        self.assertTrue(payload["mistakes"][0]["uuid"])
        normalized_headers = {key.lower(): value for key, value in headers.items()}
        self.assertIn("coderecall-v3-", normalized_headers.get("content-disposition", ""))

        encoded = json.dumps(payload)
        self.assertIn("\"schema_version\": 3", encoded)


if __name__ == "__main__":
    unittest.main()
