from flask import Blueprint, render_template

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] gp_checklist_builder_bp
# [RESPONSABILIDADE] Registrar rotas do builder de checklist no módulo de produção
# ====================================================================
gp_checklist_builder_bp = Blueprint(
    "gp_checklist_builder_bp", __name__, url_prefix="/producao/gp/checklist"
)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] builder
# [RESPONSABILIDADE] Renderizar tela do Builder do Checklist (front-only)
# ====================================================================
@gp_checklist_builder_bp.route("/builder", methods=["GET"])
def builder():
    """
    Tela do Builder do Checklist (somente front, sem banco).
    URL: /producao/gp/checklist/builder
    """
    return render_template("gp_templates/checklist/builder.html")


# ====================================================================
# [FIM BLOCO] builder
# ====================================================================

# ====================================================================
# [FIM BLOCO] gp_checklist_builder_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: gp_checklist_builder_bp
# FUNÇÃO: builder
# ====================================================================
