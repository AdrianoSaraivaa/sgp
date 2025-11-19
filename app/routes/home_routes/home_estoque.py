from flask import Blueprint, render_template
from flask_login import login_required  # 1. Importar

estoque_bp = Blueprint("estoque_bp", __name__)


@estoque_bp.route("/estoque")
@login_required  # 2. Trancar a rota
def tela_estoque():
    return render_template("home_templates/home_estoque.html")
