# app/routes/producao_routes/painel_routes/needs_api.py
from flask import Blueprint, jsonify
from app import db
from .rop_service import list_rop_needs

gp_needs_api_bp = Blueprint(
    "gp_needs_api_bp",
    __name__,
    url_prefix="/producao/gp"
)

@gp_needs_api_bp.route("/needs", methods=["GET"])
def api_needs():
    """
    Retorna necessidades de montagem quando CONJUNTOS (máquinas) estão em ROP.
    Se o módulo Peca/ROP não estiver pronto, retorna lista vazia (não quebra o painel).
    """
    try:
        needs = list_rop_needs(db.session)
        return jsonify(needs), 200
    except Exception as e:
        from flask import current_app
        current_app.logger.exception(f"[NEEDS_API] ROP desativado temporariamente: {e}")
        return jsonify([]), 200
