from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.db.session import get_db
from app.schemas.import_export import ExportResponse, ImportPayload, ImportResponse
from app.services.import_export_service import (
    export_data,
    export_mistakes_v2,
    import_data,
    import_mistakes_v2_records,
    parse_export_include,
)


router = APIRouter(tags=["import-export"])


@router.get("/export", response_model=ExportResponse)
def export_route(
    include: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Export selected resources as JSON."""
    export_payload = export_data(db, parse_export_include(include))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return JSONResponse(
        content=jsonable_encoder(export_payload),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="coderecall-export-{timestamp}.json"',
        },
    )


@router.post("/import", response_model=ImportResponse)
def import_route(
    payload: ImportPayload,
    strategy: str = Query(default="skip_existing"),
    db: Session = Depends(get_db),
) -> ImportResponse:
    """Import categories, tags, and mistakes from JSON."""
    return import_data(db, payload, strategy)


@router.get("/mistakes/export")
def export_mistakes_route(db: Session = Depends(get_db)) -> JSONResponse:
    """Export mistakes as a v2 round-trip list."""
    return JSONResponse(content=jsonable_encoder(export_mistakes_v2(db)))


@router.post("/mistakes/import", response_model=ImportResponse)
def import_mistakes_route(
    payload: Any = Body(...),
    strategy: str = Query(default="skip_existing"),
    db: Session = Depends(get_db),
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
        return import_mistakes_v2_records(db, payload, strategy)

    if isinstance(payload, dict):
        return import_data(db, ImportPayload.model_validate(payload), strategy)

    raise_api_error(
        422,
        "invalid_import_payload",
        "Import payload must be a list of mistakes or an import object.",
        {},
    )
