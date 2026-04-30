from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Mistake


class MistakeRepository:
    @staticmethod
    def _build_filters(
        *,
        user_id: Optional[int] = None,
        category_id: Optional[int] = None,
        language: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> list:
        filters = []
        if user_id is not None:
            filters.append(Mistake.user_id == user_id)
        if category_id is not None:
            filters.append(Mistake.category_id == category_id)
        if language:
            filters.append(Mistake.language == language)
        if keyword:
            searchable_columns = (
                Mistake.title,
                Mistake.stem_markdown,
                Mistake.wrong_answer_markdown,
                Mistake.correct_answer_markdown,
                Mistake.error_reason_markdown,
            )
            for term in keyword.split():
                filters.append(or_(*(column.ilike(f"%{term}%") for column in searchable_columns)))
        return filters

    @staticmethod
    def _base_query() -> Select[Mistake]:
        return select(Mistake).options(
            joinedload(Mistake.category),
            selectinload(Mistake.tags),
        )

    @staticmethod
    def list(
        db: Session,
        *,
        user_id: Optional[int] = None,
        page: int,
        page_size: int,
        category_id: Optional[int] = None,
        language: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> list[Mistake]:
        filters = MistakeRepository._build_filters(
            user_id=user_id,
            category_id=category_id,
            language=language,
            keyword=keyword,
        )

        statement = (
            MistakeRepository._base_query()
            .where(*filters)
            .order_by(Mistake.created_at.desc(), Mistake.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def count(
        db: Session,
        *,
        user_id: Optional[int] = None,
        category_id: Optional[int] = None,
        language: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> int:
        filters = MistakeRepository._build_filters(
            user_id=user_id,
            category_id=category_id,
            language=language,
            keyword=keyword,
        )

        statement = select(func.count()).select_from(Mistake).where(*filters)
        return int(db.scalar(statement) or 0)

    @staticmethod
    def get_by_id(db: Session, mistake_id: int, user_id: Optional[int] = None) -> Optional[Mistake]:
        filters = [Mistake.id == mistake_id]
        if user_id is not None:
            filters.append(Mistake.user_id == user_id)
        statement = MistakeRepository._base_query().where(*filters)
        return db.scalar(statement)

    @staticmethod
    def find_existing(
        db: Session,
        *,
        user_id: Optional[int] = None,
        title: str,
        language: str,
        category_id: int,
    ) -> Optional[Mistake]:
        statement = MistakeRepository._base_query().where(
            Mistake.title == title,
            Mistake.language == language,
            Mistake.category_id == category_id,
        )
        if user_id is not None:
            statement = statement.where(Mistake.user_id == user_id)
        return db.scalar(statement)
