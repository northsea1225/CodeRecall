from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from math import ceil

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.category import Category  # noqa: F401 - relationship target needed for joinedload
from app.models.mistake import Mistake, MistakeStatus
from app.models.review import ReviewLog, ReviewResult
from app.models.tag import MistakeTag, Tag
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


# All date-bucketing here uses SQLite's func.date(value, 'N minutes') modifier.
# Postgres would need date_trunc + interval; revisit when porting (plan §821).


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


def _local_date_to_utc_start(local_day: date, tz_offset_minutes: int) -> str:
    """Return the UTC start of ``local_day`` as an ISO string, no microseconds.

    SQLAlchemy's SQLite DATETIME bind appends ``.%06d`` microseconds to the
    string it sends to SQLite (storage_format default), which then sorts
    lexicographically *above* the stored value (which has no fractional
    seconds, see tests' ``_store_datetime``). Returning a plain string ensures
    SQLAlchemy binds it via the String type and we keep full control of the
    representation.
    """
    aware = datetime.combine(
        local_day, time(0, 0, 0), tzinfo=_local_timezone(tz_offset_minutes)
    ).astimezone(timezone.utc)
    return aware.replace(tzinfo=None, microsecond=0).isoformat(sep=" ")


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


def _local_date_expr(column, tz_offset_minutes: int):
    return func.date(column, f"{tz_offset_minutes} minutes")


def _parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _utc_iso_no_micros(value: datetime) -> str:
    return value.replace(tzinfo=None, microsecond=0).isoformat(sep=" ")


def get_overview(db: Session, *, user_id: int, tz_offset_minutes: int = 0) -> StatsOverviewOut:
    now = _utc_now()
    now_iso = _utc_iso_no_micros(now)
    today_local = _to_local_date(now, tz_offset_minutes)
    seven_day_start_local = today_local - timedelta(days=6)
    today_start_utc = _local_date_to_utc_start(today_local, tz_offset_minutes)
    tomorrow_start_utc = _local_date_to_utc_start(today_local + timedelta(days=1), tz_offset_minutes)
    seven_day_start_utc = _local_date_to_utc_start(seven_day_start_local, tz_offset_minutes)

    correct_results = (ReviewResult.GOOD, ReviewResult.EASY)

    mistake_row = db.execute(
        select(
            func.count(Mistake.id).label("total"),
            func.coalesce(func.avg(Mistake.ease_factor), 0.0).label("avg_ease"),
            func.coalesce(
                func.sum(case((Mistake.status != MistakeStatus.MASTERED, 1), else_=0)), 0
            ).label("active"),
            func.coalesce(
                func.sum(case((Mistake.status == MistakeStatus.MASTERED, 1), else_=0)), 0
            ).label("mastered"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Mistake.next_review_at.is_not(None),
                                Mistake.next_review_at <= now_iso,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("due_today"),
        ).where(Mistake.user_id == user_id, Mistake.is_archived.is_(False))
    ).one()

    log_row = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                ReviewLog.shown_at >= today_start_utc,
                                ReviewLog.shown_at < tomorrow_start_utc,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("reviewed_today"),
            func.coalesce(func.count(ReviewLog.id), 0).label("reviewed_7d"),
            func.coalesce(
                func.sum(case((ReviewLog.user_result.in_(correct_results), 1), else_=0)), 0
            ).label("correct_recent"),
        ).where(
            ReviewLog.user_id == user_id,
            ReviewLog.shown_at >= seven_day_start_utc,
        )
    ).one()

    streak_day_rows = db.execute(
        select(_local_date_expr(ReviewLog.shown_at, tz_offset_minutes).label("day"))
        .where(ReviewLog.user_id == user_id)
        .group_by("day")
        .order_by(func.max(ReviewLog.shown_at).desc())
        .limit(365)
    ).all()
    streak_dates = {_parse_date(row.day) for row in streak_day_rows}

    streak_days = 0
    cursor = today_local
    while cursor in streak_dates:
        streak_days += 1
        cursor -= timedelta(days=1)

    reviewed_7d = int(log_row.reviewed_7d or 0)
    correct_recent = int(log_row.correct_recent or 0)
    avg_accuracy = (correct_recent / reviewed_7d) if reviewed_7d else 0.0

    return StatsOverviewOut(
        as_of=now,
        total_mistakes=int(mistake_row.total or 0),
        active_mistakes=int(mistake_row.active or 0),
        mastered_count=int(mistake_row.mastered or 0),
        due_today=int(mistake_row.due_today or 0),
        reviewed_today=int(log_row.reviewed_today or 0),
        reviewed_7d=reviewed_7d,
        avg_accuracy_7d=round(avg_accuracy, 4),
        avg_ease_factor=round(float(mistake_row.avg_ease or 0.0), 2),
        streak_days=streak_days,
    )


def get_trend(
    db: Session,
    *,
    user_id: int,
    days: int = 30,
    bucket: str = "day",
    tz_offset_minutes: int = 0,
) -> StatsTrendOut:
    start_date, end_date = _date_window(days, tz_offset_minutes)
    items_by_date = {target_date: _empty_trend_item(target_date) for target_date in _list_window_dates(start_date, end_date)}
    window_start_utc = _local_date_to_utc_start(start_date, tz_offset_minutes)
    window_end_utc = _local_date_to_utc_start(end_date + timedelta(days=1), tz_offset_minutes)

    created_rows = db.execute(
        select(
            _local_date_expr(Mistake.created_at, tz_offset_minutes).label("day"),
            func.count(Mistake.id).label("cnt"),
        )
        .where(
            Mistake.user_id == user_id,
            Mistake.is_archived.is_(False),
            Mistake.created_at >= window_start_utc,
            Mistake.created_at < window_end_utc,
        )
        .group_by("day")
    ).all()

    for row in created_rows:
        local_day = _parse_date(row.day)
        if local_day in items_by_date:
            items_by_date[local_day].created_count += int(row.cnt)

    log_rows = db.execute(
        select(
            _local_date_expr(ReviewLog.shown_at, tz_offset_minutes).label("day"),
            ReviewLog.user_result.label("result"),
            func.count(ReviewLog.id).label("cnt"),
        )
        .where(
            ReviewLog.user_id == user_id,
            ReviewLog.shown_at >= window_start_utc,
            ReviewLog.shown_at < window_end_utc,
        )
        .group_by("day", ReviewLog.user_result)
    ).all()

    for row in log_rows:
        local_day = _parse_date(row.day)
        if local_day not in items_by_date:
            continue
        item = items_by_date[local_day]
        cnt = int(row.cnt)
        item.review_count += cnt
        if row.result == ReviewResult.AGAIN:
            item.again_count += cnt
        elif row.result == ReviewResult.HARD:
            item.hard_count += cnt
        elif row.result == ReviewResult.GOOD:
            item.good_count += cnt
        elif row.result == ReviewResult.EASY:
            item.easy_count += cnt

    return StatsTrendOut(
        range=StatsTrendRangeOut(from_date=start_date, to_date=end_date, bucket=bucket),
        items=[items_by_date[target_date] for target_date in sorted(items_by_date)],
    )


def get_heatmap(db: Session, *, user_id: int, days: int = 90, tz_offset_minutes: int = 0) -> StatsHeatmapOut:
    start_date, end_date = _date_window(days, tz_offset_minutes)
    counts: dict[date, int] = {target_date: 0 for target_date in _list_window_dates(start_date, end_date)}
    window_start_utc = _local_date_to_utc_start(start_date, tz_offset_minutes)
    window_end_utc = _local_date_to_utc_start(end_date + timedelta(days=1), tz_offset_minutes)

    bucket_rows = db.execute(
        select(
            _local_date_expr(ReviewLog.shown_at, tz_offset_minutes).label("day"),
            func.count(ReviewLog.id).label("cnt"),
        )
        .where(
            ReviewLog.user_id == user_id,
            ReviewLog.shown_at >= window_start_utc,
            ReviewLog.shown_at < window_end_utc,
        )
        .group_by("day")
    ).all()

    for row in bucket_rows:
        local_day = _parse_date(row.day)
        if local_day in counts:
            counts[local_day] = int(row.cnt)

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


def get_top_weak(db: Session, *, user_id: int, limit: int = 5, days: int = 30) -> StatsTopWeakOut:
    now = _utc_now()
    cutoff = _utc_iso_no_micros(now - timedelta(days=days))

    candidate_rows = db.execute(
        select(
            ReviewLog.mistake_id.label("mistake_id"),
            func.coalesce(
                func.sum(case((ReviewLog.user_result == ReviewResult.AGAIN, 1), else_=0)), 0
            ).label("again_count"),
            func.coalesce(
                func.sum(case((ReviewLog.user_result == ReviewResult.HARD, 1), else_=0)), 0
            ).label("hard_count"),
        )
        .where(
            ReviewLog.user_id == user_id,
            ReviewLog.shown_at >= cutoff,
        )
        .group_by(ReviewLog.mistake_id)
    ).all()

    if not candidate_rows:
        return StatsTopWeakOut(items=[])

    candidate_stats = {
        int(row.mistake_id): (int(row.again_count), int(row.hard_count)) for row in candidate_rows
    }

    mistakes = db.scalars(
        select(Mistake)
        .where(
            Mistake.user_id == user_id,
            Mistake.is_archived.is_(False),
            Mistake.id.in_(candidate_stats.keys()),
        )
        .options(joinedload(Mistake.category), selectinload(Mistake.review_logs))
    ).all()

    items: list[StatsTopWeakItemOut] = []
    for mistake in mistakes:
        again_count, hard_count = candidate_stats[mistake.id]
        all_logs = sorted(
            (log for log in mistake.review_logs if _ensure_utc(log.shown_at) is not None),
            key=lambda log: _ensure_utc(log.shown_at) or now,
        )

        next_review_at = _ensure_utc(mistake.next_review_at)
        overdue_days = 0
        if next_review_at is not None and next_review_at < now:
            overdue_days = (now - next_review_at).days

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


def get_tag_radar(
    db: Session,
    *,
    user_id: int,
    min_count: int = 2,
    max_tags: int = 8,
) -> StatsTagRadarOut:
    correct_results = (ReviewResult.GOOD, ReviewResult.EASY)

    relations = db.execute(
        select(
            Mistake.id.label("mistake_id"),
            Mistake.ease_factor.label("ease_factor"),
            Tag.name.label("tag_name"),
        )
        .select_from(Mistake)
        .join(MistakeTag, MistakeTag.mistake_id == Mistake.id)
        .join(Tag, Tag.id == MistakeTag.tag_id)
        .where(Mistake.user_id == user_id, Mistake.is_archived.is_(False))
    ).all()

    if not relations:
        return StatsTagRadarOut(items=[], min_count_threshold=min_count)

    mistake_ids = {int(row.mistake_id) for row in relations}
    log_rows = db.execute(
        select(
            ReviewLog.mistake_id.label("mistake_id"),
            func.count(ReviewLog.id).label("total"),
            func.coalesce(
                func.sum(case((ReviewLog.user_result.in_(correct_results), 1), else_=0)), 0
            ).label("mastered"),
        )
        .where(ReviewLog.user_id == user_id, ReviewLog.mistake_id.in_(mistake_ids))
        .group_by(ReviewLog.mistake_id)
    ).all()
    log_map: dict[int, tuple[int, int]] = {
        int(row.mistake_id): (int(row.total), int(row.mastered)) for row in log_rows
    }

    tag_buckets: dict[str, dict] = defaultdict(
        lambda: {
            "mistake_ids": set(),
            "ease_sum": 0.0,
            "ease_count": 0,
            "total_reviews": 0,
            "mastered_reviews": 0,
        }
    )
    for row in relations:
        bucket = tag_buckets[row.tag_name]
        if row.mistake_id in bucket["mistake_ids"]:
            continue
        bucket["mistake_ids"].add(row.mistake_id)
        bucket["ease_sum"] += float(row.ease_factor)
        bucket["ease_count"] += 1
        total, mastered = log_map.get(row.mistake_id, (0, 0))
        bucket["total_reviews"] += total
        bucket["mastered_reviews"] += mastered

    items: list[StatsTagRadarItemOut] = []
    for tag_name, bucket in tag_buckets.items():
        mistake_count = len(bucket["mistake_ids"])
        if mistake_count < min_count:
            continue
        mastery_rate = (
            round(bucket["mastered_reviews"] / bucket["total_reviews"], 4)
            if bucket["total_reviews"] > 0
            else 0.0
        )
        avg_ease_factor = round(bucket["ease_sum"] / bucket["ease_count"], 2)
        items.append(
            StatsTagRadarItemOut(
                tag_name=tag_name,
                mistake_count=mistake_count,
                mastery_rate=mastery_rate,
                avg_ease_factor=avg_ease_factor,
            )
        )

    items.sort(key=lambda x: (-x.mistake_count, x.tag_name))
    return StatsTagRadarOut(items=items[:max_tags], min_count_threshold=min_count)
