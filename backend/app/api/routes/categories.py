from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.category import CategoryCreate, CategoryListResponse, CategoryOut, CategoryUpdate
from app.schemas.common import DeleteResponse
from app.services.taxonomy_service import create_category, delete_category, get_category, list_categories, update_category


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
def list_categories_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    """List all categories."""
    items = list_categories(db, user_id=current_user.id)
    return CategoryListResponse(items=items, total=len(items))


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category_route(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryOut:
    """Create a category."""
    return create_category(db, payload, user_id=current_user.id)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category_route(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryOut:
    """Fetch a category by id."""
    return get_category(db, category_id, user_id=current_user.id)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category_route(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryOut:
    """Partially update a category."""
    return update_category(db, category_id, payload, user_id=current_user.id)


@router.delete("/{category_id}", response_model=DeleteResponse)
def delete_category_route(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteResponse:
    """Delete a category."""
    return delete_category(db, category_id, user_id=current_user.id)
