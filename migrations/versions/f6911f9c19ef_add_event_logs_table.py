"""Add event_logs table

Revision ID: f6911f9c19ef
Revises: dda6242a627d
Create Date: 2021-01-07 17:02:28.427704

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6911f9c19ef'
down_revision = 'dda6242a627d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'event_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('table', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('modified_on', sa.DateTime(), nullable=True),
        sa.Column('data', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('event_logs')
