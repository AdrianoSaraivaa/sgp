from flask import Blueprint, render_template

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] gp_checklist_exec_bp
# [RESPONSABILIDADE] Criação e configuração do Blueprint do checklist GP
# ====================================================================
gp_checklist_exec_bp = Blueprint(
    "gp_checklist_exec_bp", __name__, url_prefix="/producao/gp/checklist"
)

# ====================================================================
# [FIM BLOCO] gp_checklist_exec_bp
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] exec_view
# [RESPONSABILIDADE] Renderizar a tela de execução do checklist GP
# ====================================================================
@gp_checklist_exec_bp.route("/exec", methods=["GET"])
def exec_view():
    """
    Tela de execução (tablet) da Bancada 8
    URL: /producao/gp/checklist/exec
    """
    return render_template("gp_templates/checklist/exec.html")


# ====================================================================
# [FIM BLOCO] exec_view
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: gp_checklist_exec_bp
# FUNÇÃO: exec_view
# ====================================================================
