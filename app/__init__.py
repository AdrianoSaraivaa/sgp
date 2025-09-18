# app/__init__.py

import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# -----------------------------
# Extensões (instanciadas fora da factory)
# -----------------------------
db = SQLAlchemy()
migrate = Migrate()


def _try_register(app: Flask, import_line: str, attr: str, *, required: bool = False, alias: Optional[str] = None):
    """
    Importa dinamicamente um blueprint e registra no app.
    - import_line: caminho do módulo (ex.: "app.routes.home_routes.login")
    - attr: nome do blueprint dentro do módulo (ex.: "login_bp")
    - required: se True, levanta exceção ao falhar; caso contrário loga warning e segue
    - alias: nome a ser exibido nos logs (opcional)
    """
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


def create_app() -> Flask:
    """
    Application Factory do Flask.
    - Configura SECRET_KEY e SQLAlchemy.
    - Registra Blueprints e extensões.
    - Torna robusto o boot (não cai se algum módulo opcional faltar).
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # -----------------------------
    # Configurações
    # -----------------------------
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Banco de dados (padrão: SQLite local). Em produção, usar env DATABASE_URL
    # Ex.: export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname"
    database_url = os.environ.get("DATABASE_URL", "sqlite:///pneumark.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # PIN admin de séries (exemplo) — em prod colocar em env
    app.config["SERIES_ADMIN_PIN"] = os.environ.get("SERIES_ADMIN_PIN", "4321")

    # Logger básico (útil no boot)
    if not app.logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # -----------------------------
    # Inicializa extensões
    # -----------------------------
    db.init_app(app)

    # -----------------------------
    # Blueprints
    # -----------------------------
    # 1) Rastreabilidade (este pacote expõe init_app)
    try:
        from app.routes.producao_routes.rastreabilidade_nserie_routes import init_app as rastreabilidade_init
        rastreabilidade_init(app)  # registra gp_rastreabilidade_bp internamente
        app.logger.info("[BOOT] Rastreabilidade registrada via init_app().")
    except Exception as e:
        app.logger.warning("[BOOT] Rastreabilidade indisponível: %s", e)

    # 2) Home / Módulos
    _try_register(app, "app.routes.home_routes.login", "login_bp", required=False)
    _try_register(app, "app.routes.home_routes.modulos", "modulos_bp", required=False)
    _try_register(app, "app.routes.home_routes.home_estoque", "estoque_bp", required=False)
    _try_register(app, "app.routes.home_routes.home_producao", "home_producao_bp", required=False)

    # 3) Estoque
    _try_register(app, "app.routes.estoque_routes.cadastrar_peca", "cadastrar_peca_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.listar_pecas", "listar_pecas_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.editar_peca", "editar_peca_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.consultar_peca", "consultar_peca_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.deletar_peca", "deletar_peca_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.autocomplete_pecas", "autocomplete_bp", required=False)

    # 3.1) Fornecedores (Estoque)
    _try_register(app, "app.routes.estoque_routes.fornecedor_routes.cadastrar_fornecedor", "cadastrar_fornecedor_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.fornecedor_routes.editar_fornecedor", "editar_fornecedor_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.fornecedor_routes.deletar_fornecedor", "deletar_fornecedor_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.fornecedor_routes.listar_fornecedor", "listar_fornecedor_bp", required=False)

    # 4) Produção — Máquinas
    _try_register(app, "app.routes.producao_routes.maquinas_routes.montar_maquinas", "maquinas_bp", required=False)
    _try_register(app, "app.routes.estoque_routes.editar_conjunto", "editar_conjunto_bp", required=False)
    _try_register(app, "app.routes.producao_routes.maquinas_routes.imprimir_etiqueta", "imprimir_etiqueta_bp", required=False)
    _try_register(app, "app.routes.producao_routes.maquinas_routes.montagens", "montagens_bp", required=False)
    _try_register(app, "app.routes.producao_routes.maquinas_routes.series", "series_bp", required=False)

    # 5) Utilidades (AGORA: apenas via home_routes.utilidades_routes)
    _try_register(app, "app.routes.home_routes.utilidades_routes", "utilidades_bp", required=False)

    # 6) Gerenciamento de Produção (GP)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.gp_setup", "gp_setup_bp", required=False)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.hipot_routes", "gp_hipot_bp", required=False)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_builder", "gp_checklist_builder_bp", required=False)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_exec", "gp_checklist_exec_bp", required=False)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_api", "gp_checklist_api_bp", required=False)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.setup_save", "gp_setup_save_bp", required=False)

    # 7) Painel ao Vivo (GP)
    _try_register(app, "app.routes.producao_routes.painel_routes.board_page", "gp_painel_page_bp", required=False)
    _try_register(app, "app.routes.producao_routes.painel_routes.board_api", "gp_painel_api_bp", required=False)
    # ⬇️ Corrigido: caminho do módulo do scan (fica em gerenciamento_producao_routes)
    _try_register(app, "app.routes.producao_routes.gerenciamento_producao_routes.gp_painel_scan_api", "gp_painel_scan_api_bp", required=False)
    _try_register(app, "app.routes.producao_routes.painel_routes.order_api", "gp_painel_order_api_bp", required=False)
    _try_register(app, "app.routes.producao_routes.painel_routes.needs_api", "gp_needs_api_bp", required=False)

    # =========================
    # OMIE (NOVA INTEGRAÇÃO) — manter comentado até consolidar
    # =========================
    # _try_register(app, "app.routes.estoque_routes.OMIE_routes", "omie_bp", required=True, alias="omie_bp")

    # -----------------------------
    # Models (import após db.init_app, antes do migrate)
    # -----------------------------
    # Importar os modelos SQLAlchemy gerados automaticamente a partir do
    # banco de dados para que o Alembic detecte as tabelas. Caso os
    # modelos não existam (por exemplo, ainda não foram extraídos), a
    # aplicação continuará inicializando, porém as migrações podem não
    # refletir todas as tabelas.
    try:
        from app.models_sqla import (  # noqa: F401
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
        app.logger.info("[BOOT] Modelos SQLAlchemy importados para migrações.")
    except Exception as e:
        app.logger.warning(
            "[BOOT] Modelos SQLAlchemy indisponíveis ou incompletos: %s", e
        )

    # Agora sim: inicializa o Flask-Migrate com app e db
    migrate.init_app(app, db)

    # -----------------------------
    # Context processors / filtros
    # -----------------------------
    @app.context_processor
    def inject_now():
        # uso no template: {{ now().year }}
        return {"now": datetime.utcnow}

    app.logger.info("[BOOT] Aplicação inicializada com sucesso.")
    return app
