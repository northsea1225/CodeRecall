from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.review import ReviewResult
from app.services.review.scheduler import compute_next_schedule


FIXED_NOW = datetime(2026, 4, 27, 8, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("user_result", "ease_factor", "interval_days", "repetition", "expected"),
    [
        (
            ReviewResult.AGAIN,
            2.5,
            10,
            3,
            {"ease_factor": 1.7, "interval_days": 1, "repetition": 0},
        ),
        (
            ReviewResult.HARD,
            2.5,
            0,
            0,
            {"ease_factor": 2.36, "interval_days": 1, "repetition": 1},
        ),
        (
            ReviewResult.HARD,
            2.5,
            1,
            1,
            {"ease_factor": 2.36, "interval_days": 2, "repetition": 2},
        ),
        (
            ReviewResult.HARD,
            2.5,
            10,
            2,
            {"ease_factor": 2.36, "interval_days": 24, "repetition": 3},
        ),
        (
            ReviewResult.GOOD,
            2.5,
            0,
            0,
            {"ease_factor": 2.5, "interval_days": 1, "repetition": 1},
        ),
        (
            ReviewResult.GOOD,
            2.5,
            1,
            1,
            {"ease_factor": 2.5, "interval_days": 3, "repetition": 2},
        ),
        (
            ReviewResult.GOOD,
            2.5,
            7,
            2,
            {"ease_factor": 2.5, "interval_days": 18, "repetition": 3},
        ),
        (
            ReviewResult.EASY,
            2.5,
            0,
            0,
            {"ease_factor": 2.6, "interval_days": 4, "repetition": 1},
        ),
        (
            ReviewResult.EASY,
            2.5,
            4,
            1,
            {"ease_factor": 2.6, "interval_days": 6, "repetition": 2},
        ),
        (
            ReviewResult.EASY,
            2.5,
            6,
            2,
            {"ease_factor": 2.6, "interval_days": 20, "repetition": 3},
        ),
        (
            ReviewResult.HARD,
            1.31,
            10,
            4,
            {"ease_factor": 1.3, "interval_days": 13, "repetition": 5},
        ),
    ],
)
def test_compute_next_schedule_matches_expected_vectors(
    user_result: ReviewResult,
    ease_factor: float,
    interval_days: int,
    repetition: int,
    expected: dict[str, float | int],
) -> None:
    result = compute_next_schedule(
        user_result=user_result,
        ease_factor=ease_factor,
        interval_days=interval_days,
        repetition=repetition,
        now=FIXED_NOW,
    )

    assert result["ease_factor"] == pytest.approx(expected["ease_factor"], rel=0, abs=1e-6)
    assert result["interval_days"] == expected["interval_days"]
    assert result["repetition"] == expected["repetition"]
    assert result["next_review_at"] == FIXED_NOW + timedelta(days=int(expected["interval_days"]))


def test_compute_next_schedule_enforces_ease_factor_floor() -> None:
    result = compute_next_schedule(
        user_result=ReviewResult.AGAIN,
        ease_factor=1.31,
        interval_days=30,
        repetition=8,
        now=FIXED_NOW,
    )

    assert result["ease_factor"] == pytest.approx(1.3)
    assert result["interval_days"] == 1
    assert result["repetition"] == 0


def test_five_good_reviews_follow_expected_growth_curve() -> None:
    state = {
        "ease_factor": 2.5,
        "interval_days": 0,
        "repetition": 0,
    }
    intervals: list[int] = []

    for _ in range(5):
        state = compute_next_schedule(
            user_result=ReviewResult.GOOD,
            ease_factor=state["ease_factor"],
            interval_days=state["interval_days"],
            repetition=state["repetition"],
            now=FIXED_NOW,
        )
        intervals.append(state["interval_days"])

    assert intervals[:2] == [1, 3]
    assert 7 <= intervals[2] <= 8
    assert 17 <= intervals[3] <= 20
    assert 42 <= intervals[4] <= 50
