"""Add columns created_date and release_date to panel_versions table

Revision ID: bcd8bff69995
Revises: 68b4dcb164af
Create Date: 2023-01-05 15:43:10.411815

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bcd8bff69995'
down_revision = '68b4dcb164af'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('panel_versions', sa.Column('created_date', sa.Date(), nullable=True))
    op.add_column('panel_versions', sa.Column('release_date', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('panel_versions', 'release_date')
    op.drop_column('panel_versions', 'created_date')
