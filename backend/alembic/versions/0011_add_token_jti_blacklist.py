"""add token_jti_blacklist

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-02
"""

import sqlalchemy as sa
from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_jti_blacklist",
        sa.Column("jti", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("exp_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_token_jti_blacklist_user_id", "token_jti_blacklist", ["user_id"])
    op.create_index("ix_token_jti_blacklist_exp_at", "token_jti_blacklist", ["exp_at"])
    op.create_index("ix_token_jti_blacklist_user_exp", "token_jti_blacklist", ["user_id", "exp_at"])


def downgrade() -> None:
    op.drop_index("ix_token_jti_blacklist_user_exp", table_name="token_jti_blacklist")
    op.drop_index("ix_token_jti_blacklist_exp_at", table_name="token_jti_blacklist")
    op.drop_index("ix_token_jti_blacklist_user_id", table_name="token_jti_blacklist")
    op.drop_table("token_jti_blacklist")
