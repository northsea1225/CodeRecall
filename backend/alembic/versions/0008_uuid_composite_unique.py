"""uuid composite unique per user

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_mistakes_uuid", table_name="mistakes")
    op.create_index(
        "ix_mistakes_user_uuid",
        "mistakes",
        ["user_id", "uuid"],
        unique=True,
        sqlite_where=sa.text("uuid IS NOT NULL"),
    )


def downgrade() -> None:
    conn = op.get_bind()
    dupes = conn.execute(
        sa.text(
            """
            SELECT uuid, COUNT(*) AS cnt
            FROM mistakes
            WHERE uuid IS NOT NULL
            GROUP BY uuid
            HAVING cnt > 1
            """
        )
    ).fetchall()
    if dupes:
        raise RuntimeError(
            f"Cannot downgrade: {len(dupes)} uuid(s) appear in multiple users' data. "
            "Remove duplicates first."
        )

    op.drop_index("ix_mistakes_user_uuid", table_name="mistakes")
    op.create_index("ix_mistakes_uuid", "mistakes", ["uuid"], unique=True)
