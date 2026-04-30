from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error, raise_not_found
from app.models import Category, Tag
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.common import DeleteResponse
from app.schemas.tag import TagCreate, TagUpdate


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise_api_error(
            status_code=422,
            code="invalid_field",
            message=f"{field_name} cannot be blank.",
            detail={"field": field_name},
        )
    return normalized


def normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip()


def normalize_tag_names(tag_names: Iterable[str]) -> list[str]:
    normalized_names: list[str] = []
    seen: set[str] = set()

    for tag_name in tag_names:
        normalized = normalize_required_text(tag_name, field_name="tags")
        if normalized not in seen:
            seen.add(normalized)
            normalized_names.append(normalized)

    return normalized_names


def list_categories(db: Session, user_id: Optional[int] = None) -> list[Category]:
    statement = select(Category).order_by(Category.created_at.desc(), Category.id.desc())
    if user_id is not None:
        statement = statement.where(Category.user_id == user_id)
    return list(db.scalars(statement).all())


def get_category(db: Session, category_id: int, user_id: Optional[int] = None) -> Category:
    statement = select(Category).where(Category.id == category_id)
    if user_id is not None:
        statement = statement.where(Category.user_id == user_id)
    category = db.scalar(statement)
    if category is None:
        raise_not_found("category", category_id)
    return category


def _validate_parent_category(
    db: Session,
    parent_id: Optional[int],
    current_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> None:
    if parent_id is None:
        return

    if current_id is not None and parent_id == current_id:
        raise_api_error(
            status_code=422,
            code="invalid_category_parent",
            message="Category cannot be its own parent.",
            detail={"parent_id": parent_id},
        )

    get_category(db, parent_id, user_id=user_id)


def _flush_or_raise_duplicate(db: Session, *, entity: str, name: str) -> None:
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise_api_error(
            status_code=409,
            code=f"{entity}_name_conflict",
            message=f"{entity.title()} name already exists.",
            detail={"name": name},
        )


def create_category(db: Session, payload: CategoryCreate, user_id: Optional[int] = None) -> Category:
    _validate_parent_category(db, payload.parent_id, user_id=user_id)

    category = Category(
        user_id=user_id,
        name=normalize_required_text(payload.name, field_name="name"),
        description=normalize_optional_text(payload.description) or "",
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(category)
    _flush_or_raise_duplicate(db, entity="category", name=category.name)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, payload: CategoryUpdate, user_id: Optional[int] = None) -> Category:
    category = get_category(db, category_id, user_id=user_id)
    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates:
        category.name = normalize_required_text(updates["name"], field_name="name")
    if "description" in updates:
        category.description = normalize_optional_text(updates["description"]) or ""
    if "parent_id" in updates:
        _validate_parent_category(db, updates["parent_id"], current_id=category.id, user_id=user_id)
        category.parent_id = updates["parent_id"]
    if "sort_order" in updates:
        category.sort_order = updates["sort_order"]

    category.updated_at = utc_now()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_api_error(
            status_code=409,
            code="category_name_conflict",
            message="Category name already exists.",
            detail={"name": category.name},
        )

    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int, user_id: Optional[int] = None) -> DeleteResponse:
    category = get_category(db, category_id, user_id=user_id)
    db.delete(category)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_api_error(
            status_code=409,
            code="category_in_use",
            message="Category is still referenced by mistakes.",
            detail={"category_id": category_id},
        )

    return DeleteResponse(id=category_id, deleted=True)


def list_tags(db: Session, user_id: Optional[int] = None) -> list[Tag]:
    statement = select(Tag).order_by(Tag.created_at.desc(), Tag.id.desc())
    if user_id is not None:
        statement = statement.where(Tag.user_id == user_id)
    return list(db.scalars(statement).all())


def get_tag(db: Session, tag_id: int, user_id: Optional[int] = None) -> Tag:
    statement = select(Tag).where(Tag.id == tag_id)
    if user_id is not None:
        statement = statement.where(Tag.user_id == user_id)
    tag = db.scalar(statement)
    if tag is None:
        raise_not_found("tag", tag_id)
    return tag


def get_tags_by_names(db: Session, tag_names: list[str], user_id: Optional[int] = None) -> list[Tag]:
    if not tag_names:
        return []

    statement = select(Tag).where(Tag.name.in_(tag_names)).order_by(Tag.id.asc())
    if user_id is not None:
        statement = statement.where(Tag.user_id == user_id)
    return list(db.scalars(statement).all())


def get_or_create_tags(db: Session, tag_names: Iterable[str], user_id: Optional[int] = None) -> list[Tag]:
    normalized_names = normalize_tag_names(tag_names)
    if not normalized_names:
        return []

    existing_tags = {
        tag.name: tag
        for tag in get_tags_by_names(db, normalized_names, user_id=user_id)
    }

    ordered_tags: list[Tag] = []
    timestamp = utc_now()
    for tag_name in normalized_names:
        tag = existing_tags.get(tag_name)
        if tag is None:
            tag = Tag(name=tag_name, user_id=user_id, created_at=timestamp, updated_at=timestamp)
            db.add(tag)
            db.flush()
            existing_tags[tag_name] = tag
        ordered_tags.append(tag)

    return ordered_tags


def create_tag(db: Session, payload: TagCreate, user_id: Optional[int] = None) -> Tag:
    tag = Tag(
        user_id=user_id,
        name=normalize_required_text(payload.name, field_name="name"),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(tag)
    _flush_or_raise_duplicate(db, entity="tag", name=tag.name)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, payload: TagUpdate, user_id: Optional[int] = None) -> Tag:
    tag = get_tag(db, tag_id, user_id=user_id)
    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates:
        tag.name = normalize_required_text(updates["name"], field_name="name")

    tag.updated_at = utc_now()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_api_error(
            status_code=409,
            code="tag_name_conflict",
            message="Tag name already exists.",
            detail={"name": tag.name},
        )

    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int, user_id: Optional[int] = None) -> DeleteResponse:
    tag = get_tag(db, tag_id, user_id=user_id)
    db.delete(tag)
    db.commit()
    return DeleteResponse(id=tag_id, deleted=True)
