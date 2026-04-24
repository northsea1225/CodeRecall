from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import MagicMock, patch

from app.services import prompt_templates as prompt_templates_module
from app.services.prompt_templates import (
    ReviewStage,
    _compute_review_stage,
    _is_lapsed,
    _is_oscillator,
    _language_focus,
    _result_polarity,
    _xml_list,
    _xml_text,
)

try:
    from app.services.prompt_templates import build_mistake_prompt_input
except ImportError:
    from app.services.ai_analysis_service import build_mistake_prompt_input


def _freeze_prompt_now(fixed_now: datetime):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    return patch.object(prompt_templates_module, "datetime", FrozenDateTime)


class TestResultPolarity(unittest.TestCase):
    def test_weak_results(self) -> None:
        self.assertEqual(_result_polarity("again"), "weak")
        self.assertEqual(_result_polarity("hard"), "weak")

    def test_strong_results(self) -> None:
        self.assertEqual(_result_polarity("good"), "strong")
        self.assertEqual(_result_polarity("easy"), "strong")

    def test_unknown_and_empty_results(self) -> None:
        self.assertIsNone(_result_polarity("fair"))
        self.assertIsNone(_result_polarity(""))


class TestIsLapsed(unittest.TestCase):
    def test_none_input_returns_false(self) -> None:
        self.assertFalse(_is_lapsed(None))

    def test_more_than_30_days_ago_returns_true(self) -> None:
        fixed_now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        with _freeze_prompt_now(fixed_now):
            self.assertTrue(_is_lapsed(fixed_now - timedelta(days=30, seconds=1)))

    def test_less_than_30_days_ago_returns_false(self) -> None:
        fixed_now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        with _freeze_prompt_now(fixed_now):
            self.assertFalse(_is_lapsed(fixed_now - timedelta(days=29, hours=23)))

    def test_exactly_30_days_ago_returns_false(self) -> None:
        fixed_now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        with _freeze_prompt_now(fixed_now):
            self.assertFalse(_is_lapsed(fixed_now - timedelta(days=30)))

    def test_naive_datetime_respects_30_day_rule(self) -> None:
        fixed_now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        with _freeze_prompt_now(fixed_now):
            self.assertTrue(_is_lapsed(datetime(2026, 3, 21, 11, 59, 59)))
            self.assertFalse(_is_lapsed(datetime(2026, 3, 23, 12, 0)))


class TestIsOscillator(unittest.TestCase):
    def test_weak_strong_weak_returns_true(self) -> None:
        self.assertTrue(_is_oscillator(["again", "easy", "again"]))

    def test_strong_weak_strong_returns_true(self) -> None:
        self.assertTrue(_is_oscillator(["easy", "again", "easy"]))

    def test_fewer_than_3_known_polarities_returns_false(self) -> None:
        self.assertFalse(_is_oscillator(["again", "easy"]))

    def test_empty_list_returns_false(self) -> None:
        self.assertFalse(_is_oscillator([]))

    def test_unknown_entries_are_ignored_when_remaining_entries_alternate(self) -> None:
        self.assertTrue(_is_oscillator(["fair", "again", "easy", "fair", "hard"]))

    def test_unknown_entries_reduce_known_count_below_3(self) -> None:
        self.assertFalse(_is_oscillator(["fair", "again", "easy"]))

    def test_adjacent_same_polarity_returns_false(self) -> None:
        self.assertFalse(_is_oscillator(["again", "again", "easy"]))

    def test_4_or_more_alternating_known_polarities_returns_true(self) -> None:
        self.assertTrue(_is_oscillator(["again", "easy", "hard", "good"]))


class TestComputeReviewStage(unittest.TestCase):
    def test_count_zero_returns_new_mistake_even_if_lapsed(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(days=31)
        self.assertEqual(
            _compute_review_stage(0, [], old),
            ReviewStage.NEW_MISTAKE,
        )

    def test_count_zero_returns_new_mistake_even_if_repeated_weakness(self) -> None:
        self.assertEqual(
            _compute_review_stage(0, ["again", "hard"], datetime.now(timezone.utc)),
            ReviewStage.NEW_MISTAKE,
        )

    def test_lapsed_beats_repeated_weakness(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(days=31)
        self.assertEqual(
            _compute_review_stage(2, ["again", "hard"], old),
            ReviewStage.LAPSED,
        )

    def test_lapsed_beats_oscillator(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(days=31)
        self.assertEqual(
            _compute_review_stage(2, ["again", "easy", "again"], old),
            ReviewStage.LAPSED,
        )

    def test_repeated_weakness_beats_oscillator(self) -> None:
        self.assertEqual(
            _compute_review_stage(2, ["again", "easy", "hard"], datetime.now(timezone.utc)),
            ReviewStage.REPEATED_WEAKNESS,
        )

    def test_weak_count_two_without_lapsed_or_oscillator_returns_repeated_weakness(self) -> None:
        self.assertEqual(
            _compute_review_stage(3, ["again", "hard", "easy"], datetime.now(timezone.utc)),
            ReviewStage.REPEATED_WEAKNESS,
        )

    def test_oscillator_without_lapsed_or_repeated_weakness_returns_oscillator(self) -> None:
        self.assertEqual(
            _compute_review_stage(3, ["easy", "again", "good"], datetime.now(timezone.utc)),
            ReviewStage.OSCILLATOR,
        )

    def test_count_one_without_lapsed_returns_early_review(self) -> None:
        self.assertEqual(
            _compute_review_stage(1, [], datetime.now(timezone.utc)),
            ReviewStage.EARLY_REVIEW,
        )

    def test_count_five_without_special_conditions_returns_maintenance(self) -> None:
        self.assertEqual(
            _compute_review_stage(5, ["good", "easy"], datetime.now(timezone.utc)),
            ReviewStage.MAINTENANCE,
        )


class TestXmlText(unittest.TestCase):
    def test_escapes_special_xml_characters(self) -> None:
        self.assertEqual(_xml_text("value", "<"), "<value>&lt;</value>")
        self.assertEqual(_xml_text("value", ">"), "<value>&gt;</value>")
        self.assertEqual(_xml_text("value", "&"), "<value>&amp;</value>")

    def test_none_value_produces_empty_text_between_tags(self) -> None:
        self.assertEqual(_xml_text("value", None), "<value></value>")

    def test_tag_and_content_are_wrapped(self) -> None:
        self.assertEqual(_xml_text("title", "Two Sum"), "<title>Two Sum</title>")


class TestXmlList(unittest.TestCase):
    def test_normal_list_produces_parent_and_child_tags(self) -> None:
        self.assertEqual(
            _xml_list("tags", "tag", ["dp", "graph"]),
            "<tags><tag>dp</tag><tag>graph</tag></tags>",
        )

    def test_each_item_is_xml_escaped(self) -> None:
        self.assertEqual(
            _xml_list("tags", "tag", ["a&b", "x<y"]),
            "<tags><tag>a&amp;b</tag><tag>x&lt;y</tag></tags>",
        )

    def test_empty_list_produces_parent_tag_with_no_child_items(self) -> None:
        self.assertEqual(_xml_list("tags", "tag", []), "<tags></tags>")

    def test_script_content_is_escaped(self) -> None:
        self.assertEqual(
            _xml_list("items", "item", ["<script>"]),
            "<items><item>&lt;script&gt;</item></items>",
        )


class TestLanguageFocus(unittest.TestCase):
    def test_algorithm_mentions_time_complexity(self) -> None:
        self.assertIn("时间复杂度", _language_focus("algorithm"))

    def test_javascript_mentions_promise(self) -> None:
        self.assertIn("Promise", _language_focus("javascript"))

    def test_python_mentions_mutable_defaults(self) -> None:
        self.assertIn("可变默认值", _language_focus("python"))

    def test_cpp_variants_match_cpp_hint(self) -> None:
        for language in ("c++", "cpp", "C++"):
            with self.subTest(language=language):
                hint = _language_focus(language)
                self.assertIn("C++ 竞赛", hint)

    def test_exact_c_matches_c_hint_not_cpp(self) -> None:
        hint = _language_focus("c")
        self.assertIn("按 C 题", hint)
        self.assertNotIn("C++", hint)

    def test_csharp_falls_through_to_generic_hint(self) -> None:
        hint = _language_focus("c#")
        self.assertIn("通用编程题", hint)
        self.assertNotIn("按 C 题", hint)
        self.assertNotIn("C++ 竞赛", hint)


class TestBuildMistakePromptInput(unittest.TestCase):
    def _named(self, name: str):
        obj = MagicMock()
        obj.name = name
        return obj

    def _log(
        self,
        *,
        at: datetime | None,
        result: object | None = None,
        note: str | None = None,
        shown_at: datetime | None = None,
    ):
        log = MagicMock()
        log.answered_at = at
        log.shown_at = shown_at
        log.user_result = result
        log.note = note
        return log

    def _mistake(
        self,
        *,
        review_count: int = 0,
        last_reviewed_at: datetime | None = None,
        review_logs: list[object] | None = None,
    ):
        mistake = MagicMock()
        mistake.title = "Two Sum"
        mistake.language = "python"
        mistake.difficulty = 2
        mistake.category = self._named("Array")
        mistake.tags = [self._named("hash"), self._named("implementation")]
        mistake.stem_markdown = "Find pair"
        mistake.wrong_answer_markdown = "wrong"
        mistake.correct_answer_markdown = "correct"
        mistake.error_reason_markdown = "off by one"
        mistake.review_count = review_count
        mistake.last_reviewed_at = last_reviewed_at
        mistake.review_logs = review_logs or []
        return mistake

    def test_empty_review_logs_use_stored_review_fields(self) -> None:
        mistake = self._mistake(review_count=3, last_reviewed_at=None, review_logs=[])

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["review_count"], 3)
        self.assertEqual(data["recent_review_results"], [])
        self.assertEqual(data["recent_review_notes"], [])
        self.assertIsNone(data["last_review_result"])
        self.assertIsNone(data["last_reviewed_at"])

    def test_stored_count_beats_shorter_log_count(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        logs = [
            self._log(at=base, result="again"),
            self._log(at=base - timedelta(days=1), result="good"),
        ]
        mistake = self._mistake(review_count=5, review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["review_count"], 5)

    def test_log_count_beats_smaller_stored_count(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        logs = [
            self._log(at=base - timedelta(days=offset), result="good")
            for offset in range(4)
        ]
        mistake = self._mistake(review_count=1, review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["review_count"], 4)

    def test_string_result_is_extracted(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        mistake = self._mistake(review_logs=[self._log(at=base, result="again")])

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["recent_review_results"], ["again"])
        self.assertEqual(data["last_review_result"], "again")

    def test_enum_like_result_value_is_extracted(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        enum_result = MagicMock()
        enum_result.value = "good"
        mistake = self._mistake(review_logs=[self._log(at=base, result=enum_result)])

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["recent_review_results"], ["good"])
        self.assertEqual(data["last_review_result"], "good")

    def test_recent_results_take_up_to_3_most_recent_non_none_results(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        logs = [
            self._log(at=base - timedelta(minutes=3), result="hard"),
            self._log(at=base, result="easy"),
            self._log(at=base - timedelta(minutes=1), result="good"),
            self._log(at=base - timedelta(minutes=2), result="again"),
            self._log(at=base - timedelta(minutes=4), result=None),
        ]
        mistake = self._mistake(review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["recent_review_results"], ["easy", "good", "again"])

    def test_recent_notes_take_up_to_2_most_recent_non_empty_notes(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        logs = [
            self._log(at=base - timedelta(minutes=2), result="again", note="older"),
            self._log(at=base, result="good", note="newer"),
            self._log(at=base - timedelta(minutes=1), result="hard", note="middle"),
        ]
        mistake = self._mistake(review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["recent_review_notes"], ["newer", "middle"])

    def test_empty_string_note_is_skipped(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        logs = [
            self._log(at=base, result="good", note="kept"),
            self._log(at=base - timedelta(minutes=1), result="hard", note=""),
        ]
        mistake = self._mistake(review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["recent_review_notes"], ["kept"])

    def test_logs_are_sorted_by_time_most_recent_first(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        older = self._log(at=base - timedelta(days=2), result="again", note="older")
        newer = self._log(at=base, result="easy", note="newer")
        middle = self._log(at=base - timedelta(days=1), result="hard", note="middle")
        mistake = self._mistake(review_logs=[older, newer, middle])

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["recent_review_results"], ["easy", "hard", "again"])
        self.assertEqual(data["recent_review_notes"], ["newer", "middle"])
        self.assertEqual(data["last_review_result"], "easy")

    def test_latest_reviewed_at_uses_stored_when_it_is_larger(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        stored = base + timedelta(hours=1)
        logs = [self._log(at=base, result="good")]
        mistake = self._mistake(last_reviewed_at=stored, review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["last_reviewed_at"], stored)

    def test_latest_reviewed_at_uses_latest_log_when_it_is_larger(self) -> None:
        base = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        stored = base - timedelta(days=1)
        logs = [self._log(at=base, result="good")]
        mistake = self._mistake(last_reviewed_at=stored, review_logs=logs)

        data = build_mistake_prompt_input(mistake)

        self.assertEqual(data["last_reviewed_at"], base)


if __name__ == "__main__":
    unittest.main()
