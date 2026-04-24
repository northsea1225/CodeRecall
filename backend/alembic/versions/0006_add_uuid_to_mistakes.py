from alembic import op
import sqlalchemy as sa
import uuid as _uuid_module

revision = '0006'
down_revision = '07959ed0df16'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('mistakes', sa.Column('uuid', sa.String(36), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text('SELECT id FROM mistakes')).fetchall()
    for row in rows:
        conn.execute(
            sa.text('UPDATE mistakes SET uuid = :uuid WHERE id = :id'),
            {'uuid': str(_uuid_module.uuid4()), 'id': row[0]}
        )
    op.create_index('ix_mistakes_uuid', 'mistakes', ['uuid'], unique=True)


def downgrade():
    op.drop_index('ix_mistakes_uuid', table_name='mistakes')
    op.drop_column('mistakes', 'uuid')
