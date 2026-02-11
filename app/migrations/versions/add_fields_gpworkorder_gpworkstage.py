"""add result/rework_flag/workstation to GPWorkStage, finished_at to GPWorkOrder

Revision ID: add_fields_gpworkorder_gpworkstage
Revises: 67b7637239ef
Create Date: 2025-09-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fields_gpworkorder_gpworkstage'
down_revision = '67b7637239ef'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('gp_work_stage', schema=None) as batch_op:
        batch_op.add_column(sa.Column('result', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('rework_flag', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('workstation', sa.String(length=120), nullable=True))

    with op.batch_alter_table('gp_work_order', schema=None) as batch_op:
        batch_op.add_column(sa.Column('finished_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('gp_work_stage', schema=None) as batch_op:
        batch_op.drop_column('workstation')
        batch_op.drop_column('rework_flag')
        batch_op.drop_column('result')

    with op.batch_alter_table('gp_work_order', schema=None) as batch_op:
        batch_op.drop_column('finished_at')
