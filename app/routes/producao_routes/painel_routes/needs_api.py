# app/routes/producao_routes/painel_routes/needs_api.py
from flask import Blueprint, jsonify
from app import db
from .rop_service import list_rop_needs

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] gp_needs_api_bp
# [RESPONSABILIDADE] Definir blueprint e prefixo das rotas de necessidades (ROP) do painel
# ====================================================================
gp_needs_api_bp = Blueprint("gp_needs_api_bp", __name__, url_prefix="/producao/gp")
# ====================================================================
# [FIM BLOCO] gp_needs_api_bp
# ====================================================================


@gp_needs_api_bp.route("/needs", methods=["GET"])
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] api_needs
# [RESPONSABILIDADE] Retornar lista de necessidades de montagem com base em ROP, com fallback seguro
# ====================================================================
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


# ====================================================================
# [FIM BLOCO] api_needs
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: gp_needs_api_bp
# FUNÇÃO: api_needs
# ====================================================================
