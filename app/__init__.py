# app/__init__.py
"""
Application Factory do Flask para o projeto SGP (Pneumark).
"""

import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager  # <--- Importante para o login

# ---------------------------------------------------------------------
# Extensões globais
# ---------------------------------------------------------------------
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()  # <--- Inicialização do LoginManager


# ---------------------------------------------------------------------
# Helper: registro dinâmico e seguro de blueprints
# ---------------------------------------------------------------------
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
        app.logger.info(
            "[BOOT] Blueprint registrado: %s (%s.%s)", name, import_line, attr
        )
    except Exception as e:
        msg = (
            f"[BOOT] Falha ao registrar blueprint: {name} ({import_line}.{attr}) -> {e}"
        )
        if required:
            app.logger.exception(msg)
            raise
        else:
            app.logger.warning(msg)


# ---------------------------------------------------------------------
# Factory principal
# ---------------------------------------------------------------------
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

    database_url = os.environ.get("DATABASE_URL", "sqlite:///pneumark.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SERIES_ADMIN_PIN"] = os.environ.get("SERIES_ADMIN_PIN", "4321")

    if not app.logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # -----------------------------------------------------------------
    # Inicialização de extensões
    # -----------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)

    # --- CONFIGURAÇÃO DO LOGIN ---
    login_manager.init_app(app)
    login_manager.login_view = "login_bp.login"
    login_manager.login_message = "Faça login para acessar o sistema."

    # Função que carrega o usuário do banco
    # Importamos aqui dentro para evitar o erro de ciclo que você viu
    from app.models_sqla import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # -----------------------------------------------------------------
    # REGISTROS — Blueprints
    # -----------------------------------------------------------------

    # 1) Rastreabilidade
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

    # 2) Home / Módulos
    _try_register(app, "app.routes.home_routes.login", "login_bp")
    _try_register(app, "app.routes.home_routes.modulos", "modulos_bp")
    _try_register(app, "app.routes.home_routes.home_estoque", "estoque_bp")
    _try_register(app, "app.routes.home_routes.home_producao", "home_producao_bp")

    # 3) Estoque
    _try_register(app, "app.routes.estoque_routes.cadastrar_peca", "cadastrar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.listar_pecas", "listar_pecas_bp")
    _try_register(app, "app.routes.estoque_routes.editar_peca", "editar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.consultar_peca", "consultar_peca_bp")
    _try_register(app, "app.routes.estoque_routes.deletar_peca", "deletar_peca_bp")
    _try_register(
        app, "app.routes.estoque_routes.autocomplete_pecas", "autocomplete_bp"
    )

    # 3.1) Fornecedores
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

    # 4) Produção
    _try_register(
        app, "app.routes.producao_routes.maquinas_routes.montar_maquinas", "maquinas_bp"
    )
    _try_register(
        app, "app.routes.estoque_routes.editar_conjunto", "editar_conjunto_bp"
    )
    _try_register(
        app,
        "app.routes.producao_routes.maquinas_routes.imprimir_etiqueta",
        "imprimir_etiqueta_bp",
    )
    _try_register(app, "app.routes.producao_routes.maquinas_routes.series", "series_bp")

    # 5) Utilidades
    _try_register(app, "app.routes.home_routes.utilidades_routes", "utilidades_bp")

    # 6) Gerenciamento de Produção (GP)
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

    # 7) Painel ao Vivo
    _try_register(
        app, "app.routes.producao_routes.painel_routes.board_page", "gp_painel_page_bp"
    )
    _try_register(
        app, "app.routes.producao_routes.painel_routes.board_api", "gp_painel_api_bp"
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
    _try_register(
        app, "app.routes.producao_routes.painel_routes.needs_api", "gp_needs_api_bp"
    )

    # 8) OMIE
    _try_register(
        app,
        "app.routes.estoque_routes.OMIE_routes.omie_routes",
        "estoque_omie_bp",
        alias="OMIE",
    )

    # -----------------------------------------------------------------
    # Models
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # Context processors
    # -----------------------------------------------------------------
    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow}

    app.logger.info("[BOOT] Aplicação inicializada com sucesso.")
    return app
