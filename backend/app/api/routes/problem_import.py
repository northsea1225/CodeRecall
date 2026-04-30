from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from app.api.deps import get_current_user
from app.models import User
from app.schemas.problem_import import ProblemUrlPreviewRequest, ProblemUrlPreviewResponse
from app.services.problem_import_service import fetch_problem_preview
from app.services.providers.base import ProblemImportError


router = APIRouter(prefix="/import", tags=["problem-import"])


@router.post("/problem-url/preview", response_model=ProblemUrlPreviewResponse)
async def preview_problem_url_route(
    body: ProblemUrlPreviewRequest,
    current_user: User = Depends(get_current_user),
) -> ProblemUrlPreviewResponse:
    try:
        return await fetch_problem_preview(body.url)
    except ProblemImportError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        )
