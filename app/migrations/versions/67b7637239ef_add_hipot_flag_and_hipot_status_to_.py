"""add hipot_flag and hipot_status to GPWorkOrder

Revision ID: 67b7637239ef
Revises: 40139d04be4b
Create Date: 2025-09-11 18:57:55.370079

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67b7637239ef'
down_revision = '40139d04be4b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('gp_work_order', schema=None) as batch_op:
        # Corrigido para SQLite: precisa de server_default
        batch_op.add_column(
            sa.Column('hipot_flag', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )
        batch_op.add_column(
            sa.Column('hipot_status', sa.String(length=10), nullable=False, server_default='')
        )
        batch_op.add_column(
            sa.Column('hipot_last_at', sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('gp_work_order', schema=None) as batch_op:
        batch_op.drop_column('hipot_last_at')
        batch_op.drop_column('hipot_status')
        batch_op.drop_column('hipot_flag')
