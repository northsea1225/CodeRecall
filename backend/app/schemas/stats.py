from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.mistake import MistakeStatus
from app.models.review import ReviewResult


class StatsOverviewOut(BaseModel):
    as_of: datetime
    total_mistakes: int
    active_mistakes: int
    mastered_count: int
    due_today: int
    reviewed_today: int
    reviewed_7d: int
    avg_accuracy_7d: float
    avg_ease_factor: float
    streak_days: int


class StatsTrendRangeOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    bucket: Literal["day"]


class StatsTrendItemOut(BaseModel):
    date: date
    created_count: int
    review_count: int
    again_count: int
    hard_count: int
    good_count: int
    easy_count: int


class StatsTrendOut(BaseModel):
    range: StatsTrendRangeOut
    items: list[StatsTrendItemOut]


class StatsHeatmapRangeOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")


class StatsHeatmapCellOut(BaseModel):
    date: date
    count: int
    level: int = Field(ge=0, le=4)


class StatsHeatmapOut(BaseModel):
    range: StatsHeatmapRangeOut
    max_count: int
    cells: list[StatsHeatmapCellOut]


class StatsTopWeakItemOut(BaseModel):
    mistake_id: int
    title: str
    language: str
    category_name: str
    status: MistakeStatus
    review_count: int
    last_result: Optional[ReviewResult] = None
    again_count: int
    hard_count: int
    next_review_at: Optional[datetime] = None
    overdue_days: int
    weak_score: float


class StatsTopWeakOut(BaseModel):
    items: list[StatsTopWeakItemOut]


class StatsTagRadarItemOut(BaseModel):
    tag_name: str
    mistake_count: int
    mastery_rate: float
    avg_ease_factor: float


class StatsTagRadarOut(BaseModel):
    items: list[StatsTagRadarItemOut]
    min_count_threshold: int
