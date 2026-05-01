from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.taxonomy_constraints import TagName


class TagBase(BaseModel):
    name: TagName


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[TagName] = None


class TagOut(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    items: list[TagOut]
    total: int
