from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Any = Field(default_factory=dict)


class DeleteResponse(BaseModel):
    id: int
    deleted: bool = True
