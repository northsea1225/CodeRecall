import unittest

from pydantic import ValidationError

from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.import_export import (
    ImportCategory,
    ImportMistake,
    ImportTag,
)
from app.schemas.tag import TagCreate, TagUpdate
from app.schemas.taxonomy_constraints import (
    CATEGORY_DESC_MAX,
    CATEGORY_NAME_MAX,
    TAG_NAME_MAX,
)


class CategoryCreateLimitsTests(unittest.TestCase):
    def test_blank_name_fails(self) -> None:
        with self.assertRaises(ValidationError):
            CategoryCreate(name="")

    def test_name_at_max_passes(self) -> None:
        CategoryCreate(name="A" * CATEGORY_NAME_MAX)

    def test_name_over_max_fails(self) -> None:
        with self.assertRaises(ValidationError):
            CategoryCreate(name="A" * (CATEGORY_NAME_MAX + 1))

    def test_description_over_max_fails(self) -> None:
        with self.assertRaises(ValidationError):
            CategoryCreate(name="ok", description="x" * (CATEGORY_DESC_MAX + 1))


class CategoryUpdateLimitsTests(unittest.TestCase):
    def test_blank_name_fails(self) -> None:
        with self.assertRaises(ValidationError):
            CategoryUpdate(name="")

    def test_name_over_max_fails(self) -> None:
        with self.assertRaises(ValidationError):
            CategoryUpdate(name="A" * (CATEGORY_NAME_MAX + 1))

    def test_none_name_passes(self) -> None:
        CategoryUpdate(name=None)


class TagSchemaLimitsTests(unittest.TestCase):
    def test_create_blank_name_fails(self) -> None:
        with self.assertRaises(ValidationError):
            TagCreate(name="")

    def test_create_name_over_max_fails(self) -> None:
        with self.assertRaises(ValidationError):
            TagCreate(name="A" * (TAG_NAME_MAX + 1))

    def test_create_name_at_max_passes(self) -> None:
        TagCreate(name="A" * TAG_NAME_MAX)

    def test_update_name_over_max_fails(self) -> None:
        with self.assertRaises(ValidationError):
            TagUpdate(name="A" * (TAG_NAME_MAX + 1))


class ImportSchemaLimitsTests(unittest.TestCase):
    def test_import_category_oversized_name_fails(self) -> None:
        with self.assertRaises(ValidationError):
            ImportCategory(name="A" * (CATEGORY_NAME_MAX + 1))

    def test_import_tag_oversized_name_fails(self) -> None:
        with self.assertRaises(ValidationError):
            ImportTag(name="A" * (TAG_NAME_MAX + 1))

    def test_import_mistake_oversized_category_name_fails(self) -> None:
        payload = {
            "title": "x",
            "stem_markdown": "x",
            "wrong_answer_markdown": "x",
            "correct_answer_markdown": "x",
            "error_reason_markdown": "x",
            "language": "python",
            "difficulty": 3,
            "category_name": "A" * (CATEGORY_NAME_MAX + 1),
        }
        with self.assertRaises(ValidationError):
            ImportMistake(**payload)

    def test_import_mistake_oversized_tag_name_fails(self) -> None:
        payload = {
            "title": "x",
            "stem_markdown": "x",
            "wrong_answer_markdown": "x",
            "correct_answer_markdown": "x",
            "error_reason_markdown": "x",
            "language": "python",
            "difficulty": 3,
            "category_name": "ok",
            "tag_names": ["A" * (TAG_NAME_MAX + 1)],
        }
        with self.assertRaises(ValidationError):
            ImportMistake(**payload)


if __name__ == "__main__":
    unittest.main()
