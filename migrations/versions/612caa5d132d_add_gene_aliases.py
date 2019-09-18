"""Add gene aliases.

Revision ID: 612caa5d132d
Revises: e812b2e381c7
Create Date: 2019-08-20 14:56:24.606136

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '612caa5d132d'
down_revision = 'e812b2e381c7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'gene_aliases',
        sa.Column('id', sa.String(length=50, collation='utf8_bin'), nullable=False),
        sa.Column('gene_id', sa.String(length=50, collation='utf8_bin'), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ),
        sa.PrimaryKeyConstraint('id', 'gene_id')
    )


def downgrade():
    op.drop_table('gene_aliases')
