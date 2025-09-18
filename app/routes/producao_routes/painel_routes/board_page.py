from flask import Blueprint, render_template, request, jsonify

gp_painel_page_bp = Blueprint(
    "gp_painel_page_bp",
    __name__,
    url_prefix="/producao/gp/painel"
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
def painel():
    modelo = request.args.get("modelo", "PM2100")
    return render_template(
        "producao_templates/painel_templates/board.html",
        modelo=modelo,
        prefix_map_json=PREFIX_MAP
    )

@gp_painel_page_bp.get("/prefixes")
def prefixes():
    return jsonify(PREFIX_MAP)
