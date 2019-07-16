"""Add research number to custom panels.

Revision ID: e812b2e381c7
Revises:
Create Date: 2019-07-16 12:12:06.405766

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e812b2e381c7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('custom_panels', sa.Column('research_number', sa.String(length=255), server_default='', nullable=True))


def downgrade():
    op.create_index('ix_exons_chr', 'exons', ['chr'], unique=False)
