# app/routes/estoque_routes/OMIE_routes/omie_routes.py
from __future__ import annotations

import logging
from flask import Blueprint, render_template, jsonify, Response
from app.utils import omie_utils

# Logger simples para este módulo
logger = logging.getLogger(__name__)

# Blueprint do OMIE no módulo de estoque
estoque_omie_bp = Blueprint(
    "estoque_omie_bp",
    __name__,
    url_prefix="/estoque/omie",
)

@estoque_omie_bp.route("/", methods=["GET"])
def home_omie():
    """
    Página inicial da área de integração OMIE no módulo de estoque.
    Renderiza: app/templates/estoque_templates/OMIE_templates/home_omie.html
    """
    logger.info("[OMIE] Renderizando home_omie")
    return render_template("estoque_templates/OMIE_templates/home_omie.html")

@estoque_omie_bp.route("/reqs", methods=["GET"])
def listar_requisicoes():
    """API para listar últimas requisições OMIE."""
    try:
        reqs = omie_utils.get_requisicoes_recentes(20)
        return jsonify(reqs)
    except Exception as e:
        logger.error(f"[OMIE] Erro ao listar requisições: {e}")
        return jsonify({"error": str(e)}), 500

@estoque_omie_bp.route("/export/produtos", methods=["GET"])
def export_produtos():
    """Exporta catálogo de produtos para Excel."""
    try:
        excel_bytes = omie_utils.exportar_produtos_excel()
        return Response(
            excel_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=produtos.xlsx"}
        )
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar produtos: {e}")
        return jsonify({"error": str(e)}), 500

@estoque_omie_bp.route("/export/fornecedores", methods=["GET"])
def export_fornecedores():
    """Exporta catálogo de fornecedores para Excel."""
    try:
        excel_bytes = omie_utils.exportar_fornecedores_excel()
        return Response(
            excel_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=fornecedores.xlsx"}
        )
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar fornecedores: {e}")
        return jsonify({"error": str(e)}), 500

@estoque_omie_bp.route("/export/produtos_fornecedores", methods=["GET"])
def export_produtos_fornecedores():
    """Exporta relacionamento produtos x fornecedores para Excel."""
    try:
        excel_bytes = omie_utils.exportar_produtos_fornecedores_excel()
        return Response(
            excel_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=produtos_fornecedores.xlsx"}
        )
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar produtos x fornecedores: {e}")
        return jsonify({"error": str(e)}), 500

@estoque_omie_bp.route("/export/snapshot_pp", methods=["GET"])
def export_snapshot_ponto_pedido():
    """Exporta snapshot do ponto de pedido para Excel."""
    try:
        excel_bytes = omie_utils.exportar_snapshot_ponto_pedido_excel()
        return Response(
            excel_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=snapshot_ponto_pedido.xlsx"}
        )
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar snapshot ponto de pedido: {e}")
        return jsonify({"error": str(e)}), 500
