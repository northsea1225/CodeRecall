from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.category import Category
from app.models.mistake import Mistake, MistakeStatus
from app.models.review import ReviewLog, ReviewResult
from app.schemas.stats import (
    StatsHeatmapCellOut,
    StatsHeatmapOut,
    StatsHeatmapRangeOut,
    StatsOverviewOut,
    StatsTagRadarItemOut,
    StatsTagRadarOut,
    StatsTopWeakItemOut,
    StatsTopWeakOut,
    StatsTrendItemOut,
    StatsTrendOut,
    StatsTrendRangeOut,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _local_timezone(tz_offset_minutes: int) -> timezone:
    return timezone(timedelta(minutes=tz_offset_minutes))


def _to_local_date(value: datetime, tz_offset_minutes: int) -> date:
    utc_value = _ensure_utc(value)
    assert utc_value is not None
    return utc_value.astimezone(_local_timezone(tz_offset_minutes)).date()


def _date_window(days: int, tz_offset_minutes: int, now: datetime | None = None) -> tuple[date, date]:
    current = _ensure_utc(now) or _utc_now()
    end_date = _to_local_date(current, tz_offset_minutes)
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def _list_window_dates(start_date: date, end_date: date) -> list[date]:
    total_days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(total_days)]


def _empty_trend_item(target_date: date) -> StatsTrendItemOut:
    return StatsTrendItemOut(
        date=target_date,
        created_count=0,
        review_count=0,
        again_count=0,
        hard_count=0,
        good_count=0,
        easy_count=0,
    )


def get_overview(db: Session, tz_offset_minutes: int = 0) -> StatsOverviewOut:
    now = _utc_now()
    today_local = _to_local_date(now, tz_offset_minutes)
    recent_start = today_local - timedelta(days=6)

    mistakes = db.scalars(select(Mistake).where(Mistake.is_archived.is_(False))).all()
    review_logs = db.scalars(select(ReviewLog)).all()

    reviewed_today = 0
    recent_logs: list[ReviewLog] = []
    streak_dates: set[date] = set()

    for log in review_logs:
        shown_at = _ensure_utc(log.shown_at)
        if shown_at is None:
            continue

        local_day = _to_local_date(shown_at, tz_offset_minutes)
        streak_dates.add(local_day)

        if local_day == today_local:
            reviewed_today += 1

        if recent_start <= local_day <= today_local:
            recent_logs.append(log)

    correct_recent = sum(
        1 for log in recent_logs if log.user_result in {ReviewResult.GOOD, ReviewResult.EASY}
    )
    avg_accuracy = (correct_recent / len(recent_logs)) if recent_logs else 0.0
    avg_ease_factor = (sum(mistake.ease_factor for mistake in mistakes) / len(mistakes)) if mistakes else 0.0

    streak_days = 0
    cursor = today_local
    while cursor in streak_dates:
        streak_days += 1
        cursor -= timedelta(days=1)

    return StatsOverviewOut(
        as_of=now,
        total_mistakes=len(mistakes),
        active_mistakes=sum(1 for mistake in mistakes if mistake.status != MistakeStatus.MASTERED),
        mastered_count=sum(1 for mistake in mistakes if mistake.status == MistakeStatus.MASTERED),
        due_today=sum(
            1
            for mistake in mistakes
            if _ensure_utc(mistake.next_review_at) is not None and _ensure_utc(mistake.next_review_at) <= now
        ),
        reviewed_today=reviewed_today,
        reviewed_7d=len(recent_logs),
        avg_accuracy_7d=round(avg_accuracy, 4),
        avg_ease_factor=round(avg_ease_factor, 2),
        streak_days=streak_days,
    )


def get_trend(db: Session, days: int = 30, bucket: str = "day", tz_offset_minutes: int = 0) -> StatsTrendOut:
    start_date, end_date = _date_window(days, tz_offset_minutes)
    items_by_date = {target_date: _empty_trend_item(target_date) for target_date in _list_window_dates(start_date, end_date)}

    mistakes = db.scalars(select(Mistake).where(Mistake.is_archived.is_(False))).all()
    review_logs = db.scalars(select(ReviewLog)).all()

    for mistake in mistakes:
        created_at = _ensure_utc(mistake.created_at)
        if created_at is None:
            continue

        local_day = _to_local_date(created_at, tz_offset_minutes)
        if local_day in items_by_date:
            items_by_date[local_day].created_count += 1

    for log in review_logs:
        shown_at = _ensure_utc(log.shown_at)
        if shown_at is None:
            continue

        local_day = _to_local_date(shown_at, tz_offset_minutes)
        if local_day not in items_by_date:
            continue

        current = items_by_date[local_day]
        current.review_count += 1
        if log.user_result == ReviewResult.AGAIN:
            current.again_count += 1
        elif log.user_result == ReviewResult.HARD:
            current.hard_count += 1
        elif log.user_result == ReviewResult.GOOD:
            current.good_count += 1
        elif log.user_result == ReviewResult.EASY:
            current.easy_count += 1

    return StatsTrendOut(
        range=StatsTrendRangeOut(from_date=start_date, to_date=end_date, bucket=bucket),
        items=[items_by_date[target_date] for target_date in sorted(items_by_date)],
    )


def get_heatmap(db: Session, days: int = 90, tz_offset_minutes: int = 0) -> StatsHeatmapOut:
    start_date, end_date = _date_window(days, tz_offset_minutes)
    counts: dict[date, int] = {target_date: 0 for target_date in _list_window_dates(start_date, end_date)}

    review_logs = db.scalars(select(ReviewLog)).all()
    for log in review_logs:
        shown_at = _ensure_utc(log.shown_at)
        if shown_at is None:
            continue

        local_day = _to_local_date(shown_at, tz_offset_minutes)
        if local_day in counts:
            counts[local_day] += 1

    max_count = max(counts.values(), default=0)
    cells = []
    for target_date in sorted(counts):
        count = counts[target_date]
        level = 0 if count == 0 or max_count == 0 else min(4, ceil(count / max_count * 4))
        cells.append(StatsHeatmapCellOut(date=target_date, count=count, level=level))

    return StatsHeatmapOut(
        range=StatsHeatmapRangeOut(from_date=start_date, to_date=end_date),
        max_count=max_count,
        cells=cells,
    )


def get_top_weak(db: Session, limit: int = 5, days: int = 30) -> StatsTopWeakOut:
    now = _utc_now()
    cutoff = now - timedelta(days=days)

    mistakes = db.scalars(
        select(Mistake)
        .where(Mistake.is_archived.is_(False))
        .options(joinedload(Mistake.category), selectinload(Mistake.review_logs))
    ).all()

    items: list[StatsTopWeakItemOut] = []

    for mistake in mistakes:
        all_logs = sorted(
            (
                log
                for log in mistake.review_logs
                if _ensure_utc(log.shown_at) is not None
            ),
            key=lambda log: _ensure_utc(log.shown_at) or now,
        )
        recent_logs = [
            log
            for log in all_logs
            if (_ensure_utc(log.shown_at) or now) >= cutoff
        ]

        if not recent_logs:
            continue

        next_review_at = _ensure_utc(mistake.next_review_at)
        overdue_days = 0
        if next_review_at is not None and next_review_at < now:
            overdue_days = (now - next_review_at).days

        again_count = sum(1 for log in recent_logs if log.user_result == ReviewResult.AGAIN)
        hard_count = sum(1 for log in recent_logs if log.user_result == ReviewResult.HARD)
        last_log = all_logs[-1] if all_logs else None
        category = mistake.category if isinstance(mistake.category, Category) else None
        weak_score = round(again_count * 3 + hard_count + overdue_days * 0.5, 2)

        items.append(
            StatsTopWeakItemOut(
                mistake_id=mistake.id,
                title=mistake.title,
                language=mistake.language,
                category_name=category.name if category is not None else "",
                status=mistake.status,
                review_count=len(all_logs),
                last_result=last_log.user_result if last_log is not None else None,
                again_count=again_count,
                hard_count=hard_count,
                next_review_at=next_review_at,
                overdue_days=overdue_days,
                weak_score=weak_score,
            )
        )

    items.sort(
        key=lambda item: (
            -item.weak_score,
            -item.again_count,
            -item.hard_count,
            -item.review_count,
            item.mistake_id,
        )
    )
    return StatsTopWeakOut(items=items[:limit])


def get_tag_radar(db: Session, min_count: int = 2, max_tags: int = 8) -> StatsTagRadarOut:
    mistakes = db.scalars(
        select(Mistake)
        .where(Mistake.is_archived.is_(False))
        .options(selectinload(Mistake.tags), selectinload(Mistake.review_logs))
    ).all()

    tag_mistakes: dict[str, list[Mistake]] = defaultdict(list)
    for mistake in mistakes:
        for tag in mistake.tags:
            tag_mistakes[tag.name].append(mistake)

    items: list[StatsTagRadarItemOut] = []
    for tag_name, tag_mistake_list in tag_mistakes.items():
        if len(tag_mistake_list) < min_count:
            continue

        total_reviews = 0
        mastered_reviews = 0
        ease_sum = 0.0
        for mistake in tag_mistake_list:
            ease_sum += mistake.ease_factor
            for log in mistake.review_logs:
                total_reviews += 1
                if log.user_result in {ReviewResult.GOOD, ReviewResult.EASY}:
                    mastered_reviews += 1

        mastery_rate = round(mastered_reviews / total_reviews, 4) if total_reviews > 0 else 0.0
        avg_ease_factor = round(ease_sum / len(tag_mistake_list), 2)

        items.append(StatsTagRadarItemOut(
            tag_name=tag_name,
            mistake_count=len(tag_mistake_list),
            mastery_rate=mastery_rate,
            avg_ease_factor=avg_ease_factor,
        ))

    items.sort(key=lambda x: (-x.mistake_count, x.tag_name))
    return StatsTagRadarOut(items=items[:max_tags], min_count_threshold=min_count)
