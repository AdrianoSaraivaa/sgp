"""Criando tabela de usuarios

Revision ID: 24ad62e98f8c
Revises: 8eecf2a1c9ab
Create Date: 2025-11-18 13:53:29.095241

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '24ad62e98f8c'
down_revision = '8eecf2a1c9ab'
branch_labels = None
depends_on = None


def upgrade():
    # --- 1. Criar tabela de usuários (NOVA) ---
    op.create_table('usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=True),
        sa.Column('is_active_user', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # --- 2. Criar tabela OMIE (NOVA - detectada pelo sistema) ---
    op.create_table('omie_requisicoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('peca_id', sa.Integer(), nullable=False),
        sa.Column('fornecedor', sa.String(length=100), nullable=True),
        sa.Column('quantidade', sa.Integer(), nullable=False),
        sa.Column('cod_int', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('erro_msg', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Se precisarmos desfazer, apenas removemos as tabelas criadas
    op.drop_table('omie_requisicoes')
    op.drop_table('usuarios')