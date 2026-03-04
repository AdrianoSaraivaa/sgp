from flask import Blueprint, jsonify, request

# Use the SQLAlchemy models instead of dataclasses. Import from the
# auto-generated models_sqla package to ensure that ``.query`` is available.
from app.models_sqla import Peca

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] autocomplete_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas ao autocomplete de peças
# ====================================================================
autocomplete_bp = Blueprint("autocomplete_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] pecas_autocomplete
# [RESPONSABILIDADE] Retornar sugestões de peças com base em termo pesquisado
# ====================================================================
@autocomplete_bp.route("/api/pecas_autocomplete")
def pecas_autocomplete():
    termo = request.args.get("termo", "").lower()

    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_pecas_autocomplete_db
    # [RESPONSABILIDADE] Filtrar peças por descrição com limite de resultados
    # ====================================================================
    resultados = Peca.query.filter(Peca.descricao.ilike(f"%{termo}%")).limit(10).all()

    sugestoes = [
        {"descricao": p.descricao, "codigo": p.codigo_pneumark} for p in resultados
    ]
    return jsonify(sugestoes)


# ====================================================================
# [FIM BLOCO] pecas_autocomplete
# ====================================================================

# ====================================================================
# [FIM BLOCO] autocomplete_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: autocomplete_bp
# FUNÇÃO: pecas_autocomplete
# BLOCO_DB: consulta_pecas_autocomplete_db
# ====================================================================
