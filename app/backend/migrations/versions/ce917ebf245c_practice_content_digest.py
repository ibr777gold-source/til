"""Record the content used for demo practice scores.

Revision ID: ce917ebf245c
Revises: 22ed76da497f
"""
from alembic import op
import sqlalchemy as sa

revision='ce917ebf245c'
down_revision='22ed76da497f'
branch_labels=None
depends_on=None

def upgrade():
    # Existing scores are preserved with unknown content versions.
    op.add_column('demo_checkpoint_results',sa.Column('content_digest',sa.String(64),nullable=True))

def downgrade():
    op.drop_column('demo_checkpoint_results','content_digest')
