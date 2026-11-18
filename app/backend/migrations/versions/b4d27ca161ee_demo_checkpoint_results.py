"""Store demo checkpoint scores.

Revision ID: b4d27ca161ee
Revises: 8f2c1e93a0bb
"""
from alembic import op
import sqlalchemy as sa

revision='b4d27ca161ee'
down_revision='8f2c1e93a0bb'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('demo_checkpoint_results',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('course',sa.String(5),nullable=False),
        sa.Column('score',sa.Integer(),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_demo_checkpoint_results_user_id','demo_checkpoint_results',['user_id'])

def downgrade():
    op.drop_index('ix_demo_checkpoint_results_user_id',table_name='demo_checkpoint_results')
    op.drop_table('demo_checkpoint_results')
