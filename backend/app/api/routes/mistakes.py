from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.mistake import MistakeCreate, MistakeListResponse, MistakeOut, MistakeUpdate
from app.services.mistake_service import create_mistake, delete_mistake, get_mistake, list_mistakes, update_mistake


router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.post("", response_model=MistakeOut, status_code=status.HTTP_201_CREATED)
def create_mistake_route(payload: MistakeCreate, db: Session = Depends(get_db)) -> MistakeOut:
    """Create a mistake record."""
    return create_mistake(db, payload)


@router.get("", response_model=MistakeListResponse)
def list_mistakes_route(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: Optional[int] = Query(default=None),
    language: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
) -> MistakeListResponse:
    """List mistakes with pagination and filters."""
    return list_mistakes(
        db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        language=language,
        keyword=keyword,
    )


@router.get("/{mistake_id}", response_model=MistakeOut)
def get_mistake_route(mistake_id: int, db: Session = Depends(get_db)) -> MistakeOut:
    """Fetch a mistake by id."""
    return get_mistake(db, mistake_id)


@router.patch("/{mistake_id}", response_model=MistakeOut)
def update_mistake_route(
    mistake_id: int,
    payload: MistakeUpdate,
    db: Session = Depends(get_db),
) -> MistakeOut:
    """Partially update a mistake."""
    return update_mistake(db, mistake_id, payload)


@router.delete("/{mistake_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mistake_route(mistake_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a mistake by id."""
    delete_mistake(db, mistake_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
