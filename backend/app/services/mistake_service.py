from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.api.errors import raise_api_error, raise_not_found
from app.repositories import MistakeRepository
from app.schemas.mistake import MistakeCreate, MistakeListResponse, MistakeOut, MistakeUpdate, PaginationMeta
from app.services.taxonomy_service import (
    get_category,
    get_or_create_tags,
    normalize_optional_text,
    normalize_required_text,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_mistake(mistake) -> MistakeOut:
    return MistakeOut.model_validate(mistake)


def _normalize_language(language: str) -> str:
    return normalize_required_text(language, field_name="language")


def _normalize_title(title: str) -> str:
    return normalize_required_text(title, field_name="title")


def list_mistakes(
    db: Session,
    *,
    user_id: int,
    page: int,
    page_size: int,
    category_id: Optional[int] = None,
    language: Optional[str] = None,
    keyword: Optional[str] = None,
) -> MistakeListResponse:
    normalized_language = normalize_optional_text(language)
    normalized_keyword = normalize_optional_text(keyword)
    items = MistakeRepository.list(
        db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        category_id=category_id,
        language=normalized_language,
        keyword=normalized_keyword,
    )
    total = MistakeRepository.count(
        db,
        user_id=user_id,
        category_id=category_id,
        language=normalized_language,
        keyword=normalized_keyword,
    )
    return MistakeListResponse(
        items=[_serialize_mistake(item) for item in items],
        total=total,
        pagination=PaginationMeta(total=total, page=page, page_size=page_size),
    )


def get_mistake(db: Session, mistake_id: int, *, user_id: int) -> MistakeOut:
    mistake = MistakeRepository.get_by_id(db, mistake_id, user_id=user_id)
    if mistake is None:
        raise_not_found("mistake", mistake_id)
    return _serialize_mistake(mistake)


def create_mistake(db: Session, payload: MistakeCreate, *, user_id: int) -> MistakeOut:
    from app.models import Mistake

    category = get_category(db, payload.category_id, user_id=user_id)
    tags = get_or_create_tags(db, payload.tags, user_id=user_id)
    timestamp = utc_now()

    mistake = Mistake(
        title=_normalize_title(payload.title),
        user_id=user_id,
        stem_markdown=payload.stem_markdown,
        wrong_answer_markdown=payload.wrong_answer_markdown,
        correct_answer_markdown=payload.correct_answer_markdown,
        error_reason_markdown=payload.error_reason_markdown,
        language=_normalize_language(payload.language),
        category_id=category.id,
        difficulty=payload.difficulty,
        source=normalize_optional_text(payload.source) or "",
        status=payload.status,
        is_archived=payload.is_archived,
        created_at=timestamp,
        updated_at=timestamp,
    )
    mistake.tags = tags
    db.add(mistake)
    db.commit()
    db.refresh(mistake)

    hydrated = MistakeRepository.get_by_id(db, mistake.id, user_id=user_id)
    if hydrated is None:
        raise_api_error(500, "mistake_create_failed", "Mistake creation failed.")
    return _serialize_mistake(hydrated)


def update_mistake(db: Session, mistake_id: int, payload: MistakeUpdate, *, user_id: int) -> MistakeOut:
    mistake = MistakeRepository.get_by_id(db, mistake_id, user_id=user_id)
    if mistake is None:
        raise_not_found("mistake", mistake_id)

    updates = payload.model_dump(exclude_unset=True)

    if "title" in updates:
        mistake.title = _normalize_title(updates["title"])
    if "stem_markdown" in updates:
        mistake.stem_markdown = updates["stem_markdown"]
    if "wrong_answer_markdown" in updates:
        mistake.wrong_answer_markdown = updates["wrong_answer_markdown"]
    if "correct_answer_markdown" in updates:
        mistake.correct_answer_markdown = updates["correct_answer_markdown"]
    if "error_reason_markdown" in updates:
        mistake.error_reason_markdown = updates["error_reason_markdown"]
    if "language" in updates:
        mistake.language = _normalize_language(updates["language"])
    if "difficulty" in updates:
        mistake.difficulty = updates["difficulty"]
    if "source" in updates:
        mistake.source = normalize_optional_text(updates["source"]) or ""
    if "category_id" in updates:
        category_id = updates["category_id"]
        if category_id is None:
            raise_api_error(
                422,
                "invalid_field",
                "category_id cannot be null.",
                {"field": "category_id"},
            )
        mistake.category_id = get_category(db, category_id, user_id=user_id).id
    if "tags" in updates:
        mistake.tags = get_or_create_tags(db, updates["tags"] or [], user_id=user_id)
    if "is_archived" in updates:
        mistake.is_archived = updates["is_archived"]

    mistake.updated_at = utc_now()
    db.commit()
    db.refresh(mistake)

    hydrated = MistakeRepository.get_by_id(db, mistake.id, user_id=user_id)
    if hydrated is None:
        raise_not_found("mistake", mistake.id)
    return _serialize_mistake(hydrated)


def delete_mistake(db: Session, mistake_id: int, *, user_id: int) -> None:
    mistake = MistakeRepository.get_by_id(db, mistake_id, user_id=user_id)
    if mistake is None:
        raise_not_found("mistake", mistake_id)

    db.delete(mistake)
    db.commit()
