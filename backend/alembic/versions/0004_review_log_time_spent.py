"""add time_spent_ms to review logs

Revision ID: 0004_review_log_time_spent
Revises: 0003_review_session_items
Create Date: 2026-04-26 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_review_log_time_spent"
down_revision = "0003_review_session_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.add_column(sa.Column("time_spent_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.drop_column("time_spent_ms")
