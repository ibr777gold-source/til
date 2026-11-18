"""Save lesson and question context with new feedback.

Revision ID: 7d0b3a82c4fe
Revises: e216fbc9a3d4
"""
from alembic import op
import sqlalchemy as sa
revision='7d0b3a82c4fe'
down_revision='e216fbc9a3d4'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('feedback',sa.Column('lesson_title',sa.String(200),nullable=True))
    op.add_column('feedback',sa.Column('exercise_id',sa.String(80),nullable=True))
    op.add_column('feedback',sa.Column('exercise_prompt',sa.String(1000),nullable=True))

def downgrade():
    op.drop_column('feedback','exercise_prompt')
    op.drop_column('feedback','exercise_id')
    op.drop_column('feedback','lesson_title')
