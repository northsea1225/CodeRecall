from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import DeleteResponse
from app.schemas.tag import TagCreate, TagListResponse, TagOut, TagUpdate
from app.services.taxonomy_service import create_tag, delete_tag, get_tag, list_tags, update_tag


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
def list_tags_route(db: Session = Depends(get_db)) -> TagListResponse:
    """List all tags."""
    items = list_tags(db)
    return TagListResponse(items=items, total=len(items))


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag_route(payload: TagCreate, db: Session = Depends(get_db)) -> TagOut:
    """Create a tag."""
    return create_tag(db, payload)


@router.get("/{tag_id}", response_model=TagOut)
def get_tag_route(tag_id: int, db: Session = Depends(get_db)) -> TagOut:
    """Fetch a tag by id."""
    return get_tag(db, tag_id)


@router.patch("/{tag_id}", response_model=TagOut)
def update_tag_route(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)) -> TagOut:
    """Partially update a tag."""
    return update_tag(db, tag_id, payload)


@router.delete("/{tag_id}", response_model=DeleteResponse)
def delete_tag_route(tag_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    """Delete a tag."""
    return delete_tag(db, tag_id)
