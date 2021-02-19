"""Add core genes table

Revision ID: 68b4dcb164af
Revises: f6911f9c19ef
Create Date: 2021-02-18 12:07:43.405371

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '68b4dcb164af'
down_revision = 'f6911f9c19ef'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'panels_core_genes',
        sa.Column('panel_id', sa.Integer(), nullable=False),
        sa.Column('gene_id', sa.String(length=50, collation='utf8_bin'), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ),
        sa.ForeignKeyConstraint(['panel_id'], ['panel_versions.id'], ),
        sa.PrimaryKeyConstraint('panel_id', 'gene_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('panels_core_genes')
    # ### end Alembic commands ###
