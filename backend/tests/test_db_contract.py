import tempfile
import unittest
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class DatabaseContractTests(unittest.TestCase):
    def test_model_metadata_contains_expected_tables(self) -> None:
        from app.db.base import Base
        from app.models import (  # noqa: F401
            Category,
            Mistake,
            MistakeTag,
            ReviewLog,
            ReviewSession,
            Tag,
        )

        expected_tables = {
            "categories",
            "mistakes",
            "mistake_tags",
            "review_logs",
            "review_session_items",
            "review_sessions",
            "tags",
        }

        self.assertTrue(expected_tables.issubset(set(Base.metadata.tables)))

    def test_review_log_user_result_uses_non_native_enum(self) -> None:
        from sqlalchemy import Enum as SqlEnum

        from app.models.review import ReviewLog, ReviewResult

        column_type = ReviewLog.__table__.c.user_result.type
        self.assertIsInstance(column_type, SqlEnum)
        self.assertEqual(column_type.enum_class, ReviewResult)
        self.assertFalse(column_type.native_enum)

    def test_init_db_creates_sqlite_file_when_missing(self) -> None:
        from app.db.init_db import initialize_database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "contract-test.db"
            initialize_database(f"sqlite:///{db_path}", force_fallback=True)
            self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
