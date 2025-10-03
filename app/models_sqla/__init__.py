"""SQLAlchemy models auto-generated from pneumark.db.

This package contains SQLAlchemy model definitions for the tables in the
pneumark SQLite database. These models are intended to be drop-in
replacements for the original Flask-SQLAlchemy models that existed
before the dataclass refactor. By regenerating these classes from the
existing database schema, you can restore the `.query` API that many
views and services depend on.

Usage:
    from app import db
    from app.models_sqla import Peca, Montagem, EstruturaMaquina, GPWorkOrder

The ``db`` object must be initialized by calling ``db.init_app(app)``
in your application factory (this already happens in ``app/__init__.py``).

After placing this package in your project, update your imports to
reference these classes instead of the dataclass versions. For example,
change ``from app.models import Peca`` to ``from app.models_sqla import Peca``.

Note: Relationships between tables have been kept minimal to avoid
complexity. If your application relied on SQLAlchemy relationships,
you may need to recreate them manually.
"""

from flask_sqlalchemy import SQLAlchemy  # type: ignore
from app import db  # reuse the SQLAlchemy instance from the app
from datetime import datetime

# ============================
# Estoque models
# ============================


class Peca(db.Model):
    __tablename__ = "pecas"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=True)
    descricao = db.Column(db.String(100), nullable=True)
    codigo_pneumark = db.Column(db.String(50), nullable=True)
    codigo_omie = db.Column(db.String(50), nullable=True)
    estoque_minimo = db.Column(db.Integer, nullable=True)
    ponto_pedido = db.Column(db.Integer, nullable=True)
    estoque_maximo = db.Column(db.Integer, nullable=True)
    estoque_atual = db.Column(db.Integer, nullable=True)
    margem = db.Column(db.Float, nullable=True)
    custo = db.Column(db.Float, nullable=True)

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EstruturaMaquina(db.Model):
    __tablename__ = "estruturas_maquina"

    id = db.Column(db.Integer, primary_key=True)
    codigo_maquina = db.Column(db.String(50), nullable=False)
    codigo_peca = db.Column(db.String(50), nullable=False)
    quantidade = db.Column(db.Integer, nullable=True)


class FornecedoresPorPeca(db.Model):
    __tablename__ = "fornecedores_por_peca"

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, nullable=False)
    fornecedor = db.Column(db.String(100), nullable=True)
    etapa = db.Column(db.String(100), nullable=True)
    preco = db.Column(db.Float, nullable=True)


class Fornecedor(db.Model):
    __tablename__ = "fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(100), nullable=False)
    nome_contato = db.Column(db.String(100), nullable=False)
    telefone1 = db.Column(db.String(20), nullable=True)
    telefone2 = db.Column(db.String(20), nullable=True)
    email1 = db.Column(db.String(100), nullable=True)
    email2 = db.Column(db.String(100), nullable=True)


# ============================
# Produção / Montagem models
# ============================


class Montagem(db.Model):
    __tablename__ = "montagens"

    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(32), nullable=False)
    serial = db.Column(db.String(32), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    usuario = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False)
    cancel_reason = db.Column(db.Text, nullable=True)
    cancel_at = db.Column(db.DateTime, nullable=True)
    cancel_by = db.Column(db.String(64), nullable=True)
    label_printed = db.Column(db.Boolean, nullable=False)
    label_printed_at = db.Column(db.DateTime, nullable=True)
    label_printed_by = db.Column(db.String(64), nullable=True)
    label_print_count = db.Column(db.Integer, nullable=False)
    qrcode_path = db.Column(db.String(255), nullable=True)
    label_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class LabelReprintLog(db.Model):
    __tablename__ = "label_reprint_logs"

    id = db.Column(db.Integer, primary_key=True)
    montagem_id = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    reprint_by = db.Column(db.String(64), nullable=False)
    reprint_at = db.Column(db.DateTime, nullable=False)


# ============================
# GP models
# ============================


class GPChecklistExecution(db.Model):
    __tablename__ = "gp_checklist_execucoes"

    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(50), nullable=True)
    operador = db.Column(db.String(100), nullable=True)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    result = db.Column(db.String(10), nullable=True)


class GPChecklistTemplate(db.Model):
    __tablename__ = "gp_checklist_templates"

    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class GPChecklistExecutionItem(db.Model):
    __tablename__ = "gp_checklist_exec_items"

    id = db.Column(db.Integer, primary_key=True)
    exec_id = db.Column(db.Integer, nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tempo_estimado_seg = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    elapsed_seg = db.Column(db.Integer, nullable=True)
    ncrs = db.Column(db.JSON, nullable=True)


class GPChecklistItem(db.Model):
    __tablename__ = "gp_checklist_items"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tempo_seg = db.Column(db.Integer, nullable=False)
    ncr_tags = db.Column(db.JSON, nullable=True)


class GPModel(db.Model):
    __tablename__ = "gp_model"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)


class GPBenchConfig(db.Model):
    __tablename__ = "gp_bench_config"

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, nullable=False)
    bench_id = db.Column(db.String(10), nullable=False)
    ativo = db.Column(db.Boolean, nullable=True)
    obrigatorio = db.Column(db.Boolean, nullable=True)
    tempo_min = db.Column(db.Integer, nullable=True)
    tempo_esperado = db.Column(db.Integer, nullable=True)
    tempo_max = db.Column(db.Integer, nullable=True)
    operador = db.Column(db.String(120), nullable=True)
    responsavel = db.Column(db.String(120), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)


class GPWorkStage(db.Model):
    __tablename__ = "gp_work_stage"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    bench_id = db.Column(db.String(10), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    operador = db.Column(db.String(120), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    # Campos adicionados para Onda 2:
    result = db.Column(db.String(10), nullable=True)
    rework_flag = db.Column(db.Boolean, nullable=False, server_default="0")
    workstation = db.Column(db.String(120), nullable=True)


class GPROPAlert(db.Model):
    __tablename__ = "gp_rop_alerts"

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, nullable=False)
    in_alert = db.Column(db.Boolean, nullable=False)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class GPHipotRun(db.Model):
    __tablename__ = "gp_hipot_run"

    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(64), nullable=False)
    modelo = db.Column(db.String(64), nullable=True)
    operador = db.Column(db.String(120), nullable=True)
    responsavel = db.Column(db.String(120), nullable=True)
    ordem = db.Column(db.String(8), nullable=True)
    obs = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    gb_ok = db.Column(db.Boolean, nullable=True)
    gb_r_mohm = db.Column(db.Float, nullable=True)
    gb_i_a = db.Column(db.Float, nullable=True)
    gb_t_s = db.Column(db.Float, nullable=True)
    hp_ok = db.Column(db.Boolean, nullable=True)
    hp_ileak_ma = db.Column(db.Float, nullable=True)
    hp_v_obs_v = db.Column(db.Float, nullable=True)
    hp_t_s = db.Column(db.Float, nullable=True)
    final_ok = db.Column(db.Boolean, nullable=True)


class GPWorkOrder(db.Model):
    __tablename__ = "gp_work_order"

    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(64), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    current_bench = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
    hipot_flag = db.Column(db.Boolean, nullable=False)
    hipot_status = db.Column(db.String(10), nullable=False)
    hipot_last_at = db.Column(db.DateTime, nullable=True)
    # Campo novo para Onda 2:
    finished_at = db.Column(db.DateTime, nullable=True)


class OmieRequisicao(db.Model):
    __tablename__ = "omie_requisicoes"

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, nullable=False)
    fornecedor = db.Column(db.String(100), nullable=True)
    quantidade = db.Column(db.Integer, nullable=False)
    cod_int = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pendente")
    erro_msg = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


__all__ = [
    # Estoque
    "Peca",
    "EstruturaMaquina",
    "Fornecedor",
    "FornecedoresPorPeca",
    # Produção/Montagem
    "Montagem",
    "LabelReprintLog",
    # GP
    "GPChecklistExecution",
    "GPChecklistTemplate",
    "GPChecklistExecutionItem",
    "GPChecklistItem",
    "GPModel",
    "GPBenchConfig",
    "GPWorkStage",
    "GPROPAlert",
    "GPHipotRun",
    "GPWorkOrder",
    # OMIE
    "OmieRequisicao",
]

# ------------------------------------------------------------
# Backwards compatibility aliases
# ------------------------------------------------------------
# Algumas partes do código legadas esperam encontrar ``GPWorkOrderHistory`` no
# pacote ``models_sqla``.  Como essa tabela não existe no banco de dados,
# apontamos para ``GPWorkOrder`` para evitar erros de importação.
GPWorkOrderHistory = GPWorkOrder  # type: ignore
__all__.append("GPWorkOrderHistory")
