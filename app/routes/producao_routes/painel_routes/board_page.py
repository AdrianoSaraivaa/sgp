from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required  # <--- 1. Importamos a ferramenta de segurança

gp_painel_page_bp = Blueprint(
    "gp_painel_page_bp", __name__, url_prefix="/producao/gp/painel"
)

# Mapa de prefixos dos leitores → bancadas
PREFIX_MAP = {
    "SEP": "sep",
    "B1": "b1",
    "B2": "b2",
    "B3": "b3",
    "B4": "b4",
    "B5": "b5",
    "B6": "b6",
    "B7": "b7",
    "B8": "b8",
}


@gp_painel_page_bp.get("/")
@login_required  # <--- 2. O CADEADO: Agora essa página exige login!
def painel():
    modelo = request.args.get("modelo", "PM2100")
    return render_template(
        "producao_templates/painel_templates/board.html",
        modelo=modelo,
        prefix_map_json=PREFIX_MAP,
    )


@gp_painel_page_bp.get("/prefixes")
# @login_required  <-- Opcional: Se quiser bloquear a API de prefixos também, descomente aqui.
def prefixes():
    return jsonify(PREFIX_MAP)
