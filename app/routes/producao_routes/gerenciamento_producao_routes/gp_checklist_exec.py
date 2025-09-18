from flask import Blueprint, render_template

gp_checklist_exec_bp = Blueprint(
    "gp_checklist_exec_bp",
    __name__,
    url_prefix="/producao/gp/checklist"
)

@gp_checklist_exec_bp.route("/exec", methods=["GET"])
def exec_view():
    """
    Tela de execução (tablet) da Bancada 8
    URL: /producao/gp/checklist/exec
    """
    return render_template("gp_templates/checklist/exec.html")
