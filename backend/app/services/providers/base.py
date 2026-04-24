from __future__ import annotations

from typing import Protocol

import httpx

from app.schemas.problem_import import ProblemUrlPreviewResponse


class ProblemImportError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProblemPreviewProvider(Protocol):
    async def fetch_preview(
        self, url: str, client: httpx.AsyncClient
    ) -> ProblemUrlPreviewResponse: ...
