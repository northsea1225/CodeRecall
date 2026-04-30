from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.mistake import Mistake
    from app.models.user import User


class ReviewResult(str, Enum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_review_sessions_user_id_users"), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    strategy: Mapped[str] = mapped_column(String(50), default="manual", server_default="manual")
    total_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    owner: Mapped["User"] = relationship("User", back_populates="review_sessions")
    review_logs: Mapped[list["ReviewLog"]] = relationship(
        "ReviewLog",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    session_items: Mapped[list["ReviewSessionItem"]] = relationship(
        "ReviewSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ReviewSessionItem.order_index",
    )


class ReviewSessionItem(Base):
    __tablename__ = "review_session_items"
    __table_args__ = (
        UniqueConstraint("session_id", "order_index", name="uq_review_session_items_session_order"),
        UniqueConstraint("session_id", "mistake_id", name="uq_review_session_items_session_mistake"),
        Index("ix_review_session_items_session_id_order_index", "session_id", "order_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("review_sessions.id", ondelete="CASCADE"), index=True)
    mistake_id: Mapped[int] = mapped_column(ForeignKey("mistakes.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped["ReviewSession"] = relationship("ReviewSession", back_populates="session_items")
    mistake: Mapped["Mistake"] = relationship("Mistake")


class ReviewLog(Base):
    __tablename__ = "review_logs"
    __table_args__ = (
        Index("ix_review_logs_mistake_id_shown_at", "mistake_id", "shown_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", name="fk_review_logs_user_id_users"), index=True, nullable=False)
    mistake_id: Mapped[int] = mapped_column(ForeignKey("mistakes.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("review_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    review_mode: Mapped[str] = mapped_column(String(50), default="manual", server_default="manual")
    user_result: Mapped[ReviewResult] = mapped_column(
        SqlEnum(ReviewResult, name="review_result", native_enum=False)
    )
    shown_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    old_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    new_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    old_ease_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_ease_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_spent_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", server_default="")

    owner: Mapped["User"] = relationship("User", back_populates="review_logs")
    mistake: Mapped["Mistake"] = relationship("Mistake", back_populates="review_logs")
    session: Mapped[Optional["ReviewSession"]] = relationship("ReviewSession", back_populates="review_logs")
