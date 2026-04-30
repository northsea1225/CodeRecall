from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.stats import StatsHeatmapOut, StatsOverviewOut, StatsTagRadarOut, StatsTopWeakOut, StatsTrendOut
from app.services.stats_service import get_heatmap, get_overview, get_tag_radar, get_top_weak, get_trend


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverviewOut)
def get_stats_overview_route(
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsOverviewOut:
    return get_overview(db, tz_offset_minutes=tz_offset_minutes, user_id=current_user.id)


@router.get("/trend", response_model=StatsTrendOut)
def get_stats_trend_route(
    days: int = Query(default=30, ge=1, le=365),
    bucket: Literal["day"] = Query(default="day"),
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsTrendOut:
    return get_trend(db, days=days, bucket=bucket, tz_offset_minutes=tz_offset_minutes, user_id=current_user.id)


@router.get("/heatmap", response_model=StatsHeatmapOut)
def get_stats_heatmap_route(
    days: int = Query(default=90, ge=1, le=364),
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsHeatmapOut:
    return get_heatmap(db, days=days, tz_offset_minutes=tz_offset_minutes, user_id=current_user.id)


@router.get("/top-weak", response_model=StatsTopWeakOut)
def get_stats_top_weak_route(
    limit: int = Query(default=5, ge=1, le=50),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsTopWeakOut:
    return get_top_weak(db, limit=limit, days=days, user_id=current_user.id)


@router.get("/tag-radar", response_model=StatsTagRadarOut)
def get_stats_tag_radar_route(
    min_count: int = Query(default=2, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsTagRadarOut:
    return get_tag_radar(db, min_count=min_count, user_id=current_user.id)
