"""Add custom_panel validated columns

Revision ID: debc98d30e52
Revises: 612caa5d132d
Create Date: 2019-08-29 13:07:55.978540

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'debc98d30e52'
down_revision = '612caa5d132d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('custom_panels', sa.Column('validated', sa.Boolean(), nullable=True))
    op.add_column('custom_panels', sa.Column('validated_date', sa.Date(), nullable=True))
    op.add_column('custom_panels', sa.Column('validated_user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_custom_panels_validated'), 'custom_panels', ['validated'], unique=False)
    op.create_foreign_key(None, 'custom_panels', 'user', ['validated_user_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'custom_panels', type_='foreignkey')
    op.drop_index(op.f('ix_custom_panels_validated'), table_name='custom_panels')
    op.drop_column('custom_panels', 'validated_user_id')
    op.drop_column('custom_panels', 'validated_date')
    op.drop_column('custom_panels', 'validated')
