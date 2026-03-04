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

# --- IMPORTS PARA LOGIN ---
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] seção_autenticacao_imports
# [RESPONSABILIDADE] Importar mixins e utilitários de segurança para autenticação de usuários
# ====================================================================
# ============================
# Autenticação / Usuários
# ============================
# ====================================================================
# [FIM BLOCO] seção_autenticacao_imports
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] Usuario
# [RESPONSABILIDADE] Representar usuários do sistema, com autenticação e controle de acesso
# ====================================================================
class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    # Campos adicionados para melhoria do sistema
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128))

    # Controles de acesso
    is_active_user = db.Column(db.Boolean, default=True)  # Se False, usuário não loga
    is_admin = db.Column(db.Boolean, default=False)  # Se True, acessa configurações

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ====================================================================
# [FIM BLOCO] Usuario
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] seção_estoque_models
# [RESPONSABILIDADE] Definir modelos relacionados a estoque e cadastro de peças/fornecedores
# ====================================================================
# ============================
# Estoque models
# ============================
# ====================================================================
# [FIM BLOCO] seção_estoque_models
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] Peca
# [RESPONSABILIDADE] Representar itens de estoque (peças e conjuntos) e expor serialização básica
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] Peca
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] EstruturaMaquina
# [RESPONSABILIDADE] Representar estrutura (BOM) de máquina com peças e quantidades por conjunto/modelo
# ====================================================================
class EstruturaMaquina(db.Model):
    __tablename__ = "estruturas_maquina"

    id = db.Column(db.Integer, primary_key=True)
    codigo_maquina = db.Column(db.String(50), nullable=False)
    codigo_peca = db.Column(db.String(50), nullable=False)
    quantidade = db.Column(db.Integer, nullable=True)


# ====================================================================
# [FIM BLOCO] EstruturaMaquina
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] FornecedoresPorPeca
# [RESPONSABILIDADE] Representar relacionamento entre peça e fornecedor (etapa e preço)
# ====================================================================
class FornecedoresPorPeca(db.Model):
    __tablename__ = "fornecedores_por_peca"

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, nullable=False)
    fornecedor = db.Column(db.String(100), nullable=True)
    etapa = db.Column(db.String(100), nullable=True)
    preco = db.Column(db.Float, nullable=True)


# ====================================================================
# [FIM BLOCO] FornecedoresPorPeca
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] Fornecedor
# [RESPONSABILIDADE] Representar cadastro de fornecedores e seus contatos
# ====================================================================
class Fornecedor(db.Model):
    __tablename__ = "fornecedores"

    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(100), nullable=False)
    nome_contato = db.Column(db.String(100), nullable=False)
    telefone1 = db.Column(db.String(20), nullable=True)
    telefone2 = db.Column(db.String(20), nullable=True)
    email1 = db.Column(db.String(100), nullable=True)
    email2 = db.Column(db.String(100), nullable=True)


# ====================================================================
# [FIM BLOCO] Fornecedor
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] seção_producao_montagem_models
# [RESPONSABILIDADE] Definir modelos de produção/montagem e logs associados
# ====================================================================
# ============================
# Produção / Montagem models
# ============================
# ====================================================================
# [FIM BLOCO] seção_producao_montagem_models
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] Montagem
# [RESPONSABILIDADE] Representar registros de montagem de máquinas, incluindo status e trilhas de impressão
# ====================================================================
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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ====================================================================
# [FIM BLOCO] Montagem
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] LabelReprintLog
# [RESPONSABILIDADE] Registrar reimpressões de etiquetas associadas a montagens e seus motivos
# ====================================================================
class LabelReprintLog(db.Model):
    __tablename__ = "label_reprint_logs"

    id = db.Column(db.Integer, primary_key=True)
    montagem_id = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    reprint_by = db.Column(db.String(64), nullable=False)
    reprint_at = db.Column(db.DateTime, nullable=False)


# ====================================================================
# [FIM BLOCO] LabelReprintLog
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] seção_gp_models
# [RESPONSABILIDADE] Definir modelos do Gerenciamento de Produção (GP) para templates, execuções e fluxo
# ====================================================================
# ============================
# GP models
# ============================
# ====================================================================
# [FIM BLOCO] seção_gp_models
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPChecklistExecution
# [RESPONSABILIDADE] Armazenar execução de checklist por serial, com início/fim e resultado consolidado
# ====================================================================
class GPChecklistExecution(db.Model):
    __tablename__ = "gp_checklist_execucoes"

    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(50), nullable=True)
    operador = db.Column(db.String(100), nullable=True)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    result = db.Column(db.String(10), nullable=True)


# ====================================================================
# [FIM BLOCO] GPChecklistExecution
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPChecklistTemplate
# [RESPONSABILIDADE] Representar template de checklist por modelo, com controle de criação/atualização
# ====================================================================
class GPChecklistTemplate(db.Model):
    __tablename__ = "gp_checklist_templates"

    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


# ====================================================================
# [FIM BLOCO] GPChecklistTemplate
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPChecklistExecutionItem
# [RESPONSABILIDADE] Armazenar itens executados do checklist com tempos, status e registros de NCR
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] GPChecklistExecutionItem
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPChecklistItem
# [RESPONSABILIDADE] Representar itens de checklist dentro de um template, com parâmetros e flags de execução
# ====================================================================
class GPChecklistItem(db.Model):
    __tablename__ = "gp_checklist_items"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tempo_seg = db.Column(db.Integer, nullable=False)
    ncr_tags = db.Column(db.JSON, nullable=True)
    tempo_alvo_s = db.Column(db.Integer, nullable=True)
    min_s = db.Column(db.Integer, nullable=True)
    max_s = db.Column(db.Integer, nullable=True)
    bloqueante = db.Column(db.Boolean, nullable=True)
    exige_nota_se_nao = db.Column(db.Boolean, nullable=True)
    habilitado = db.Column(db.Boolean, nullable=True)


# ====================================================================
# [FIM BLOCO] GPChecklistItem
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPModel
# [RESPONSABILIDADE] Representar modelos cadastrados no GP para roteiros e configurações por bancada
# ====================================================================
class GPModel(db.Model):
    __tablename__ = "gp_model"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)


# ====================================================================
# [FIM BLOCO] GPModel
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPBenchConfig
# [RESPONSABILIDADE] Configurar roteiros e parâmetros de bancadas por modelo (ativo/obrigatório/tempos)
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] GPBenchConfig
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPWorkStage
# [RESPONSABILIDADE] Registrar etapas de work order por bancada, tempos, operador e flags de retrabalho
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] GPWorkStage
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPROPAlert
# [RESPONSABILIDADE] Controlar alertas de ponto de pedido (ROP) por peça, com carimbo de envio e atualização
# ====================================================================
class GPROPAlert(db.Model):
    __tablename__ = "gp_rop_alerts"

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, nullable=False)
    in_alert = db.Column(db.Boolean, nullable=False)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ====================================================================
# [FIM BLOCO] GPROPAlert
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPHipotRun
# [RESPONSABILIDADE] Registrar execuções de HiPot (GB/HP) e consolidar resultado final de aprovação
# ====================================================================
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
    # Resultado final (True = aprovado, False = reprovado).  Esta coluna
    # existe na base de dados mas não era declarada no modelo gerado
    # automaticamente.  A inclusão explícita aqui garante que o
    # atributo ``final_ok`` esteja disponível, e que ele seja
    # persistido corretamente.
    final_ok = db.Column(db.Boolean, nullable=True)

    def finalize(self) -> bool:
        """Define o resultado final com base nos testes GB e HP.

        Quando ambos os testes de continuação de aterramento (GB) e
        tensão suportável (HP) retornarem ``True``, o resultado final
        será marcado como aprovado (``True``).  Caso qualquer um
        seja ``False`` ou nulo, o resultado final será reprovado
        (``False``).  O valor calculado é atribuído ao atributo
        ``final_ok`` e também retornado para conveniência.

        Returns:
            bool: ``True`` se ambos os testes foram aprovados,
            ``False`` caso contrário.
        """
        # Coerce valores para booleanos para evitar problemas com
        # strings ou ``None``.  Por padrão, considera ``None`` como
        # reprovação.
        gb_ok = bool(getattr(self, "gb_ok", False))
        hp_ok = bool(getattr(self, "hp_ok", False))
        self.final_ok = gb_ok and hp_ok
        return self.final_ok


# ====================================================================
# [FIM BLOCO] GPHipotRun
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPWorkOrder
# [RESPONSABILIDADE] Representar ordem de produção (serial/modelo) e controlar progresso por bancada e HiPot
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] GPWorkOrder
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] OmieRequisicao
# [RESPONSABILIDADE] Persistir requisições de compra OMIE (status, fornecedor, erros e timestamps)
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] OmieRequisicao
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] exports_publicos
# [RESPONSABILIDADE] Definir lista pública __all__ e aliases para compatibilidade com código legado
# ====================================================================
__all__ = [
    "Usuario",
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
# ====================================================================
# [FIM BLOCO] exports_publicos
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: seção_autenticacao_imports
# CLASSE: Usuario
# BLOCO_UTIL: seção_estoque_models
# CLASSE: Peca
# CLASSE: EstruturaMaquina
# CLASSE: FornecedoresPorPeca
# CLASSE: Fornecedor
# BLOCO_UTIL: seção_producao_montagem_models
# CLASSE: Montagem
# CLASSE: LabelReprintLog
# BLOCO_UTIL: seção_gp_models
# CLASSE: GPChecklistExecution
# CLASSE: GPChecklistTemplate
# CLASSE: GPChecklistExecutionItem
# CLASSE: GPChecklistItem
# CLASSE: GPModel
# CLASSE: GPBenchConfig
# CLASSE: GPWorkStage
# CLASSE: GPROPAlert
# CLASSE: GPHipotRun
# CLASSE: GPWorkOrder
# CLASSE: OmieRequisicao
# BLOCO_UTIL: exports_publicos
# ====================================================================
