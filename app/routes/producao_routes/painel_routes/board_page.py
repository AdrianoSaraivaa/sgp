from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required  # <--- 1. Importamos a ferramenta de segurança

# ====================================================================
# [BLOCO] BLOCO_CONFIG
# [NOME] gp_painel_page_bp
# [RESPONSABILIDADE] Registro do Blueprint do painel de produção
# ====================================================================
gp_painel_page_bp = Blueprint(
    "gp_painel_page_bp", __name__, url_prefix="/producao/gp/painel"
)
# ====================================================================
# [FIM BLOCO] gp_painel_page_bp
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_CONFIG
# [NOME] PREFIX_MAP
# [RESPONSABILIDADE] Mapeamento de prefixos de leitores para bancadas
# ====================================================================
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
# ====================================================================
# [FIM BLOCO] PREFIX_MAP
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] painel
# [RESPONSABILIDADE] Renderiza a página principal do painel de produção
# ====================================================================
@gp_painel_page_bp.get("/")
@login_required  # <--- 2. O CADEADO: Agora essa página exige login!
def painel():
    modelo = request.args.get("modelo", "PM2100")
    return render_template(
        "producao_templates/painel_templates/board.html",
        modelo=modelo,
        prefix_map_json=PREFIX_MAP,
    )


# ====================================================================
# [FIM BLOCO] painel
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] prefixes
# [RESPONSABILIDADE] Retorna os prefixos de leitores em formato JSON
# ====================================================================
@gp_painel_page_bp.get("/prefixes")
# @login_required  <-- Opcional: Se quiser bloquear a API de prefixos também, descomente aqui.
def prefixes():
    return jsonify(PREFIX_MAP)


# ====================================================================
# [FIM BLOCO] prefixes
# ====================================================================


# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_CONFIG: gp_painel_page_bp
# BLOCO_CONFIG: PREFIX_MAP
# FUNÇÃO: painel
# FUNÇÃO: prefixes
# ====================================================================
