"""Stats SQL push-down regression coverage (H-006).

The legacy implementation used .all() to load every Mistake / ReviewLog row
into Python and aggregate there. The new implementation pushes aggregations
into SQL and only returns small projection rows. These tests pin behaviors
that broke or that are easy to regress when re-doing the rewrite:

  - heatmap honours the requested day window (the legacy code forgot to)
  - tz_offset for negative offsets still buckets review logs to the right day
  - get_overview stays under a generous wall-clock budget at 10K logs

Heavier semantics are still covered by tests/test_stats_api.py (HTTP layer).
"""

from __future__ import annotations

import time as time_module
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models import Category, Mistake, ReviewLog, ReviewResult, User
from app.services.auth_service import hash_password
from app.services.stats_service import get_heatmap, get_overview


def _make_user_with_mistake(db: Session, username: str = "alice") -> tuple[int, int]:
    user = User(username=username, password_hash=hash_password("testpass123"))
    db.add(user)
    db.flush()
    category = Category(user_id=user.id, name="cat")
    db.add(category)
    db.flush()
    mistake = Mistake(
        user_id=user.id,
        category_id=category.id,
        title="m",
        stem_markdown="s",
        wrong_answer_markdown="w",
        correct_answer_markdown="c",
        error_reason_markdown="e",
        language="cpp",
        difficulty=1,
    )
    db.add(mistake)
    db.flush()
    return user.id, mistake.id


def _store_dt(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")


def _insert_log(db: Session, *, user_id: int, mistake_id: int, shown_at: datetime) -> None:
    stored = _store_dt(shown_at)
    db.execute(
        sa.text(
            "INSERT INTO review_logs (user_id, mistake_id, session_id, review_mode,"
            " user_result, shown_at, answered_at, note)"
            " VALUES (:u, :m, NULL, 'manual', 'GOOD', :s, :s, '')"
        ),
        {"u": user_id, "m": mistake_id, "s": stored},
    )


def test_heatmap_excludes_logs_outside_day_window(alembic_head_engine) -> None:
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        user_id, mistake_id = _make_user_with_mistake(db)
        now = datetime.now(timezone.utc)
        # one inside the 30-day window, one 100 days ago (well outside)
        _insert_log(db, user_id=user_id, mistake_id=mistake_id, shown_at=now - timedelta(days=2))
        _insert_log(db, user_id=user_id, mistake_id=mistake_id, shown_at=now - timedelta(days=100))
        db.commit()

        heatmap = get_heatmap(db, user_id=user_id, days=30, tz_offset_minutes=0)

    total = sum(cell.count for cell in heatmap.cells)
    assert total == 1, f"expected only the in-window log to count, got {total}"
    assert heatmap.max_count == 1


def test_overview_handles_negative_tz_offset(alembic_head_engine) -> None:
    """tz_offset_minutes=-480 (UTC-8) is valid; the SQL date(value, 'N minutes')
    modifier accepts negative offsets the same way the Python helper does.
    Bucketing should agree between SQL and Python paths.
    """
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        user_id, mistake_id = _make_user_with_mistake(db)
        # 2 logs explicitly placed mid-day in UTC-8 local time today, then commit.
        local_tz = timezone(timedelta(minutes=-480))
        now_local = datetime.now(local_tz).replace(microsecond=0)
        midday_local = now_local.replace(hour=12, minute=0, second=0)
        if midday_local > now_local:
            midday_local -= timedelta(days=1)
        _insert_log(db, user_id=user_id, mistake_id=mistake_id, shown_at=midday_local)
        _insert_log(
            db,
            user_id=user_id,
            mistake_id=mistake_id,
            shown_at=midday_local - timedelta(hours=1),
        )
        db.commit()

        overview = get_overview(db, user_id=user_id, tz_offset_minutes=-480)

    assert overview.reviewed_today == 2
    assert overview.streak_days >= 1


def test_overview_runtime_under_10k_logs(alembic_head_engine) -> None:
    """Push-down version must aggregate at the DB layer; bulk-load + Python sum
    over 10K rows historically took multi-second. Allow a generous CI budget.
    """
    with Session(alembic_head_engine, expire_on_commit=False) as db:
        user_id, mistake_id = _make_user_with_mistake(db)
        now = datetime.now(timezone.utc)
        rows = [
            {
                "u": user_id,
                "m": mistake_id,
                "s": _store_dt(now - timedelta(minutes=i)),
                "r": ReviewResult.GOOD.value,
            }
            for i in range(10_000)
        ]
        db.execute(
            sa.text(
                "INSERT INTO review_logs (user_id, mistake_id, session_id, review_mode,"
                " user_result, shown_at, answered_at, note)"
                " VALUES (:u, :m, NULL, 'manual', :r, :s, :s, '')"
            ),
            rows,
        )
        db.commit()

        start = time_module.perf_counter()
        overview = get_overview(db, user_id=user_id, tz_offset_minutes=0)
        elapsed = time_module.perf_counter() - start

    # 1.5 s is ~15x the plan target (100 ms) and still flags a regression to
    # the old "load 10K rows into Python" path which took multiple seconds.
    assert elapsed < 1.5, f"get_overview took {elapsed:.3f}s, expected < 1.5s"
    assert overview.reviewed_today >= 1
