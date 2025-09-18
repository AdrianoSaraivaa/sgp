from flask import Blueprint, render_template

gp_setup_bp = Blueprint(
    "gp_setup_bp",
    __name__,
    url_prefix="/producao/gp/setup"
)

@gp_setup_bp.route("", methods=["GET"])
def page_setup_home():
    # app/templates/gp_templates/setup/index.html
    return render_template("gp_templates/setup/index.html")
