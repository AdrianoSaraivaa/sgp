"""add checklist v2 fields and ncr table (safe / idempotent)

Revision ID: 8eecf2a1c9ab
Revises: add_fields_gpworkorder_gpworkstage
Create Date: 2025-09-29 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8eecf2a1c9ab"
down_revision = "add_fields_gpworkorder_gpworkstage"
branch_labels = None
depends_on = None


def _has_column(insp, table_name, col_name):
    try:
        cols = [c["name"] for c in insp.get_columns(table_name)]
        return col_name in cols
    except Exception:
        return False


def _has_table(insp, table_name):
    try:
        return table_name in insp.get_table_names()
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Templates: tolerancia_inicio, permitir_pular_item
    if _has_table(insp, "gp_checklist_templates"):
        if not _has_column(insp, "gp_checklist_templates", "tolerancia_inicio"):
            op.add_column(
                "gp_checklist_templates",
                sa.Column(
                    "tolerancia_inicio",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("0.9"),
                ),
            )
        if not _has_column(insp, "gp_checklist_templates", "permitir_pular_item"):
            op.add_column(
                "gp_checklist_templates",
                sa.Column(
                    "permitir_pular_item",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )

    # 2) Items: novos campos
    if _has_table(insp, "gp_checklist_items"):
        if not _has_column(insp, "gp_checklist_items", "tempo_alvo_s"):
            op.add_column(
                "gp_checklist_items",
                sa.Column("tempo_alvo_s", sa.Integer(), nullable=True),
            )
        if not _has_column(insp, "gp_checklist_items", "min_s"):
            op.add_column(
                "gp_checklist_items", sa.Column("min_s", sa.Integer(), nullable=True)
            )
        if not _has_column(insp, "gp_checklist_items", "max_s"):
            op.add_column(
                "gp_checklist_items", sa.Column("max_s", sa.Integer(), nullable=True)
            )
        if not _has_column(insp, "gp_checklist_items", "bloqueante"):
            op.add_column(
                "gp_checklist_items",
                sa.Column(
                    "bloqueante",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if not _has_column(insp, "gp_checklist_items", "exige_nota_se_nao"):
            op.add_column(
                "gp_checklist_items",
                sa.Column(
                    "exige_nota_se_nao",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if not _has_column(insp, "gp_checklist_items", "habilitado"):
            op.add_column(
                "gp_checklist_items",
                sa.Column(
                    "habilitado",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )

    # 3) Execuções: adicionar status (mantém result para compat)
    if _has_table(insp, "gp_checklist_execucoes"):
        if not _has_column(insp, "gp_checklist_execucoes", "status"):
            op.add_column(
                "gp_checklist_execucoes",
                sa.Column("status", sa.String(length=10), nullable=True),
            )

    # 4) Exec logs: usar add_column direto (evita batch e o erro de dependência)
    if _has_table(insp, "gp_checklist_exec_items"):
        if not _has_column(insp, "gp_checklist_exec_items", "started_at"):
            op.add_column(
                "gp_checklist_exec_items",
                sa.Column("started_at", sa.DateTime(), nullable=True),
            )
        if not _has_column(insp, "gp_checklist_exec_items", "finished_at"):
            op.add_column(
                "gp_checklist_exec_items",
                sa.Column("finished_at", sa.DateTime(), nullable=True),
            )
        if not _has_column(insp, "gp_checklist_exec_items", "elapsed_s"):
            op.add_column(
                "gp_checklist_exec_items",
                sa.Column("elapsed_s", sa.Integer(), nullable=True),
            )
        if not _has_column(insp, "gp_checklist_exec_items", "resultado"):
            op.add_column(
                "gp_checklist_exec_items",
                sa.Column("resultado", sa.String(length=10), nullable=True),
            )
        if not _has_column(insp, "gp_checklist_exec_items", "nota"):
            op.add_column(
                "gp_checklist_exec_items", sa.Column("nota", sa.Text(), nullable=True)
            )
        if not _has_column(insp, "gp_checklist_exec_items", "pin_used"):
            op.add_column(
                "gp_checklist_exec_items",
                sa.Column(
                    "pin_used",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if not _has_column(insp, "gp_checklist_exec_items", "pin_reason"):
            op.add_column(
                "gp_checklist_exec_items",
                sa.Column("pin_reason", sa.Text(), nullable=True),
            )

    # 5) NCRs: nova tabela (criar se não existir)
    if not _has_table(insp, "gp_checklist_ncrs"):
        op.create_table(
            "gp_checklist_ncrs",
            sa.Column(
                "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
            ),
            sa.Column(
                "exec_id",
                sa.Integer(),
                sa.ForeignKey("gp_checklist_execucoes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("item_ordem", sa.Integer(), nullable=True),
            sa.Column("categoria", sa.String(length=80), nullable=True),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("foto_path", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Remove tabela NCRs
    if _has_table(insp, "gp_checklist_ncrs"):
        op.drop_table("gp_checklist_ncrs")

    # Exec logs
    if _has_table(insp, "gp_checklist_exec_items"):
        for col in [
            "pin_reason",
            "pin_used",
            "nota",
            "resultado",
            "elapsed_s",
            "finished_at",
            "started_at",
        ]:
            if _has_column(insp, "gp_checklist_exec_items", col):
                op.drop_column("gp_checklist_exec_items", col)

    # Execuções
    if _has_table(insp, "gp_checklist_execucoes"):
        if _has_column(insp, "gp_checklist_execucoes", "status"):
            op.drop_column("gp_checklist_execucoes", "status")

    # Items
    if _has_table(insp, "gp_checklist_items"):
        for col in [
            "habilitado",
            "exige_nota_se_nao",
            "bloqueante",
            "max_s",
            "min_s",
            "tempo_alvo_s",
        ]:
            if _has_column(insp, "gp_checklist_items", col):
                op.drop_column("gp_checklist_items", col)

    # Templates
    if _has_table(insp, "gp_checklist_templates"):
        for col in ["permitir_pular_item", "tolerancia_inicio"]:
            if _has_column(insp, "gp_checklist_templates", col):
                op.drop_column("gp_checklist_templates", col)
