from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.mistake import Mistake
    from app.models.review import ReviewLog, ReviewSession
    from app.models.tag import Tag
    from app.models.token_jti_blacklist import TokenJtiBlacklist


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="", server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
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

    mistakes: Mapped[list["Mistake"]] = relationship("Mistake", back_populates="owner")
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="owner")
    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="owner")
    review_sessions: Mapped[list["ReviewSession"]] = relationship("ReviewSession", back_populates="owner")
    review_logs: Mapped[list["ReviewLog"]] = relationship("ReviewLog", back_populates="owner")
    token_blacklist_entries: Mapped[list["TokenJtiBlacklist"]] = relationship(
        "TokenJtiBlacklist",
        back_populates="user",
        cascade="all, delete-orphan",
    )
