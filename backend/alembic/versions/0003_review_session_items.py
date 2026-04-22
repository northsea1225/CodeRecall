"""review session items queue

Revision ID: 0003_review_session_items
Revises: 0002_review_result_enum
Create Date: 2026-04-24 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_review_session_items"
down_revision = "0002_review_result_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_session_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("mistake_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["review_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mistake_id"], ["mistakes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "order_index", name="uq_review_session_items_session_order"),
        sa.UniqueConstraint("session_id", "mistake_id", name="uq_review_session_items_session_mistake"),
    )
    op.create_index("ix_review_session_items_session_id", "review_session_items", ["session_id"], unique=False)
    op.create_index("ix_review_session_items_mistake_id", "review_session_items", ["mistake_id"], unique=False)
    op.create_index(
        "ix_review_session_items_session_id_order_index",
        "review_session_items",
        ["session_id", "order_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_review_session_items_session_id_order_index", table_name="review_session_items")
    op.drop_index("ix_review_session_items_mistake_id", table_name="review_session_items")
    op.drop_index("ix_review_session_items_session_id", table_name="review_session_items")
    op.drop_table("review_session_items")
