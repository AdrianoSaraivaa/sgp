# app/__init__.py
"""
Application Factory do Flask para o projeto SGP (Pneumark).

Este arquivo segue o padrão recomendado de factory:
- NÃO registra blueprints fora da função create_app().
- Evita importações precoces que causam circular import.
- Torna o boot robusto (módulos opcionais não derrubam a app).
- Facilita a inclusão de novos blueprints no futuro (ver seção 'REGISTROS').

Guia rápido para adicionar um novo blueprint:
1) Crie seu módulo (ex.: app/routes/minha_area/minha_rota.py) com algo como:
       from flask import Blueprint
       minha_rota_bp = Blueprint("minha_rota_bp", __name__)
       @minha_rota_bp.route("/ping")
       def ping(): return "pong"

2) Aqui no __init__.py, dentro de create_app(), use _try_register:
       _try_register(app, "app.routes.minha_area.minha_rota", "minha_rota_bp")

3) Dica: Use 'alias=' para logs mais claros se o nome do atributo for pouco descritivo.

Atenção a duplicidade:
- Não registre o MESMO blueprint duas vezes por caminhos diferentes.
- Se um 'init_app(app)' já registra um BP internamente, NÃO repita abaixo.

Execução:
- CLI (recomendado): FLASK_APP="app:create_app" flask run
- WSGI (opcional): descomente 'app = create_app()' no final.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# ---------------------------------------------------------------------
# Extensões globais (instanciadas aqui, inicializadas na factory)
# ---------------------------------------------------------------------
db = SQLAlchemy()
migrate = Migrate()


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
    """
    Importa dinamicamente e registra um blueprint, com tratamento de erros.

    Parâmetros:
      - import_line: caminho do módulo (ex.: "app.routes.home_routes.login")
      - attr: nome do objeto Blueprint dentro do módulo (ex.: "login_bp")
      - required: se True, falha interrompe o boot (raise); se False, apenas loga warning
      - alias: nome amigável para aparecer no log (opcional)

    Uso:
      _try_register(app, "app.routes.x.y", "meu_bp")
      _try_register(app, "app.routes.x.y", "meu_bp", alias="Minha Área")
    """
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
            # Se for essencial para a aplicação, subimos a exceção
            app.logger.exception(msg)
            raise
        else:
            # Caso opcional, apenas avisamos e seguimos com o boot
            app.logger.warning(msg)


# ---------------------------------------------------------------------
# Factory principal
# ---------------------------------------------------------------------
def create_app() -> Flask:
    """
    Cria e configura a aplicação Flask:
      - Carrega configurações essenciais.
      - Inicializa extensões (db, migrate).
      - Registra blueprints de forma resiliente.
      - Disponibiliza context processors úteis.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # -----------------------------------------------------------------
    # Configurações básicas
    # -----------------------------------------------------------------
    # Segurança
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Banco de dados:
    # - Em produção, configure DATABASE_URL, ex.:
    #   postgresql+psycopg://user:pass@host:5432/dbname
    database_url = os.environ.get("DATABASE_URL", "sqlite:///pneumark.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # PIN admin de séries (mova para env em produção)
    app.config["SERIES_ADMIN_PIN"] = os.environ.get("SERIES_ADMIN_PIN", "4321")

    # Logging básico para o boot (evita handlers duplicados em alguns ambientes)
    if not app.logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # -----------------------------------------------------------------
    # Inicialização de extensões
    # -----------------------------------------------------------------
    db.init_app(app)

    # -----------------------------------------------------------------
    # REGISTROS — Blueprints
    # -----------------------------------------------------------------
    # 1) Rastreabilidade (pacote com init_app próprio)
    #    O init_app() deve registrar apenas o gp_rastreabilidade_bp — mantenha a consistência.
    try:
        from app.routes.producao_routes.rastreabilidade_nserie_routes import (
            init_app as rastreabilidade_init,
        )

        rastreabilidade_init(app)
        app.logger.info("[BOOT] Rastreabilidade registrada via init_app().")
    except Exception as e:
        app.logger.warning("[BOOT] Rastreabilidade indisponível: %s", e)

    # 1.1) Trace API (nova API de rastreabilidade consolidada)
    #      Certifique-se de que NÃO está sendo registrada também dentro do init_app acima.
    _try_register(
        app,
        "app.routes.producao_routes.rastreabilidade_nserie_routes.trace_api",
        "trace_api_bp",
        required=False,
        alias="Trace API",
    )

    # 2) Home / Módulos
    _try_register(app, "app.routes.home_routes.login", "login_bp", required=False)
    _try_register(app, "app.routes.home_routes.modulos", "modulos_bp", required=False)
    _try_register(
        app, "app.routes.home_routes.home_estoque", "estoque_bp", required=False
    )
    _try_register(
        app, "app.routes.home_routes.home_producao", "home_producao_bp", required=False
    )

    # 3) Estoque
    _try_register(
        app,
        "app.routes.estoque_routes.cadastrar_peca",
        "cadastrar_peca_bp",
        required=False,
    )
    _try_register(
        app, "app.routes.estoque_routes.listar_pecas", "listar_pecas_bp", required=False
    )
    _try_register(
        app, "app.routes.estoque_routes.editar_peca", "editar_peca_bp", required=False
    )
    _try_register(
        app,
        "app.routes.estoque_routes.consultar_peca",
        "consultar_peca_bp",
        required=False,
    )
    _try_register(
        app, "app.routes.estoque_routes.deletar_peca", "deletar_peca_bp", required=False
    )
    _try_register(
        app,
        "app.routes.estoque_routes.autocomplete_pecas",
        "autocomplete_bp",
        required=False,
    )

    # 3.1) Fornecedores (Estoque)
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.cadastrar_fornecedor",
        "cadastrar_fornecedor_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.editar_fornecedor",
        "editar_fornecedor_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.deletar_fornecedor",
        "deletar_fornecedor_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.estoque_routes.fornecedor_routes.listar_fornecedor",
        "listar_fornecedor_bp",
        required=False,
    )

    # 4) Produção — Máquinas
    _try_register(
        app,
        "app.routes.producao_routes.maquinas_routes.montar_maquinas",
        "maquinas_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.estoque_routes.editar_conjunto",
        "editar_conjunto_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.maquinas_routes.imprimir_etiqueta",
        "imprimir_etiqueta_bp",
        required=False,
    )
    # arquivo obsoleto (mantido como comentário para referência)
    # _try_register(app, "app.routes.producao_routes.maquinas_routes.montagens", "montagens_bp", required=False)
    _try_register(
        app,
        "app.routes.producao_routes.maquinas_routes.series",
        "series_bp",
        required=False,
    )

    # 5) Utilidades (centralizado em home_routes.utilidades_routes)
    _try_register(
        app, "app.routes.home_routes.utilidades_routes", "utilidades_bp", required=False
    )

    # 6) Gerenciamento de Produção (GP)
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_setup",
        "gp_setup_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.hipot_routes",
        "gp_hipot_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_builder",
        "gp_checklist_builder_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_exec",
        "gp_checklist_exec_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_checklist_api",
        "gp_checklist_api_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.setup_save",
        "gp_setup_save_bp",
        required=False,
    )

    # 7) Painel ao Vivo (GP)
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.board_page",
        "gp_painel_page_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.board_api",
        "gp_painel_api_bp",
        required=False,
    )
    # Corrigido: módulo do scan fica em gerenciamento_producao_routes
    _try_register(
        app,
        "app.routes.producao_routes.gerenciamento_producao_routes.gp_painel_scan_api",
        "gp_painel_scan_api_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.order_api",
        "gp_painel_order_api_bp",
        required=False,
    )
    _try_register(
        app,
        "app.routes.producao_routes.painel_routes.needs_api",
        "gp_needs_api_bp",
        required=False,
    )

    # 8) OMIE (Integração nova)
    _try_register(
        app,
        "app.routes.estoque_routes.OMIE_routes.omie_routes",
        "estoque_omie_bp",
        required=False,
        alias="OMIE",
    )

    # -----------------------------------------------------------------
    # Models (import após db.init_app, antes do migrate)
    # -----------------------------------------------------------------
    # Importamos os modelos SQLAlchemy mapeados para que o Alembic detecte as tabelas.
    # Se falhar (ex.: modelos gerados ainda não existem), seguimos com o boot
    # — mas as migrações podem não refletir tudo até que os modelos estejam ok.
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

    # Inicializa o Flask-Migrate
    migrate.init_app(app, db)

    # -----------------------------------------------------------------
    # Context processors / filtros
    # -----------------------------------------------------------------
    @app.context_processor
    def inject_now():
        # Uso no template: {{ now().year }} — retorna datetime.utcnow (callable)
        return {"now": datetime.utcnow}

    app.logger.info("[BOOT] Aplicação inicializada com sucesso.")
    return app


# ------------------------------------------------------------
# Opcional: expor um 'app' concreto para WSGI (ex.: gunicorn)
# Em CLI, prefira FLASK_APP="app:create_app".
# ------------------------------------------------------------
# app = create_app()
