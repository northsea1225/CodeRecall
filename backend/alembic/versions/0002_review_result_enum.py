"""review result enum

Revision ID: 0002_review_result_enum
Revises: 0001_initial
Create Date: 2026-04-23 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_review_result_enum"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


review_result = sa.Enum(
    "again",
    "hard",
    "good",
    "easy",
    name="review_result",
    native_enum=False,
)

old_review_result = sa.String(length=50)


def upgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.alter_column(
            "user_result",
            existing_type=old_review_result,
            type_=review_result,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("review_logs") as batch_op:
        batch_op.alter_column(
            "user_result",
            existing_type=review_result,
            type_=old_review_result,
            existing_nullable=False,
        )
