from flask import Blueprint, render_template

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] gp_setup_bp
# [RESPONSABILIDADE] Criação e configuração do Blueprint de setup do módulo GP
# ====================================================================
gp_setup_bp = Blueprint("gp_setup_bp", __name__, url_prefix="/producao/gp/setup")

# ====================================================================
# [FIM BLOCO] gp_setup_bp
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] page_setup_home
# [RESPONSABILIDADE] Renderizar a página inicial do setup do módulo GP
# ====================================================================
@gp_setup_bp.route("", methods=["GET"])
def page_setup_home():
    # app/templates/gp_templates/setup/index.html
    return render_template("gp_templates/setup/index.html")


# ====================================================================
# [FIM BLOCO] page_setup_home
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: gp_setup_bp
# FUNÇÃO: page_setup_home
# ====================================================================
