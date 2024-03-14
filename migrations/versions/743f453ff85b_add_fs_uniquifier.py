"""Add fs_uniquifier

Revision ID: 743f453ff85b
Revises: bcd8bff69995
Create Date: 2024-03-11 23:47:09.778701

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '743f453ff85b'
down_revision = 'bcd8bff69995'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fs_uniquifier', sa.String(length=255), nullable=False))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('fs_uniquifier')
