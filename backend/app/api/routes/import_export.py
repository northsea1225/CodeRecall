from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.errors import raise_api_error
from app.core.limiter import limiter
from app.db.session import get_db
from app.models import User
from app.schemas.import_export import ExportResponse, ExportResponseV3, ImportPayload, ImportPayloadV3, ImportResponse
from app.services.import_export_service import (
    export_data,
    export_data_v3,
    export_mistakes_v2,
    import_data,
    import_data_v3,
    import_mistakes_v2_records,
    parse_export_include,
)


router = APIRouter(tags=["import-export"])
V1_IMPORT_RESPONSE_EXCLUDE = {
    "imported": {"review_sessions", "review_session_items", "review_logs"},
}


@router.get("/export", response_model=ExportResponse)
def export_route(
    include: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Export selected resources as JSON."""
    export_payload = export_data(db, parse_export_include(include), user_id=current_user.id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return JSONResponse(
        content=jsonable_encoder(export_payload),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="coderecall-export-{timestamp}.json"',
        },
    )


@router.get("/export/v3", response_model=ExportResponseV3)
def export_v3_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    export_payload = export_data_v3(db, user_id=current_user.id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return JSONResponse(
        content=jsonable_encoder(export_payload),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="coderecall-v3-{timestamp}.json"',
        },
    )


@router.post("/import", response_model=ImportResponse, response_model_exclude=V1_IMPORT_RESPONSE_EXCLUDE)
def import_route(
    payload: ImportPayload,
    strategy: str = Query(default="skip_existing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResponse:
    """Import categories, tags, and mistakes from JSON."""
    return import_data(db, payload, strategy, user_id=current_user.id)


@router.post("/import/v3", response_model=ImportResponse)
@limiter.limit("5/hour")
def import_v3_route(
    request: Request,
    payload: ImportPayloadV3,
    strategy: str = Query(default="skip_existing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResponse:
    """Import a schema v3 full backup, including review history."""
    return import_data_v3(db, payload, strategy, user_id=current_user.id)


@router.get("/mistakes/export")
def export_mistakes_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Export mistakes as a v2 round-trip list."""
    return JSONResponse(content=jsonable_encoder(export_mistakes_v2(db, user_id=current_user.id)))


@router.post("/mistakes/import", response_model=ImportResponse, response_model_exclude=V1_IMPORT_RESPONSE_EXCLUDE)
def import_mistakes_route(
    payload: Any = Body(...),
    strategy: str = Query(default="skip_existing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResponse:
    """Import mistakes from the v2 round-trip list shape."""
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise_api_error(
                422,
                "invalid_import_payload",
                "Import payload must be a list of mistake objects.",
                {},
            )
        return import_mistakes_v2_records(db, payload, strategy, user_id=current_user.id)

    if isinstance(payload, dict):
        return import_data(db, ImportPayload.model_validate(payload), strategy, user_id=current_user.id)

    raise_api_error(
        422,
        "invalid_import_payload",
        "Import payload must be a list of mistakes or an import object.",
        {},
    )
