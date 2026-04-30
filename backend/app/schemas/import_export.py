from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ImportCategory(BaseModel):
    name: str
    description: str = ""


class ImportTag(BaseModel):
    name: str


class ImportMistake(BaseModel):
    title: str
    stem_markdown: str
    wrong_answer_markdown: str
    correct_answer_markdown: str
    error_reason_markdown: str
    language: str
    difficulty: int = Field(ge=1, le=5)
    source: str = ""
    status: str = "new"
    category_name: str
    tag_names: list[str] = Field(default_factory=list)
    ease_factor: float = 2.5
    interval_days: int = 0
    repetition: int = 0
    next_review_at: Optional[datetime] = None
    is_archived: bool = False


class ImportPayload(BaseModel):
    version: str = "v1"
    schema_version: Optional[str] = None
    mistakes: list[ImportMistake] = Field(default_factory=list)
    categories: list[ImportCategory] = Field(default_factory=list)
    tags: list[ImportTag] = Field(default_factory=list)


class ExportResponse(BaseModel):
    version: str = "v1"
    schema_version: str = "v2"
    exported_at: datetime
    categories: list[ImportCategory]
    tags: list[ImportTag]
    mistakes: list[ImportMistake]


class ImportCount(BaseModel):
    mistakes: int = 0
    categories: int = 0
    tags: int = 0
    review_sessions: int = 0
    review_session_items: int = 0
    review_logs: int = 0


class ImportSkip(BaseModel):
    entity: str
    identifier: str
    reason: str


class ImportResponse(BaseModel):
    version: str = "v1"
    imported: ImportCount
    skipped: list[ImportSkip] = Field(default_factory=list)


class ExportReviewLog(BaseModel):
    mistake_uuid: Optional[str] = None
    session_id: Optional[int] = None
    review_mode: str
    user_result: str
    shown_at: datetime
    answered_at: Optional[datetime] = None
    old_interval_days: Optional[int] = Field(default=None, ge=0)
    new_interval_days: Optional[int] = Field(default=None, ge=0)
    old_ease_factor: Optional[float] = None
    new_ease_factor: Optional[float] = None
    time_spent_ms: Optional[int] = Field(default=None, ge=0)
    note: str = ""


class ExportReviewSession(BaseModel):
    id: int = Field(ge=1)
    started_at: datetime
    ended_at: Optional[datetime] = None
    strategy: str
    total_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)


class ExportReviewSessionItem(BaseModel):
    session_id: int = Field(ge=1)
    mistake_uuid: Optional[str] = None
    order_index: int = Field(ge=0)


class ExportMistakeV3(BaseModel):
    uuid: Optional[str] = None
    legacy_id: int
    title: str
    stem_markdown: str
    wrong_answer_markdown: str
    correct_answer_markdown: str
    error_reason_markdown: str
    language: str
    difficulty: int = Field(ge=1, le=5)
    source: str
    status: str
    category_name: str
    tag_names: list[str]
    ease_factor: float
    interval_days: int
    repetition: int
    next_review_at: Optional[datetime] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ExportResponseV3(BaseModel):
    format: str = "coderecall"
    schema_version: int = 3
    exported_at: datetime
    categories: list[ImportCategory]
    tags: list[ImportTag]
    mistakes: list[ExportMistakeV3]
    review_sessions: list[ExportReviewSession]
    review_session_items: list[ExportReviewSessionItem]
    review_logs: list[ExportReviewLog]


class ImportPayloadV3(BaseModel):
    format: str = "coderecall"
    schema_version: int = 3
    exported_at: Optional[datetime] = None
    categories: list[ImportCategory] = Field(default_factory=list, max_length=1000)
    tags: list[ImportTag] = Field(default_factory=list, max_length=10000)
    mistakes: list[ExportMistakeV3] = Field(default_factory=list, max_length=10000)
    review_sessions: list[ExportReviewSession] = Field(default_factory=list, max_length=10000)
    review_session_items: list[ExportReviewSessionItem] = Field(default_factory=list, max_length=100000)
    review_logs: list[ExportReviewLog] = Field(default_factory=list, max_length=200000)
