from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.taxonomy_constraints import CategoryDescription, CategoryName


class CategoryBase(BaseModel):
    name: CategoryName
    description: CategoryDescription = ""
    parent_id: Optional[int] = None
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[CategoryName] = None
    description: Optional[CategoryDescription] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    items: list[CategoryOut]
    total: int
