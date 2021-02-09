"""metadata

Revision ID: dda6242a627d
Revises: debc98d30e52
Create Date: 2020-08-28 16:50:12.096178

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dda6242a627d'
down_revision = 'debc98d30e52'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('panel_versions', sa.Column('coverage_requirement_15', sa.Float(), nullable=True))
    op.add_column('panels', sa.Column('clinical_geneticist', sa.String(length=255), nullable=True))
    op.add_column('panels', sa.Column('comments', sa.Text(), nullable=True))
    op.add_column('panels', sa.Column('disease_description_eng', sa.String(length=255), nullable=True))
    op.add_column('panels', sa.Column('disease_description_nl', sa.String(length=255), nullable=True))
    op.add_column('panels', sa.Column('patientfolder_alissa', sa.String(length=255), nullable=True))
    op.add_column('panels', sa.Column('staff_member', sa.String(length=255), nullable=True))
    op.add_column('sample_projects', sa.Column('type', sa.String(length=255), nullable=True))
    op.add_column('samples', sa.Column('type', sa.String(length=255), nullable=False))


def downgrade():
    op.drop_column('samples', 'type')
    op.drop_column('sample_projects', 'type')
    op.drop_column('panels', 'staff_member')
    op.drop_column('panels', 'patientfolder_alissa')
    op.drop_column('panels', 'disease_description_nl')
    op.drop_column('panels', 'disease_description_eng')
    op.drop_column('panels', 'comments')
    op.drop_column('panels', 'clinical_geneticist')
    op.drop_column('panel_versions', 'coverage_requirement_15')
