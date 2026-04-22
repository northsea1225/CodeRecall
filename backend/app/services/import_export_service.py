from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.models import Category, Mistake, MistakeStatus, Tag
from app.repositories import MistakeRepository
from app.schemas.mistake_constraints import (
    MAX_ERROR_REASON_LEN,
    MAX_LANGUAGE_LEN,
    MAX_MARKDOWN_LEN,
    MAX_SOURCE_LEN,
    MAX_TITLE_LEN,
)
from app.schemas.import_export import (
    ExportResponse,
    ImportMistake,
    ImportCount,
    ImportPayload,
    ImportResponse,
    ImportSkip,
)
from app.services.taxonomy_service import get_or_create_tags, normalize_optional_text, normalize_required_text


EXPORTABLE_FIELDS = {"mistakes", "categories", "tags"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_export_include(include: Optional[str]) -> set[str]:
    if not include:
        return set(EXPORTABLE_FIELDS)

    requested = {item.strip() for item in include.split(",") if item.strip()}
    invalid_items = sorted(requested - EXPORTABLE_FIELDS)
    if invalid_items:
        raise_api_error(
            400,
            "invalid_export_include",
            "Export include contains unsupported resources.",
            {"include": invalid_items},
        )
    return requested


def export_data(db: Session, include: Iterable[str]) -> ExportResponse:
    selected = set(include)
    categories = []
    tags = []
    mistakes = []

    if "categories" in selected:
        categories = [
            {
                "name": category.name,
                "description": category.description,
            }
            for category in db.scalars(
                select(Category).order_by(Category.created_at.desc(), Category.id.desc())
            ).all()
        ]

    if "tags" in selected:
        tags = [
            {
                "name": tag.name,
            }
            for tag in db.scalars(select(Tag).order_by(Tag.created_at.desc(), Tag.id.desc())).all()
        ]

    if "mistakes" in selected:
        mistakes = [
            {
                "title": mistake.title,
                "stem_markdown": mistake.stem_markdown,
                "wrong_answer_markdown": mistake.wrong_answer_markdown,
                "correct_answer_markdown": mistake.correct_answer_markdown,
                "error_reason_markdown": mistake.error_reason_markdown,
                "language": mistake.language,
                "difficulty": mistake.difficulty,
                "source": mistake.source,
                "status": mistake.status.value,
                "category_name": mistake.category.name,
                "tag_names": [tag.name for tag in mistake.tags],
                "ease_factor": mistake.ease_factor,
                "interval_days": mistake.interval_days,
                "repetition": mistake.repetition,
                "next_review_at": mistake.next_review_at,
                "is_archived": mistake.is_archived,
            }
            for mistake in db.scalars(
                MistakeRepository._base_query().order_by(Mistake.created_at.desc(), Mistake.id.desc())
            ).all()
        ]

    return ExportResponse(
        version="v1",
        schema_version="v2",
        exported_at=utc_now(),
        mistakes=mistakes,
        categories=categories,
        tags=tags,
    )


def export_mistakes_v2(db: Session) -> list[dict[str, Any]]:
    """Export the mistakes-only v2 shape used by the batch round-trip flow."""
    return [
        {
            "id": mistake.id,
            "title": mistake.title,
            "stem": mistake.stem_markdown,
            "error_reason": mistake.error_reason_markdown,
            "wrong_answer_markdown": mistake.wrong_answer_markdown,
            "correct_answer_markdown": mistake.correct_answer_markdown,
            "ease_factor": mistake.ease_factor,
            "interval_days": mistake.interval_days,
            "next_review_at": mistake.next_review_at,
            "is_archived": mistake.is_archived,
            "language": mistake.language,
            "difficulty": mistake.difficulty,
            "source": mistake.source,
            "status": mistake.status.value,
            "category_name": mistake.category.name,
            "tag_names": [tag.name for tag in mistake.tags],
            "repetition": mistake.repetition,
        }
        for mistake in db.scalars(
            MistakeRepository._base_query().order_by(Mistake.created_at.desc(), Mistake.id.desc())
        ).all()
    ]


def _skip(entity: str, identifier: str, reason: str) -> ImportSkip:
    return ImportSkip(entity=entity, identifier=identifier, reason=reason)


def _sm2_skip_reason(record) -> str | None:
    if record.ease_factor < 1.3 or record.ease_factor > 5.0:
        return "invalid_ease_factor"
    if record.interval_days < 0:
        return "invalid_interval_days"
    if record.repetition < 0:
        return "invalid_repetition"
    return None


def _field_length_skip_reason(record) -> str | None:
    if len(record.title) > MAX_TITLE_LEN:
        return "title_too_long"
    if len(record.stem_markdown) > MAX_MARKDOWN_LEN:
        return "stem_markdown_too_long"
    if len(record.wrong_answer_markdown) > MAX_MARKDOWN_LEN:
        return "wrong_answer_too_long"
    if len(record.correct_answer_markdown) > MAX_MARKDOWN_LEN:
        return "correct_answer_too_long"
    if len(record.error_reason_markdown) > MAX_ERROR_REASON_LEN:
        return "error_reason_too_long"
    if len(record.language) > MAX_LANGUAGE_LEN:
        return "language_too_long"
    if len(record.source) > MAX_SOURCE_LEN:
        return "source_too_long"
    return None


def import_data(db: Session, payload: ImportPayload, strategy: str) -> ImportResponse:
    if payload.version != "v1":
        raise_api_error(
            400,
            "invalid_import_version",
            "Import payload version must be 'v1'.",
            {"version": payload.version},
        )

    if strategy == "replace":
        raise_api_error(
            501,
            "import_strategy_not_implemented",
            "Import strategy 'replace' is not implemented yet.",
            {"strategy": strategy},
        )
    if strategy != "skip_existing":
        raise_api_error(
            400,
            "invalid_import_strategy",
            "Import strategy must be one of: skip_existing, replace.",
            {"strategy": strategy},
        )

    imported = {"mistakes": 0, "categories": 0, "tags": 0}
    skipped: list[ImportSkip] = []
    valid_mistakes = []
    for mistake in payload.mistakes:
        reason = _sm2_skip_reason(mistake)
        if reason is None:
            reason = _field_length_skip_reason(mistake)
        if reason is not None:
            skipped.append(_skip("mistake", mistake.title, reason))
            continue
        valid_mistakes.append(mistake)

    category_inputs = {
        normalize_required_text(category.name, field_name="categories.name"): normalize_optional_text(
            category.description
        )
        or ""
        for category in payload.categories
    }
    for mistake in valid_mistakes:
        category_name = normalize_required_text(mistake.category_name, field_name="mistakes.category_name")
        category_inputs.setdefault(category_name, "")

    tag_names = {
        normalize_required_text(tag.name, field_name="tags.name")
        for tag in payload.tags
    }
    for mistake in valid_mistakes:
        tag_names.update(get_or_create_names(mistake.tag_names))

    try:
        for category_name, description in category_inputs.items():
            existing_category = db.scalar(select(Category).where(Category.name == category_name))
            if existing_category is not None:
                skipped.append(_skip("category", category_name, "already_exists"))
                continue

            db.add(
                Category(
                    name=category_name,
                    description=description,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
            db.flush()
            imported["categories"] += 1

        for tag_name in sorted(tag_names):
            existing_tag = db.scalar(select(Tag).where(Tag.name == tag_name))
            if existing_tag is not None:
                skipped.append(_skip("tag", tag_name, "already_exists"))
                continue

            db.add(Tag(name=tag_name, created_at=utc_now(), updated_at=utc_now()))
            db.flush()
            imported["tags"] += 1

        for record in valid_mistakes:
            category_name = normalize_required_text(record.category_name, field_name="mistakes.category_name")
            category = db.scalar(select(Category).where(Category.name == category_name))
            if category is None:
                raise_api_error(
                    400,
                    "missing_import_category",
                    "Import mistake references a missing category.",
                    {"category_name": category_name},
                )

            normalized_title = normalize_required_text(record.title, field_name="mistakes.title")
            normalized_language = normalize_required_text(record.language, field_name="mistakes.language")
            existing_mistake = MistakeRepository.find_existing(
                db,
                title=normalized_title,
                language=normalized_language,
                category_id=category.id,
            )
            if existing_mistake is not None:
                skipped.append(_skip("mistake", normalized_title, "already_exists"))
                continue

            tags = get_or_create_tags(db, record.tag_names)
            timestamp = utc_now()
            try:
                status = MistakeStatus(record.status)
            except ValueError:
                raise_api_error(
                    400,
                    "invalid_mistake_status",
                    "Import mistake contains an unsupported status.",
                    {"status": record.status, "title": normalized_title},
                )
            mistake = Mistake(
                title=normalized_title,
                stem_markdown=record.stem_markdown,
                wrong_answer_markdown=record.wrong_answer_markdown,
                correct_answer_markdown=record.correct_answer_markdown,
                error_reason_markdown=record.error_reason_markdown,
                language=normalized_language,
                difficulty=record.difficulty,
                source=normalize_optional_text(record.source) or "",
                status=status,
                category_id=category.id,
                ease_factor=record.ease_factor,
                interval_days=record.interval_days,
                repetition=record.repetition,
                next_review_at=record.next_review_at,
                is_archived=record.is_archived,
                created_at=timestamp,
                updated_at=timestamp,
            )
            mistake.tags = tags
            db.add(mistake)
            db.flush()
            imported["mistakes"] += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return ImportResponse(
        version="v1",
        imported=ImportCount(**imported),
        skipped=skipped,
    )


def import_mistakes_v2_records(
    db: Session,
    records: list[dict[str, Any]],
    strategy: str,
) -> ImportResponse:
    mistakes = [
        ImportMistake(
            title=record.get("title", ""),
            stem_markdown=record.get("stem_markdown") or record.get("stem") or "",
            wrong_answer_markdown=record.get("wrong_answer_markdown", ""),
            correct_answer_markdown=record.get("correct_answer_markdown", ""),
            error_reason_markdown=record.get("error_reason_markdown") or record.get("error_reason") or "",
            language=record.get("language") or "unknown",
            difficulty=record.get("difficulty", 3),
            source=record.get("source", ""),
            status=record.get("status", "new"),
            category_name=record.get("category_name") or "Imported",
            tag_names=record.get("tag_names", []),
            ease_factor=record.get("ease_factor", 2.5),
            interval_days=record.get("interval_days", 0),
            repetition=record.get("repetition", 0),
            next_review_at=record.get("next_review_at"),
            is_archived=record.get("is_archived", False),
        )
        for record in records
    ]
    return import_data(
        db,
        ImportPayload(version="v1", schema_version="v2", mistakes=mistakes),
        strategy,
    )


def get_or_create_names(values: Iterable[str]) -> set[str]:
    return {
        normalize_required_text(value, field_name="mistakes.tag_names")
        for value in values
    }
