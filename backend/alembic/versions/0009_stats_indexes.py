"""stats indexes for SQL pushdown

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-01
"""

from alembic import op


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_review_logs_user_shown",
        "review_logs",
        ["user_id", "shown_at"],
        unique=False,
    )
    op.create_index(
        "ix_mistakes_user_next_review",
        "mistakes",
        ["user_id", "next_review_at"],
        unique=False,
    )
    op.create_index(
        "ix_mistakes_user_archived",
        "mistakes",
        ["user_id", "is_archived"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mistakes_user_archived", table_name="mistakes")
    op.drop_index("ix_mistakes_user_next_review", table_name="mistakes")
    op.drop_index("ix_review_logs_user_shown", table_name="review_logs")
