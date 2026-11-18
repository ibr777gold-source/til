"""Add optional clarity ratings to feedback.

Revision ID: e216fbc9a3d4
Revises: ce917ebf245c
"""
from alembic import op
import sqlalchemy as sa

revision='e216fbc9a3d4'
down_revision='ce917ebf245c'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('feedback',sa.Column('clarity_rating',sa.Integer(),nullable=True))

def downgrade():
    op.drop_column('feedback','clarity_rating')
