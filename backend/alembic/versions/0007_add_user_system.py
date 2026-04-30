"""add user system

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-24 00:00:00
"""

from __future__ import annotations

import os

from alembic import op
from passlib.context import CryptContext
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "users" not in inspector.get_table_names():
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("display_name", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        )
        op.create_index("ix_users_username", "users", ["username"], unique=True)
    elif "ix_users_username" not in {index["name"] for index in inspector.get_indexes("users")}:
        op.create_index("ix_users_username", "users", ["username"], unique=True)

    password = os.environ.get("OLD_USER_INITIAL_PASSWORD", "coderecall")
    password_hash = pwd_context.hash(password)
    existing_old_user = conn.execute(sa.text("SELECT id FROM users WHERE username = 'old_user'")).scalar()
    if existing_old_user is None:
        conn.execute(
            sa.text(
                """
                INSERT INTO users (username, password_hash, display_name, is_active)
                VALUES (:username, :password_hash, :display_name, 1)
                """
            ),
            {"username": "old_user", "password_hash": password_hash, "display_name": "old user"},
        )
    old_user_id = conn.execute(sa.text("SELECT id FROM users WHERE username = 'old_user'")).scalar_one()

    for table_name in ("mistakes", "categories", "tags", "review_sessions", "review_logs"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        if "user_id" not in columns:
            op.add_column(table_name, sa.Column("user_id", sa.Integer(), nullable=True))
        if f"ix_{table_name}_user_id" not in indexes:
            op.create_index(f"ix_{table_name}_user_id", table_name, ["user_id"], unique=False)
        conn.execute(sa.text(f"UPDATE {table_name} SET user_id = :user_id"), {"user_id": old_user_id})

    category_indexes = {index["name"] for index in inspector.get_indexes("categories")}
    tag_indexes = {index["name"] for index in inspector.get_indexes("tags")}
    if "ix_categories_name" in category_indexes:
        op.drop_index("ix_categories_name", table_name="categories")
        category_indexes.remove("ix_categories_name")
    if "ix_tags_name" in tag_indexes:
        op.drop_index("ix_tags_name", table_name="tags")
        tag_indexes.remove("ix_tags_name")
    if "ix_categories_name" not in category_indexes:
        op.create_index("ix_categories_name", "categories", ["name"], unique=False)
    if "ix_tags_name" not in tag_indexes:
        op.create_index("ix_tags_name", "tags", ["name"], unique=False)

    for table_name in ("categories", "tags", "mistakes", "review_sessions", "review_logs"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_foreign_key(f"fk_{table_name}_user_id_users", "users", ["user_id"], ["id"])

    with op.batch_alter_table("categories") as batch_op:
        batch_op.create_unique_constraint("uq_categories_user_name", ["user_id", "name"])
    with op.batch_alter_table("tags") as batch_op:
        batch_op.create_unique_constraint("uq_tags_user_name", ["user_id", "name"])


def downgrade() -> None:
    with op.batch_alter_table("tags") as batch_op:
        batch_op.drop_constraint("uq_tags_user_name", type_="unique")
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint("uq_categories_user_name", type_="unique")

    for table_name in ("review_logs", "review_sessions", "mistakes", "tags", "categories"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(f"fk_{table_name}_user_id_users", type_="foreignkey")
            batch_op.drop_index(f"ix_{table_name}_user_id")
            batch_op.drop_column("user_id")

    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_index("ix_categories_name", table_name="categories")
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
