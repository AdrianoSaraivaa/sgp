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


def _has_table(insp, table_name):
    try:
        return table_name in insp.get_table_names()
    except Exception:
        return False


def _has_column(insp, table_name, col_name):
    try:
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, 'gp_work_stage'):
        with op.batch_alter_table('gp_work_stage', schema=None) as batch_op:
            if not _has_column(insp, 'gp_work_stage', 'result'):
                batch_op.add_column(sa.Column('result', sa.String(length=10), nullable=True))
            if not _has_column(insp, 'gp_work_stage', 'rework_flag'):
                batch_op.add_column(
                    sa.Column('rework_flag', sa.Boolean(), nullable=False, server_default=sa.text('0'))
                )
            if not _has_column(insp, 'gp_work_stage', 'workstation'):
                batch_op.add_column(sa.Column('workstation', sa.String(length=120), nullable=True))

    if _has_table(insp, 'gp_work_order'):
        with op.batch_alter_table('gp_work_order', schema=None) as batch_op:
            if not _has_column(insp, 'gp_work_order', 'finished_at'):
                batch_op.add_column(sa.Column('finished_at', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, 'gp_work_stage'):
        with op.batch_alter_table('gp_work_stage', schema=None) as batch_op:
            if _has_column(insp, 'gp_work_stage', 'workstation'):
                batch_op.drop_column('workstation')
            if _has_column(insp, 'gp_work_stage', 'rework_flag'):
                batch_op.drop_column('rework_flag')
            if _has_column(insp, 'gp_work_stage', 'result'):
                batch_op.drop_column('result')

    if _has_table(insp, 'gp_work_order'):
        with op.batch_alter_table('gp_work_order', schema=None) as batch_op:
            if _has_column(insp, 'gp_work_order', 'finished_at'):
                batch_op.drop_column('finished_at')