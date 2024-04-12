"""Add fs_uniquifier

Revision ID: 743f453ff85b
Revises: bcd8bff69995
Create Date: 2024-03-11 23:47:09.778701

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '743f453ff85b'
down_revision = 'bcd8bff69995'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fs_uniquifier', sa.String(length=255), nullable=False))

    connection = op.get_bind()
    for user in connection.execute(sa.text('SELECT id FROM user')):
        fs_uniquifier = uuid.uuid4().hex
        connection.execute(sa.text(f"UPDATE user SET fs_uniquifier = '{fs_uniquifier}' WHERE id = {user[0]}"))

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_unique_constraint(None, ['fs_uniquifier'])


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('fs_uniquifier', type_='unique')
        batch_op.drop_column('fs_uniquifier')
