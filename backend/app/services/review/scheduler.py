from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import ReviewResult


_QUALITY_MAP: dict[ReviewResult, int] = {
    ReviewResult.AGAIN: 0,
    ReviewResult.HARD: 3,
    ReviewResult.GOOD: 4,
    ReviewResult.EASY: 5,
}


def _coerce_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _next_ease_factor(user_result: ReviewResult, ease_factor: float) -> float:
    quality = _QUALITY_MAP[user_result]
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    next_value = max(1.3, ease_factor + delta)

    # 当 EF 已跌到低位时，good 评分允许其缓慢恢复，避免长期锁死在 1.3。
    if user_result == ReviewResult.GOOD and ease_factor < 2.5 and next_value <= ease_factor:
        return min(2.5, round(ease_factor + 0.05, 6))

    return next_value


def compute_next_schedule(
    user_result: ReviewResult,
    ease_factor: float = 2.5,
    interval_days: int = 0,
    repetition: int = 0,
    now: datetime | None = None,
) -> dict[str, datetime | float | int]:
    current_now = _coerce_utc(now)
    next_ease_factor = _next_ease_factor(user_result, ease_factor)

    if user_result == ReviewResult.AGAIN:
        next_repetition = 0
        next_interval_days = 1
    else:
        next_repetition = repetition + 1
        if repetition == 0:
            next_interval_days = 1 if user_result != ReviewResult.EASY else 4
        elif repetition == 1:
            if user_result == ReviewResult.HARD:
                next_interval_days = 2
            elif user_result == ReviewResult.GOOD:
                next_interval_days = 3
            else:
                next_interval_days = 6
        else:
            if user_result == ReviewResult.HARD:
                multiplier = max(ease_factor - 0.15, 1.3)
            elif user_result == ReviewResult.GOOD:
                multiplier = ease_factor
            else:
                multiplier = ease_factor * 1.3
            next_interval_days = max(1, int(round(interval_days * multiplier)))

    return {
        "ease_factor": next_ease_factor,
        "interval_days": next_interval_days,
        "repetition": next_repetition,
        "next_review_at": current_now + timedelta(days=next_interval_days),
    }
