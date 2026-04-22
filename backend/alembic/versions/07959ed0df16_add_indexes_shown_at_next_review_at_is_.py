"""add_indexes_shown_at_next_review_at_is_archived

Revision ID: 07959ed0df16
Revises: 0004_review_log_time_spent
Create Date: 2026-04-20 18:46:15.253542
"""

from __future__ import annotations

from alembic import op



# revision identifiers, used by Alembic.
revision = "07959ed0df16"
down_revision = "0004_review_log_time_spent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_review_logs_shown_at"), "review_logs", ["shown_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_logs_shown_at"), table_name="review_logs")
