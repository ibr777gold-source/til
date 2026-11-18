"""Add explicit owner access.

Revision ID: 3a7c9f142b01
Revises: 7d0b3a82c4fe
"""
from alembic import op
import sqlalchemy as sa
revision = '3a7c9f142b01'
down_revision = '7d0b3a82c4fe'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('owner_access', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True))

def downgrade():
    op.drop_table('owner_access')
