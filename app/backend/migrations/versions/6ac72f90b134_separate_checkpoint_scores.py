"""Separate greeting checkpoints from module practice.

Revision ID: 6ac72f90b134
Revises: 41f9a380bc27
"""
from alembic import op
import sqlalchemy as sa

revision = '6ac72f90b134'
down_revision = '41f9a380bc27'
branch_labels = None
depends_on = None


def upgrade():
    # Old category 3 contains both types and cannot be reliably disambiguated.
    # Retain those rows in a quarantined category rather than mislabel scores.
    op.execute('UPDATE demo_checkpoint_results SET module_number = -2 WHERE module_number = 3')
    with op.batch_alter_table('demo_checkpoint_results') as batch:
        batch.alter_column('module_number', existing_type=sa.Integer(), server_default='-1', existing_nullable=False)


def downgrade():
    op.execute('UPDATE demo_checkpoint_results SET module_number = 3 WHERE module_number IN (-2, -1)')
    with op.batch_alter_table('demo_checkpoint_results') as batch:
        batch.alter_column('module_number', existing_type=sa.Integer(), server_default='3', existing_nullable=False)
