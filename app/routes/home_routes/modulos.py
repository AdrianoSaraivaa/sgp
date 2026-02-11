from flask import Blueprint, render_template
from flask_login import login_required  # <--- Importante: Ferramenta de segurança

modulos_bp = Blueprint("modulos_bp", __name__)


@modulos_bp.route("/modulos")
@login_required  # <--- O CADEADO: Só entra se estiver logado!
def tela_modulos():
    return render_template("home_templates/modulosIniciais.html")
