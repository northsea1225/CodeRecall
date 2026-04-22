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


class ImportSkip(BaseModel):
    entity: str
    identifier: str
    reason: str


class ImportResponse(BaseModel):
    version: str = "v1"
    imported: ImportCount
    skipped: list[ImportSkip] = Field(default_factory=list)
