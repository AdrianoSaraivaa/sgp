"""Adicionando email e admin ao usuario

Revision ID: afbad526ba33
Revises: 24ad62e98f8c
Create Date: 2025-11-18 14:13:56.698301

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'afbad526ba33'
down_revision = '24ad62e98f8c'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona as novas colunas na tabela usuarios de forma segura
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True))
        batch_op.create_unique_constraint('uq_usuarios_email', ['email'])


def downgrade():
    # Remove as colunas caso precise desfazer no futuro
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_constraint('uq_usuarios_email', type_='unique')
        batch_op.drop_column('is_admin')
        batch_op.drop_column('email')