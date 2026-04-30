from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, Float, ForeignKey, Index
from sqlalchemy import Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.review import ReviewLog
    from app.models.tag import Tag
    from app.models.user import User


class MistakeStatus(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    REVIEWING = "reviewing"
    MASTERED = "mastered"


class Mistake(Base):
    __tablename__ = "mistakes"
    __table_args__ = (
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="ck_mistakes_difficulty_range"),
        Index("ix_mistakes_status_next_review_at", "status", "next_review_at"),
        Index(
            "ix_mistakes_user_uuid",
            "user_id",
            "uuid",
            unique=True,
            sqlite_where=sa.text("uuid IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        default=lambda: str(uuid4()),
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_mistakes_user_id_users"), index=True, nullable=False)
    stem_markdown: Mapped[str] = mapped_column(Text)
    wrong_answer_markdown: Mapped[str] = mapped_column(Text)
    correct_answer_markdown: Mapped[str] = mapped_column(Text)
    error_reason_markdown: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(50), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    difficulty: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(255), default="", server_default="")
    status: Mapped[MistakeStatus] = mapped_column(
        SqlEnum(MistakeStatus, name="mistake_status", native_enum=False),
        default=MistakeStatus.NEW,
        server_default=MistakeStatus.NEW.value,
    )
    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        doc="跨 session 累计总复习次数；当前 session 计数请查 ReviewSession.completed_count。",
    )
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, server_default="2.5")
    interval_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    repetition: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="mistakes")
    category: Mapped["Category"] = relationship("Category", back_populates="mistakes")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="mistake_tags",
        back_populates="mistakes",
    )
    review_logs: Mapped[list["ReviewLog"]] = relationship(
        "ReviewLog",
        back_populates="mistake",
        cascade="all, delete-orphan",
    )
