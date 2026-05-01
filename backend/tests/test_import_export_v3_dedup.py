from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.init_db import initialize_database
from app.db.session import _connect_args
from app.models import Category, Mistake, User
from app.schemas.import_export import ExportMistakeV3, ImportCategory, ImportPayloadV3
from app.services import import_export_service


def _make_export_v3(
    *,
    uuid_str: str | None,
    legacy_id: int,
    title: str = "x",
    category_name: str = "数组",
) -> ExportMistakeV3:
    now = datetime.now(timezone.utc)
    return ExportMistakeV3(
        uuid=uuid_str,
        legacy_id=legacy_id,
        title=title,
        stem_markdown="x",
        wrong_answer_markdown="x",
        correct_answer_markdown="x",
        error_reason_markdown="x",
        language="python",
        difficulty=3,
        source="",
        status="new",
        category_name=category_name,
        tag_names=[],
        ease_factor=2.5,
        interval_days=0,
        repetition=0,
        next_review_at=None,
        is_archived=False,
        created_at=now,
        updated_at=now,
    )


class ChunkedUuidLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{Path(self.tempdir.name) / 'dedup-v3.db'}"
        initialize_database(self.database_url, force_fallback=True)
        self.engine = create_engine(self.database_url, connect_args=_connect_args(self.database_url))
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.tempdir.cleanup()

    def _old_user_id(self, db) -> int:
        return db.query(User.id).filter(User.username == "old_user").scalar()

    def _seed_existing_mistakes(self, count: int) -> list[str]:
        with self.SessionLocal() as db:
            user_id = self._old_user_id(db)
            category = Category(user_id=user_id, name="数组")
            db.add(category)
            db.flush()

            uuids: list[str] = []
            now = datetime.now(timezone.utc)
            for i in range(count):
                uuid_str = f"{i:08x}-aaaa-bbbb-cccc-dddddddddddd"
                db.add(
                    Mistake(
                        user_id=user_id,
                        title=f"existing-{i}",
                        stem_markdown="x",
                        wrong_answer_markdown="x",
                        correct_answer_markdown="x",
                        error_reason_markdown="x",
                        language="python",
                        difficulty=3,
                        source="",
                        status="new",
                        category_id=category.id,
                        ease_factor=2.5,
                        interval_days=0,
                        repetition=0,
                        is_archived=False,
                        uuid=uuid_str,
                        created_at=now,
                        updated_at=now,
                    )
                )
                uuids.append(uuid_str)
            db.commit()
            return uuids

    @patch.object(import_export_service, "_MISTAKE_UUID_LOOKUP_CHUNK", 3)
    def test_chunked_lookup_finds_all_existing_above_chunk_size(self) -> None:
        # 7 incoming UUIDs all matching existing rows -> 3 chunks (3+3+1).
        # All 7 must be detected as already_exists across chunk boundaries.
        existing_uuids = self._seed_existing_mistakes(7)

        payload = ImportPayloadV3(
            categories=[ImportCategory(name="数组")],
            mistakes=[
                _make_export_v3(uuid_str=u, legacy_id=i + 100)
                for i, u in enumerate(existing_uuids)
            ],
        )

        with self.SessionLocal() as db:
            user_id = self._old_user_id(db)
            response = import_export_service.import_data_v3(
                db, payload, "skip_existing", user_id=user_id
            )

        skipped_uuids = {
            skip.identifier for skip in response.skipped if skip.entity == "mistake"
        }
        for u in existing_uuids:
            self.assertIn(u, skipped_uuids, f"UUID {u} not detected as already_exists")
        self.assertEqual(response.imported.mistakes, 0)

    @patch.object(import_export_service, "_MISTAKE_UUID_LOOKUP_CHUNK", 3)
    def test_duplicate_incoming_uuid_collapsed_in_lookup(self) -> None:
        # Same UUID appearing twice in payload must not blow up uniqueness
        # constraints during the new-mistake insert path. The first record
        # goes through; the second one targeting the same UUID must be
        # skipped with already_exists rather than triggering an
        # IntegrityError inside the chunk lookup.
        shared_uuid = "abcdef01-aaaa-bbbb-cccc-dddddddddddd"
        payload = ImportPayloadV3(
            categories=[ImportCategory(name="数组")],
            mistakes=[
                _make_export_v3(uuid_str=shared_uuid, legacy_id=1, title="first"),
                _make_export_v3(uuid_str=shared_uuid, legacy_id=2, title="second"),
            ],
        )

        with self.SessionLocal() as db:
            user_id = self._old_user_id(db)
            response = import_export_service.import_data_v3(
                db, payload, "skip_existing", user_id=user_id
            )

        # Exactly one mistake created; the duplicate is skipped.
        self.assertEqual(response.imported.mistakes, 1)
        skipped_uuids = [
            skip.identifier for skip in response.skipped if skip.entity == "mistake"
        ]
        self.assertEqual(skipped_uuids.count(shared_uuid), 1)

    @patch.object(import_export_service, "_MISTAKE_UUID_LOOKUP_CHUNK", 2)
    def test_chunk_boundary_does_not_drop_matches(self) -> None:
        # 4 incoming UUIDs split exactly on the chunk boundary (2+2). Both
        # the last UUID of chunk 1 and the first UUID of chunk 2 are
        # pre-existing; verify both are recognised.
        existing_uuids = self._seed_existing_mistakes(4)

        payload = ImportPayloadV3(
            categories=[ImportCategory(name="数组")],
            mistakes=[
                _make_export_v3(uuid_str=u, legacy_id=i + 200)
                for i, u in enumerate(existing_uuids)
            ],
        )

        with self.SessionLocal() as db:
            user_id = self._old_user_id(db)
            response = import_export_service.import_data_v3(
                db, payload, "skip_existing", user_id=user_id
            )

        self.assertEqual(response.imported.mistakes, 0)
        self.assertEqual(
            {skip.identifier for skip in response.skipped if skip.entity == "mistake"},
            set(existing_uuids),
        )


if __name__ == "__main__":
    unittest.main()
