from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.review import ReviewResult
from app.services.review.scheduler import compute_next_schedule


FIXED_NOW = datetime(2026, 4, 28, 8, 0, tzinfo=timezone.utc)


def test_again_at_floor_keeps_ease_factor_floor() -> None:
    result = compute_next_schedule(
        user_result=ReviewResult.AGAIN,
        ease_factor=1.3,
        interval_days=12,
        repetition=5,
        now=FIXED_NOW,
    )

    assert result["ease_factor"] == pytest.approx(1.3)
    assert result["interval_days"] == 1
    assert result["repetition"] == 0


def test_good_from_floor_recovers_ease_factor_slowly() -> None:
    result = compute_next_schedule(
        user_result=ReviewResult.GOOD,
        ease_factor=1.3,
        interval_days=1,
        repetition=1,
        now=FIXED_NOW,
    )

    assert result["ease_factor"] == pytest.approx(1.35)
    assert result["interval_days"] == 3
    assert result["repetition"] == 2


def test_repeated_good_reviews_raise_low_ease_factor_monotonically() -> None:
    state = {
        "ease_factor": 1.3,
        "interval_days": 1,
        "repetition": 1,
    }
    observed: list[float] = []

    for _ in range(4):
        state = compute_next_schedule(
            user_result=ReviewResult.GOOD,
            ease_factor=state["ease_factor"],
            interval_days=state["interval_days"],
            repetition=state["repetition"],
            now=FIXED_NOW,
        )
        observed.append(round(float(state["ease_factor"]), 2))

    assert observed == [1.35, 1.4, 1.45, 1.5]


def test_easy_recovers_low_ease_factor_faster_than_good() -> None:
    good = compute_next_schedule(
        user_result=ReviewResult.GOOD,
        ease_factor=1.3,
        interval_days=1,
        repetition=1,
        now=FIXED_NOW,
    )
    easy = compute_next_schedule(
        user_result=ReviewResult.EASY,
        ease_factor=1.3,
        interval_days=1,
        repetition=1,
        now=FIXED_NOW,
    )

    assert easy["ease_factor"] > good["ease_factor"]


def test_good_at_default_ease_factor_remains_stable() -> None:
    result = compute_next_schedule(
        user_result=ReviewResult.GOOD,
        ease_factor=2.5,
        interval_days=7,
        repetition=2,
        now=FIXED_NOW,
    )

    assert result["ease_factor"] == pytest.approx(2.5)
