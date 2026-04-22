"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-17 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


mistake_status = sa.Enum(
    "new",
    "learning",
    "reviewing",
    "mastered",
    name="mistake_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"], unique=False)

    op.create_table(
        "review_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("strategy", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_review_sessions_started_at", "review_sessions", ["started_at"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "mistakes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("stem_markdown", sa.Text(), nullable=False),
        sa.Column("wrong_answer_markdown", sa.Text(), nullable=False),
        sa.Column("correct_answer_markdown", sa.Text(), nullable=False),
        sa.Column("error_reason_markdown", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", mistake_status, nullable=False, server_default="new"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetition", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="ck_mistakes_difficulty_range"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
    )
    op.create_index("ix_mistakes_category_id", "mistakes", ["category_id"], unique=False)
    op.create_index("ix_mistakes_is_archived", "mistakes", ["is_archived"], unique=False)
    op.create_index("ix_mistakes_language", "mistakes", ["language"], unique=False)
    op.create_index("ix_mistakes_next_review_at", "mistakes", ["next_review_at"], unique=False)
    op.create_index("ix_mistakes_status_next_review_at", "mistakes", ["status", "next_review_at"], unique=False)
    op.create_index("ix_mistakes_title", "mistakes", ["title"], unique=False)

    op.create_table(
        "mistake_tags",
        sa.Column("mistake_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["mistake_id"], ["mistakes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mistake_id", "tag_id"),
    )

    op.create_table(
        "review_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mistake_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("review_mode", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("user_result", sa.String(length=50), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("old_interval_days", sa.Integer(), nullable=True),
        sa.Column("new_interval_days", sa.Integer(), nullable=True),
        sa.Column("old_ease_factor", sa.Float(), nullable=True),
        sa.Column("new_ease_factor", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["mistake_id"], ["mistakes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["review_sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_review_logs_mistake_id", "review_logs", ["mistake_id"], unique=False)
    op.create_index("ix_review_logs_session_id", "review_logs", ["session_id"], unique=False)
    op.create_index("ix_review_logs_mistake_id_shown_at", "review_logs", ["mistake_id", "shown_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_review_logs_mistake_id_shown_at", table_name="review_logs")
    op.drop_index("ix_review_logs_session_id", table_name="review_logs")
    op.drop_index("ix_review_logs_mistake_id", table_name="review_logs")
    op.drop_table("review_logs")

    op.drop_table("mistake_tags")

    op.drop_index("ix_mistakes_title", table_name="mistakes")
    op.drop_index("ix_mistakes_status_next_review_at", table_name="mistakes")
    op.drop_index("ix_mistakes_next_review_at", table_name="mistakes")
    op.drop_index("ix_mistakes_language", table_name="mistakes")
    op.drop_index("ix_mistakes_is_archived", table_name="mistakes")
    op.drop_index("ix_mistakes_category_id", table_name="mistakes")
    op.drop_table("mistakes")

    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")

    op.drop_index("ix_review_sessions_started_at", table_name="review_sessions")
    op.drop_table("review_sessions")

    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")
