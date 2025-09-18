from flask import Blueprint, render_template

gp_checklist_builder_bp = Blueprint(
    "gp_checklist_builder_bp",
    __name__,
    url_prefix="/producao/gp/checklist"
)

@gp_checklist_builder_bp.route("/builder", methods=["GET"])
def builder():
    """
    Tela do Builder do Checklist (somente front, sem banco).
    URL: /producao/gp/checklist/builder
    """
    return render_template("gp_templates/checklist/builder.html")
