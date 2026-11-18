"""Tag practice scores with their sample module.

Revision ID: 22ed76da497f
Revises: b4d27ca161ee
"""
from alembic import op
import sqlalchemy as sa

revision='22ed76da497f'
down_revision='b4d27ca161ee'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('demo_checkpoint_results',sa.Column('module_number',sa.Integer(),server_default='3',nullable=False))

def downgrade():
    op.drop_column('demo_checkpoint_results','module_number')
