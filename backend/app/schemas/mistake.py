from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mistake_constraints import (
    MAX_ERROR_REASON_LEN,
    MAX_LANGUAGE_LEN,
    MAX_MARKDOWN_LEN,
    MAX_SOURCE_LEN,
    MAX_TITLE_LEN,
    MistakeErrorReason,
    MistakeLanguage,
    MistakeMarkdown,
    MistakeSource,
    MistakeTitle,
)
from app.models.mistake import MistakeStatus
from app.schemas.category import CategoryOut
from app.schemas.tag import TagOut


class PaginationMeta(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20


class MistakeBase(BaseModel):
    """可编辑基础字段；学习进度字段由 review 流统一驱动，不接受 PATCH 直改。"""

    title: MistakeTitle
    stem_markdown: MistakeMarkdown
    wrong_answer_markdown: MistakeMarkdown
    correct_answer_markdown: MistakeMarkdown
    error_reason_markdown: MistakeErrorReason
    language: MistakeLanguage
    difficulty: int = Field(ge=1, le=5)
    source: MistakeSource = ""
    status: MistakeStatus = Field(
        default=MistakeStatus.NEW,
        description="受 review 流控制；PATCH 请求会忽略该字段。",
    )
    is_archived: bool = False


class MistakeCreate(MistakeBase):
    category_id: int
    tags: list[str] = Field(default_factory=list)


class MistakeUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: MistakeTitle | None = None
    stem_markdown: MistakeMarkdown | None = None
    wrong_answer_markdown: MistakeMarkdown | None = None
    correct_answer_markdown: MistakeMarkdown | None = None
    error_reason_markdown: MistakeErrorReason | None = None
    language: MistakeLanguage | None = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    source: MistakeSource | None = None
    category_id: Optional[int] = None
    tags: Optional[list[str]] = None
    is_archived: Optional[bool] = None


class MistakeOut(MistakeBase):
    id: int
    category: CategoryOut
    tags: list[TagOut]
    review_count: int
    last_reviewed_at: Optional[datetime]
    next_review_at: Optional[datetime]
    ease_factor: float
    interval_days: int
    repetition: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MistakeListResponse(BaseModel):
    items: list[MistakeOut]
    total: int
    pagination: PaginationMeta
