"""Record owner role changes.

Revision ID: 41f9a380bc27
Revises: 3a7c9f142b01
"""
from alembic import op
import sqlalchemy as sa
revision='41f9a380bc27'
down_revision='3a7c9f142b01'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('owner_role_events',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('target_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=True),
        sa.Column('role',sa.String(20),nullable=False),
        sa.Column('enabled',sa.Boolean(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))

def downgrade():
    op.drop_table('owner_role_events')
