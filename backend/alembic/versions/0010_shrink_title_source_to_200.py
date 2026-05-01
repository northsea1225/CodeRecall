"""shrink mistakes.title and mistakes.source from String(255) to String(200)

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-01

Aligns ORM column width with the Pydantic schema constraint
(MAX_TITLE_LEN / MAX_SOURCE_LEN = 200) so future Postgres/MySQL
migrations enforce the same limit. SQLite ignores String length
declarations, so this migration is a no-op there but preserves
schema parity.
"""

import sqlalchemy as sa
from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("mistakes") as batch:
        batch.alter_column(
            "title",
            existing_type=sa.String(length=255),
            type_=sa.String(length=200),
            existing_nullable=False,
        )
        batch.alter_column(
            "source",
            existing_type=sa.String(length=255),
            type_=sa.String(length=200),
            existing_nullable=False,
            existing_server_default="",
        )


def downgrade() -> None:
    with op.batch_alter_table("mistakes") as batch:
        batch.alter_column(
            "source",
            existing_type=sa.String(length=200),
            type_=sa.String(length=255),
            existing_nullable=False,
            existing_server_default="",
        )
        batch.alter_column(
            "title",
            existing_type=sa.String(length=200),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
