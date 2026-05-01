import unittest

from app.schemas.mistake import MistakeListOut, MistakeOut


_LARGE_MARKDOWN_FIELDS = (
    "stem_markdown",
    "wrong_answer_markdown",
    "correct_answer_markdown",
    "error_reason_markdown",
)


class MistakeListOutShapeTests(unittest.TestCase):
    def test_list_schema_excludes_large_markdown_fields(self) -> None:
        # The whole point of MistakeListOut: keep list responses small by
        # stripping the 4 markdown fields that account for >80% of payload.
        for field in _LARGE_MARKDOWN_FIELDS:
            self.assertNotIn(
                field,
                MistakeListOut.model_fields,
                f"MistakeListOut should not surface {field}; full record is at /mistakes/{{id}}",
            )

    def test_full_schema_still_contains_large_markdown_fields(self) -> None:
        # MistakeOut (used by /mistakes/{id} and create/update routes) must
        # keep returning the full record.
        for field in _LARGE_MARKDOWN_FIELDS:
            self.assertIn(field, MistakeOut.model_fields)

    def test_list_schema_keeps_category_and_tags_for_frontend_compat(self) -> None:
        # Frontend list view reads record.category.name and may read tags;
        # keep the nested category and list[TagOut] so the existing rendering
        # contract isn't broken.
        self.assertIn("category", MistakeListOut.model_fields)
        self.assertIn("tags", MistakeListOut.model_fields)


if __name__ == "__main__":
    unittest.main()
