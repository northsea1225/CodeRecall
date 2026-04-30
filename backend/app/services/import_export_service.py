from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import raise_api_error
from app.models import Category, Mistake, MistakeStatus, ReviewResult, Tag
from app.models.review import ReviewLog, ReviewSession, ReviewSessionItem
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
    ExportMistakeV3,
    ExportResponseV3,
    ExportReviewLog,
    ExportReviewSession,
    ExportReviewSessionItem,
    ImportCategory,
    ImportTag,
    ImportMistake,
    ImportCount,
    ImportPayload,
    ImportPayloadV3,
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


def _owner_filter(model, user_id: int):
    return [model.user_id == user_id]


def export_data(db: Session, include: Iterable[str], *, user_id: int) -> ExportResponse:
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
                select(Category)
                .where(*_owner_filter(Category, user_id))
                .order_by(Category.created_at.desc(), Category.id.desc())
            ).all()
        ]

    if "tags" in selected:
        tags = [
            {
                "name": tag.name,
            }
            for tag in db.scalars(
                select(Tag).where(*_owner_filter(Tag, user_id)).order_by(Tag.created_at.desc(), Tag.id.desc())
            ).all()
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
                MistakeRepository._base_query()
                .where(*_owner_filter(Mistake, user_id))
                .order_by(Mistake.created_at.desc(), Mistake.id.desc())
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


def export_mistakes_v2(db: Session, *, user_id: int) -> list[dict[str, Any]]:
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
            MistakeRepository._base_query()
            .where(*_owner_filter(Mistake, user_id))
            .order_by(Mistake.created_at.desc(), Mistake.id.desc())
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


def import_data(db: Session, payload: ImportPayload, strategy: str, *, user_id: int) -> ImportResponse:
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
            existing_category = db.scalar(
                select(Category).where(Category.name == category_name, *_owner_filter(Category, user_id))
            )
            if existing_category is not None:
                skipped.append(_skip("category", category_name, "already_exists"))
                continue

            db.add(
                Category(
                    user_id=user_id,
                    name=category_name,
                    description=description,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
            db.flush()
            imported["categories"] += 1

        for tag_name in sorted(tag_names):
            existing_tag = db.scalar(select(Tag).where(Tag.name == tag_name, *_owner_filter(Tag, user_id)))
            if existing_tag is not None:
                skipped.append(_skip("tag", tag_name, "already_exists"))
                continue

            db.add(Tag(name=tag_name, user_id=user_id, created_at=utc_now(), updated_at=utc_now()))
            db.flush()
            imported["tags"] += 1

        for record in valid_mistakes:
            category_name = normalize_required_text(record.category_name, field_name="mistakes.category_name")
            category = db.scalar(
                select(Category).where(Category.name == category_name, *_owner_filter(Category, user_id))
            )
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
                user_id=user_id,
                title=normalized_title,
                language=normalized_language,
                category_id=category.id,
            )
            if existing_mistake is not None:
                skipped.append(_skip("mistake", normalized_title, "already_exists"))
                continue

            tags = get_or_create_tags(db, record.tag_names, user_id=user_id)
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
                user_id=user_id,
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
    *,
    user_id: int,
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
        user_id=user_id,
    )


def get_or_create_names(values: Iterable[str]) -> set[str]:
    return {
        normalize_required_text(value, field_name="mistakes.tag_names")
        for value in values
    }


def import_data_v3(db: Session, payload: ImportPayloadV3, strategy: str, *, user_id: int) -> ImportResponse:
    if payload.format != "coderecall" or payload.schema_version != 3:
        raise_api_error(
            400,
            "invalid_import_version",
            "Import payload must use CodeRecall schema version 3.",
            {"format": payload.format, "schema_version": payload.schema_version},
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

    imported = {
        "categories": 0,
        "tags": 0,
        "mistakes": 0,
        "review_sessions": 0,
        "review_session_items": 0,
        "review_logs": 0,
    }
    skipped: list[ImportSkip] = []
    valid_mistakes = []

    for record in payload.mistakes:
        if not record.uuid:
            skipped.append(_skip("mistake", record.title, "missing_uuid"))
            continue
        uuid_str = str(record.uuid).lower()
        if not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            uuid_str,
        ):
            skipped.append(_skip("mistake", uuid_str, "invalid_uuid_format"))
            continue
        reason = _sm2_skip_reason(record)
        if reason is None:
            reason = _field_length_skip_reason(record)
        if reason is not None:
            skipped.append(_skip("mistake", uuid_str, reason))
            continue
        try:
            MistakeStatus(record.status)
        except ValueError:
            skipped.append(_skip("mistake", uuid_str, "invalid_status"))
            continue
        valid_mistakes.append(record)

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
            existing_category = db.scalar(
                select(Category).where(Category.name == category_name, *_owner_filter(Category, user_id))
            )
            if existing_category is not None:
                skipped.append(_skip("category", category_name, "already_exists"))
                continue

            db.add(
                Category(
                    user_id=user_id,
                    name=category_name,
                    description=description,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
            db.flush()
            imported["categories"] += 1

        for tag_name in sorted(tag_names):
            existing_tag = db.scalar(select(Tag).where(Tag.name == tag_name, *_owner_filter(Tag, user_id)))
            if existing_tag is not None:
                skipped.append(_skip("tag", tag_name, "already_exists"))
                continue

            db.add(Tag(name=tag_name, user_id=user_id, created_at=utc_now(), updated_at=utc_now()))
            db.flush()
            imported["tags"] += 1

        incoming_uuids = [str(record.uuid).lower() for record in valid_mistakes if record.uuid]
        uuid_to_id: dict[str, int] = {}
        if incoming_uuids:
            existing_rows = db.execute(
                select(Mistake.uuid, Mistake.id).where(
                    Mistake.user_id == user_id,
                    func.lower(Mistake.uuid).in_(incoming_uuids),
                )
            ).all()
            for row in existing_rows:
                if not row.uuid:
                    continue
                key = str(row.uuid).lower()
                uuid_to_id[key] = row.id

        for record in valid_mistakes:
            uuid_str = str(record.uuid).lower()
            if uuid_str in uuid_to_id:
                skipped.append(_skip("mistake", uuid_str, "already_exists"))
                continue

            category_name = normalize_required_text(record.category_name, field_name="mistakes.category_name")
            category = db.scalar(
                select(Category).where(Category.name == category_name, *_owner_filter(Category, user_id))
            )
            if category is None:
                raise_api_error(
                    400,
                    "missing_import_category",
                    "Import mistake references a missing category.",
                    {"category_name": category_name},
                )

            normalized_title = normalize_required_text(record.title, field_name="mistakes.title")
            normalized_language = normalize_required_text(record.language, field_name="mistakes.language")
            tags = get_or_create_tags(db, record.tag_names, user_id=user_id)
            mistake = Mistake(
                uuid=uuid_str,
                user_id=user_id,
                title=normalized_title,
                stem_markdown=record.stem_markdown,
                wrong_answer_markdown=record.wrong_answer_markdown,
                correct_answer_markdown=record.correct_answer_markdown,
                error_reason_markdown=record.error_reason_markdown,
                language=normalized_language,
                difficulty=record.difficulty,
                source=normalize_optional_text(record.source) or "",
                status=MistakeStatus(record.status),
                category_id=category.id,
                ease_factor=record.ease_factor,
                interval_days=record.interval_days,
                repetition=record.repetition,
                next_review_at=record.next_review_at,
                is_archived=record.is_archived,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
            mistake.tags = tags
            db.add(mistake)
            db.flush()
            uuid_to_id[uuid_str] = mistake.id
            imported["mistakes"] += 1

        session_id_map: dict[int, int] = {}
        if uuid_to_id:
            for source_session in payload.review_sessions:
                if source_session.id in session_id_map:
                    skipped.append(_skip("review_session", str(source_session.id), "duplicate"))
                    continue
                existing_session = db.scalar(
                    select(ReviewSession).where(
                        ReviewSession.user_id == user_id,
                        ReviewSession.started_at == source_session.started_at,
                        ReviewSession.strategy == (source_session.strategy or "manual"),
                        ReviewSession.ended_at == source_session.ended_at,
                        ReviewSession.total_count == source_session.total_count,
                        ReviewSession.completed_count == source_session.completed_count,
                    )
                )
                if existing_session is not None:
                    session_id_map[source_session.id] = existing_session.id
                    skipped.append(_skip("review_session", str(source_session.id), "already_imported"))
                    continue
                session = ReviewSession(
                    user_id=user_id,
                    started_at=source_session.started_at,
                    ended_at=source_session.ended_at,
                    strategy=source_session.strategy,
                    total_count=source_session.total_count,
                    completed_count=source_session.completed_count,
                )
                db.add(session)
                db.flush()
                session_id_map[source_session.id] = session.id
                imported["review_sessions"] += 1

            seen_session_mistakes: set[tuple[int, int]] = set()
            seen_session_orders: set[tuple[int, int]] = set()
            for item in payload.review_session_items:
                new_session_id = session_id_map.get(item.session_id)
                if new_session_id is None:
                    skipped.append(_skip("review_session_item", str(item.session_id), "missing_session"))
                    continue
                if not item.mistake_uuid:
                    skipped.append(_skip("review_session_item", str(item.session_id), "missing_mistake_uuid"))
                    continue
                mistake_id = uuid_to_id.get(str(item.mistake_uuid).lower())
                if mistake_id is None:
                    skipped.append(_skip("review_session_item", str(item.mistake_uuid).lower(), "missing_mistake"))
                    continue

                session_mistake_key = (new_session_id, mistake_id)
                if session_mistake_key in seen_session_mistakes:
                    skipped.append(_skip("review_session_item", str(item.mistake_uuid), "duplicate"))
                    continue
                session_order_key = (new_session_id, item.order_index)
                if session_order_key in seen_session_orders:
                    skipped.append(_skip("review_session_item", str(item.order_index), "duplicate_order"))
                    continue

                existing_item = db.scalar(
                    select(ReviewSessionItem).where(
                        ReviewSessionItem.session_id == new_session_id,
                        ReviewSessionItem.mistake_id == mistake_id,
                    )
                )
                if existing_item is not None:
                    skipped.append(_skip("review_session_item", str(item.mistake_uuid), "already_imported"))
                    continue

                existing_order_item = db.scalar(
                    select(ReviewSessionItem).where(
                        ReviewSessionItem.session_id == new_session_id,
                        ReviewSessionItem.order_index == item.order_index,
                    )
                )
                if existing_order_item is not None:
                    skipped.append(_skip("review_session_item", str(item.order_index), "duplicate_order"))
                    continue

                seen_session_mistakes.add(session_mistake_key)
                seen_session_orders.add(session_order_key)
                db.add(
                    ReviewSessionItem(
                        session_id=new_session_id,
                        mistake_id=mistake_id,
                        order_index=item.order_index,
                    )
                )
                imported["review_session_items"] += 1

            for log in payload.review_logs:
                if not log.mistake_uuid:
                    skipped.append(_skip("review_log", "unknown", "missing_mistake_uuid"))
                    continue
                mistake_id = uuid_to_id.get(str(log.mistake_uuid).lower())
                if mistake_id is None:
                    skipped.append(_skip("review_log", str(log.mistake_uuid).lower(), "missing_mistake"))
                    continue

                new_session_id = None
                if log.session_id is not None:
                    new_session_id = session_id_map.get(log.session_id)
                    if new_session_id is None:
                        skipped.append(_skip("review_log", str(log.mistake_uuid), "missing_session"))
                        continue
                try:
                    result = ReviewResult(log.user_result)
                except ValueError:
                    skipped.append(_skip("review_log", str(log.mistake_uuid), "invalid_user_result"))
                    continue

                existing_log = db.scalar(
                    select(ReviewLog).where(
                        ReviewLog.mistake_id == mistake_id,
                        ReviewLog.session_id == new_session_id,
                        ReviewLog.shown_at == log.shown_at,
                    )
                )
                if existing_log is not None:
                    skipped.append(_skip("review_log", str(log.mistake_uuid), "already_imported"))
                    continue

                db.add(
                    ReviewLog(
                        user_id=user_id,
                        mistake_id=mistake_id,
                        session_id=new_session_id,
                        review_mode=log.review_mode,
                        user_result=result,
                        shown_at=log.shown_at,
                        answered_at=log.answered_at,
                        old_interval_days=log.old_interval_days,
                        new_interval_days=log.new_interval_days,
                        old_ease_factor=log.old_ease_factor,
                        new_ease_factor=log.new_ease_factor,
                        time_spent_ms=log.time_spent_ms,
                        note=log.note or "",
                    )
                )
                imported["review_logs"] += 1
        else:
            for source_session in payload.review_sessions:
                skipped.append(_skip("review_session", str(source_session.id), "no_imported_mistakes"))
            for item in payload.review_session_items:
                skipped.append(_skip("review_session_item", str(item.session_id), "no_imported_mistakes"))
            for log in payload.review_logs:
                skipped.append(_skip("review_log", str(log.mistake_uuid or "unknown"), "no_imported_mistakes"))

        db.commit()
    except Exception:
        db.rollback()
        raise

    return ImportResponse(
        version="v3",
        imported=ImportCount(**imported),
        skipped=skipped,
    )


def export_data_v3(db: Session, *, user_id: int) -> ExportResponseV3:
    categories = [
        ImportCategory(name=c.name, description=c.description or "")
        for c in db.scalars(select(Category).where(*_owner_filter(Category, user_id)).order_by(Category.id)).all()
    ]
    tags = [
        ImportTag(name=t.name)
        for t in db.scalars(select(Tag).where(*_owner_filter(Tag, user_id)).order_by(Tag.id)).all()
    ]
    mistakes_orm = db.scalars(
        select(Mistake)
        .options(selectinload(Mistake.tags), selectinload(Mistake.category), selectinload(Mistake.review_logs))
        .where(*_owner_filter(Mistake, user_id))
        .order_by(Mistake.id)
    ).all()
    mistakes_v3 = [
        ExportMistakeV3(
            uuid=m.uuid,
            legacy_id=m.id,
            title=m.title,
            stem_markdown=m.stem_markdown,
            wrong_answer_markdown=m.wrong_answer_markdown,
            correct_answer_markdown=m.correct_answer_markdown,
            error_reason_markdown=m.error_reason_markdown,
            language=m.language,
            difficulty=m.difficulty,
            source=m.source,
            status=m.status.value,
            category_name=m.category.name,
            tag_names=[tag.name for tag in m.tags],
            ease_factor=m.ease_factor,
            interval_days=m.interval_days,
            repetition=m.repetition,
            next_review_at=m.next_review_at,
            is_archived=m.is_archived,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in mistakes_orm
    ]
    uuid_by_id = {m.id: m.uuid for m in mistakes_orm}
    sessions_orm = db.scalars(
        select(ReviewSession).where(*_owner_filter(ReviewSession, user_id)).order_by(ReviewSession.id)
    ).all()
    sessions_v3 = [
        ExportReviewSession(
            id=s.id,
            started_at=s.started_at,
            ended_at=s.ended_at,
            strategy=s.strategy,
            total_count=s.total_count,
            completed_count=s.completed_count,
        )
        for s in sessions_orm
    ]
    items_orm = db.scalars(
        select(ReviewSessionItem)
        .join(ReviewSession, ReviewSessionItem.session_id == ReviewSession.id)
        .where(*_owner_filter(ReviewSession, user_id))
        .order_by(ReviewSessionItem.session_id, ReviewSessionItem.order_index)
    ).all()
    items_v3 = [
        ExportReviewSessionItem(
            session_id=item.session_id,
            mistake_uuid=uuid_by_id.get(item.mistake_id),
            order_index=item.order_index,
        )
        for item in items_orm
    ]
    logs_orm = db.scalars(select(ReviewLog).where(*_owner_filter(ReviewLog, user_id)).order_by(ReviewLog.shown_at)).all()
    logs_v3 = [
        ExportReviewLog(
            mistake_uuid=uuid_by_id.get(log.mistake_id),
            session_id=log.session_id,
            review_mode=log.review_mode,
            user_result=log.user_result.value,
            shown_at=log.shown_at,
            answered_at=log.answered_at,
            old_interval_days=log.old_interval_days,
            new_interval_days=log.new_interval_days,
            old_ease_factor=log.old_ease_factor,
            new_ease_factor=log.new_ease_factor,
            time_spent_ms=log.time_spent_ms,
            note=log.note or "",
        )
        for log in logs_orm
    ]
    return ExportResponseV3(
        exported_at=utc_now(),
        categories=categories,
        tags=tags,
        mistakes=mistakes_v3,
        review_sessions=sessions_v3,
        review_session_items=items_v3,
        review_logs=logs_v3,
    )
