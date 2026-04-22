import unittest

from pydantic import ValidationError

from app.schemas.mistake import MistakeCreate, MistakeUpdate
from app.schemas.mistake_constraints import (
    MAX_ERROR_REASON_LEN,
    MAX_LANGUAGE_LEN,
    MAX_MARKDOWN_LEN,
    MAX_SOURCE_LEN,
    MAX_TITLE_LEN,
)


def _base_create(**overrides) -> dict:
    base = {
        "title": "A" * MAX_TITLE_LEN,
        "stem_markdown": "A" * MAX_MARKDOWN_LEN,
        "wrong_answer_markdown": "A" * MAX_MARKDOWN_LEN,
        "correct_answer_markdown": "A" * MAX_MARKDOWN_LEN,
        "error_reason_markdown": "A" * MAX_ERROR_REASON_LEN,
        "language": "python",
        "difficulty": 3,
        "source": "",
        "category_id": 1,
        "tags": [],
    }
    base.update(overrides)
    return base


class TestMistakeCreateLimits(unittest.TestCase):
    def test_title_at_max_passes(self):
        MistakeCreate(**_base_create())

    def test_title_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(title="A" * (MAX_TITLE_LEN + 1)))

    def test_stem_markdown_at_max_passes(self):
        MistakeCreate(**_base_create())

    def test_stem_markdown_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(stem_markdown="A" * (MAX_MARKDOWN_LEN + 1)))

    def test_wrong_answer_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(wrong_answer_markdown="A" * (MAX_MARKDOWN_LEN + 1)))

    def test_correct_answer_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(correct_answer_markdown="A" * (MAX_MARKDOWN_LEN + 1)))

    def test_error_reason_at_max_passes(self):
        MistakeCreate(**_base_create(error_reason_markdown="A" * MAX_ERROR_REASON_LEN))

    def test_error_reason_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(error_reason_markdown="A" * (MAX_ERROR_REASON_LEN + 1)))

    def test_language_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(language="x" * (MAX_LANGUAGE_LEN + 1)))

    def test_source_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeCreate(**_base_create(source="x" * (MAX_SOURCE_LEN + 1)))


class TestMistakeUpdateLimits(unittest.TestCase):
    def test_all_none_passes(self):
        MistakeUpdate()

    def test_title_none_passes(self):
        MistakeUpdate(title=None)

    def test_title_at_max_passes(self):
        MistakeUpdate(title="A" * MAX_TITLE_LEN)

    def test_title_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeUpdate(title="A" * (MAX_TITLE_LEN + 1))

    def test_stem_markdown_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeUpdate(stem_markdown="A" * (MAX_MARKDOWN_LEN + 1))

    def test_error_reason_over_max_fails(self):
        with self.assertRaises(ValidationError):
            MistakeUpdate(error_reason_markdown="A" * (MAX_ERROR_REASON_LEN + 1))


if __name__ == "__main__":
    unittest.main()
