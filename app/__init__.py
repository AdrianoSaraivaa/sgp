# Relative path: app/__init__.py
"""
Application Factory do Flask para o projeto SGP (Pneumark).
"""

import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask
from flask_login import LoginManager  # <--- Importante para o login
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# ---------------------------------------------------------------------
# Extensões globais
# ---------------------------------------------------------------------
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  # <--- Inicialização do LoginManager


# ---------------------------------------------------------------------
# Helper: registro dinâmico e seguro de blueprints
# ---------------------------------------------------------------------
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _try_register
# [RESPONSABILIDADE] Importar e registrar blueprints dinamicamente com logging e opção de obrigatoriedade
# ====================================================================
def _try_register(
    app: Flask,
    import_line: str,
    attr: str,
    *,
    required: bool = False,
    alias: Optional[str] = None,
) -> None:
    import importlib

    name = alias or attr
    try:
        mod = importlib.import_module(import_line)
        bp = getattr(mod, attr)
        app.register_blueprint(bp)
        app.logger.info("[BOOT] Blueprint registrado: %s (%s.%s)", name, import_line, attr)
    except Exception as e:
        msg = f"[BOOT] Falha ao registrar blueprint: {name} ({import_line}.{attr}) -> {e}"
        if required:
            app.logger.exception(msg)
            raise
        else:
            app.logger.warning(msg)


# ====================================================================
# [FIM BLOCO] _try_register
# ====================================================================


# ---------------------------------------------------------------------
# Factory principal
# ---------------------------------------------------------------------
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] create_app
# [RESPONSABILIDADE] Criar e configurar a aplicação Flask, extensões, autenticação, blueprints e contexto global
# ====================================================================
def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # -----------------------------------------------------------------
    # Configurações básicas
    # -----------------------------------------------------------------
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    raw_db_url = os.environ.get("DATABASE_URL")
    if raw_db_url:
        s = raw_db_url.strip()

        # 1) Corrige prefixo antigo postgres://
        if s.startswith("postgres://"):
            s = s.replace("postgres://", "postgresql://", 1)

        # 2) Se já vier com psycopg2 explícito, troca para psycopg3
        if s.startswith("postgresql+psycopg2://"):
            s = s.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)

        # 3) Se vier sem driver, força psycopg3
        if s.startswith("postgresql://"):
            s = s.replace("postgresql://", "postgresql+psycopg://", 1)

        raw_db_url = s

    database_url = raw_db_url or "sqlite:///pneumark.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SERIES_ADMIN_PIN"] = os.environ.get("SERIES_ADMIN_PIN", "4321")

    if not app.logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # -----------------------------------------------------------------
    # Inicialização de extensões
    # -----------------------------------------------------------------
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] init_extensions
    # [RESPONSABILIDADE] Inicializar extensões globais (SQLAlchemy, Migrate, LoginManager)
    # ====================================================================
    db.init_app(app)
    migrate.init_app(app, db)

    # --- CONFIGURAÇÃO DO LOGIN ---
    login_manager.init_app(app)
    login_manager.login_view = "login_bp.login"
    login_manager.login_message = "Faça login para acessar o sistema."
    # ====================================================================
    # [FIM BLOCO] init_extensions
    # ====================================================================

    # Função que carrega o usuário do banco
    # Importamos aqui dentro para evitar o erro de ciclo que você viu
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] login_user_loader_setup
    # [RESPONSABILIDADE] Importar modelo Usuario e configurar user_loader do Flask-Login
    # ====================================================================
    from app.models_sqla import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # ====================================================================
    # [FIM BLOCO] login_user_loader_setup
    # ====================================================================

    # -----------------------------------------------------------------
    # REGISTROS — Blueprints
    # -----------------------------------------------------------------

    # 1) Rastreabilidade
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_rastreabilidade
    # [RESPONSABILIDADE] Registrar rotas e API de rastreabilidade com fallback seguro
    # ====================================================================
    try:
        from app.routes.producao_routes.rastreabilidade_nserie_routes import (
            init_app as rastreabilidade_init,
        )

        rastreabilidade_init(app)
    except Exception as e:
        app.logger.warning("[BOOT] Rastreabilidade indisponível: %s", e)

    _try_register(
        app,
        "app.routes.producao_routes.rastreabilidade_nserie_routes.trace_api",
        "trace_api_bp",
        alias="Trace API",
    )
    # ====================================================================
    # [FIM BLOCO] blueprints_rastreabilidade
    # ====================================================================

    # 2) Home / Módulos
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_home_modulos
    # [RESPONSABILIDADE] Registrar blueprints principais de navegação e páginas iniciais
    # ====================================================================
    _try_register(app, "app.routes.home_routes.login", "login_bp")
    _try_register(app, "app.routes.home_routes.modulos", "modulos_bp")
    _try_register(app, "app.routes.home_routes.home_estoque", "estoque_bp")
    _try_register(app, "app.routes.home_routes.home_producao", "home_producao_bp")
    # ====================================================================
    # [FIM BLOCO] blueprints_home_modulos
    # ====================================================================

    # 3) Estoque
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_estoque
    # [RESPONSABILIDADE] Registrar blueprints do módulo de estoque e utilitários associados
    # ====================================================================
    _try_register(app, "app.routes.estoque_routes.cadastrar_peca", "cadastrar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.listar_pecas", "listar_pecas_bp")
    _try_register(app, "app.routes.estoque_routes.editar_peca", "editar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.consultar_peca", "consultar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.deletar_peca", "deletar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.autocomplete_pecas", "autocomplete_bp")
    # ====================================================================
    # [FIM BLOCO] blueprints_estoque
    # ====================================================================

    # 3.1) Fornecedores
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_fornecedores
    # [RESPONSABILIDADE] Registrar rotas CRUD de fornecedores no módulo de estoque
    # ====================================================================
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.cadastrar_fornecedor",
        "cadastrar_fornecedor_bp",
    )
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.editar_fornecedor",
        "editar_fornecedor_bp",
    )
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.deletar_fornecedor",
        "deletar_fornecedor_bp",
    )
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.listar_fornecedor",
        "listar_fornecedor_bp",
    )
    # ====================================================================
    # [FIM BLOCO] blueprints_fornecedores
    # ====================================================================

    # 4) Produção
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_producao
    # [RESPONSABILIDADE] Registrar blueprints do módulo de produção (montagem, conjuntos, etiquetas e séries)
    # ====================================================================
    _try_register(
        app, "app.routes.producao_routes.maquinas_routes.montar_maquinas", "maquinas_bp"
    )
    _try_register(app, "app.routes.estoque_routes.editar_conjunto", "editar_conjunto_bp")
    _try_register(
        app,
        "app.routes.producao_routes.maquinas_routes.imprimir_etiqueta",
        "imprimir_etiqueta_bp",
    )
    _try_register(app, "app.routes.producao_routes.maquinas_routes.series", "series_bp")
    # ====================================================================
    # [FIM BLOCO] blueprints_producao
    # ====================================================================

    # 5) Utilidades
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_utilidades
    # [RESPONSABILIDADE] Registrar blueprint de utilidades (ex.: frase motivacional)
    # ====================================================================
    _try_register(app, "app.routes.home_routes.utilidades_routes", "utilidades_bp")
    # ====================================================================
    # [FIM BLOCO] blueprints_utilidades
    # ====================================================================

    # 6) Gerenciamento de Produção (GP)
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_gp
    # [RESPONSABILIDADE] Registrar blueprints do GP (setup, hipot, checklists e APIs)
    # ====================================================================
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_setup",
        "gp_setup_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.hipot_routes",
        "gp_hipot_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_builder",
        "gp_checklist_builder_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_exec",
        "gp_checklist_exec_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_api",
        "gp_checklist_api_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.setup_save",
        "gp_setup_save_bp",
    )
    # ====================================================================
    # [FIM BLOCO] blueprints_gp
    # ====================================================================

    # 7) Painel ao Vivo
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_painel_ao_vivo
    # [RESPONSABILIDADE] Registrar blueprints do painel ao vivo (páginas e APIs)
    # ====================================================================
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.board_page",
        "gp_painel_page_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.board_api",
        "gp_painel_api_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_painel_scan_api",
        "gp_painel_scan_api_bp",
    )
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.order_api",
        "gp_painel_order_api_bp",
    )
    _try_register(app, "app.routes.producao_routes.painel_routes.needs_api", "gp_needs_api_bp")
    # ====================================================================
    # [FIM BLOCO] blueprints_painel_ao_vivo
    # ====================================================================

    # 8) OMIE
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] blueprints_omie
    # [RESPONSABILIDADE] Registrar integração OMIE no módulo de estoque
    # ====================================================================
    _try_register(
        app,
        "app.routes.estoque_routes.OMIE_routes.omie_routes",
        "estoque_omie_bp",
        alias="OMIE",
    )
    # ====================================================================
    # [FIM BLOCO] blueprints_omie
    # ====================================================================

    # -----------------------------------------------------------------
    # Models
    # -----------------------------------------------------------------
    # ====================================================================
    # [BLOCO] BLOCO_UTIL
    # [NOME] models_import
    # [RESPONSABILIDADE] Importar modelos SQLAlchemy para garantir registro/descoberta no projeto
    # ====================================================================
    try:
        from app.models_sqla import (
            Usuario,  # <--- Garantindo que Usuario é carregado
            Peca,
            EstruturaMaquina,
            Fornecedor,
            FornecedoresPorPeca,
            Montagem,
            LabelReprintLog,
            GPChecklistExecution,
            GPChecklistTemplate,
            GPChecklistExecutionItem,
            GPChecklistItem,
            GPModel,
            GPBenchConfig,
            GPWorkStage,
            GPROPAlert,
            GPHipotRun,
            GPWorkOrder,
        )

        app.logger.info("[BOOT] Modelos SQLAlchemy importados.")
    except Exception as e:
        app.logger.warning("[BOOT] Modelos indisponíveis: %s", e)
    # ====================================================================
    # [FIM BLOCO] models_import
    # ====================================================================

    # -----------------------------------------------------------------
    # Context processors
    # -----------------------------------------------------------------
    # ====================================================================
    # [BLOCO] FUNÇÃO
    # [NOME] inject_now
    # [RESPONSABILIDADE] Injetar função de data/hora (UTC) no contexto dos templates
    # ====================================================================
    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow}

    # ====================================================================
    # [FIM BLOCO] inject_now
    # ====================================================================

    app.logger.info("[BOOT] Aplicação inicializada com sucesso.")
    return app


# ====================================================================
# [FIM BLOCO] create_app
# ====================================================================


# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# FUNÇÃO: _try_register
# FUNÇÃO: create_app
# BLOCO_UTIL: init_extensions
# BLOCO_UTIL: login_user_loader_setup
# BLOCO_UTIL: blueprints_rastreabilidade
# BLOCO_UTIL: blueprints_home_modulos
# BLOCO_UTIL: blueprints_estoque
# BLOCO_UTIL: blueprints_fornecedores
# BLOCO_UTIL: blueprints_producao
# BLOCO_UTIL: blueprints_utilidades
# BLOCO_UTIL: blueprints_gp
# BLOCO_UTIL: blueprints_painel_ao_vivo
# BLOCO_UTIL: blueprints_omie
# BLOCO_UTIL: models_import
# FUNÇÃO: inject_now
# ====================================================================