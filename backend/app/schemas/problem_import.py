from __future__ import annotations

from pydantic import BaseModel


class ProblemUrlPreviewRequest(BaseModel):
    url: str


class ProblemUrlPreviewResponse(BaseModel):
    provider: str
    source_url: str
    external_id: str
    title: str
    difficulty_raw: str
    difficulty: int
    tags: list[str]
    stem_markdown: str
    warnings: list[str]
