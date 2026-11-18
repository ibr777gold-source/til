"""Allow feedback from a guest preview.

Revision ID: 8f2c1e93a0bb
Revises: c8cbca635471
"""
from alembic import op
import sqlalchemy as sa

revision = '8f2c1e93a0bb'
down_revision = 'c8cbca635471'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('feedback') as batch:
        batch.alter_column('user_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    connection=op.get_bind()
    if connection.execute(sa.text('SELECT COUNT(*) FROM feedback WHERE user_id IS NULL')).scalar():
        raise RuntimeError('Guest feedback exists; export and remove it before downgrade')
    with op.batch_alter_table('feedback') as batch:
        batch.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
