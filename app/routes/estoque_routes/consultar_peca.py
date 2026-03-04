from flask import Blueprint, render_template
from app.models_sqla import Peca

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] consultar_peca_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à consulta de peça
# ====================================================================
consultar_peca_bp = Blueprint("consultar_peca_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] consultar_peca
# [RESPONSABILIDADE] Buscar peça pelo ID e renderizar página de consulta
# ====================================================================
@consultar_peca_bp.route("/consultar_peca/<int:peca_id>")
def consultar_peca(peca_id):
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_peca_por_id_db
    # [RESPONSABILIDADE] Recuperar registro de peça pelo identificador informado
    # ====================================================================
    peca = Peca.query.get_or_404(peca_id)
    return render_template("estoque_templates/consultar_peca.html", peca=peca)


# ====================================================================
# [FIM BLOCO] consultar_peca
# ====================================================================

# ====================================================================
# [FIM BLOCO] consultar_peca_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: consultar_peca_bp
# FUNÇÃO: consultar_peca
# BLOCO_DB: consulta_peca_por_id_db
# ====================================================================
