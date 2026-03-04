from flask import Blueprint, render_template
from flask_login import login_required  # 1. Importar

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] estoque_bp
# [RESPONSABILIDADE] Registrar rotas principais do módulo de estoque
# ====================================================================
estoque_bp = Blueprint("estoque_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] tela_estoque
# [RESPONSABILIDADE] Renderizar tela principal do estoque com autenticação obrigatória
# ====================================================================
@estoque_bp.route("/estoque")
@login_required  # 2. Trancar a rota
def tela_estoque():
    return render_template("home_templates/home_estoque.html")


# ====================================================================
# [FIM BLOCO] tela_estoque
# ====================================================================

# ====================================================================
# [FIM BLOCO] estoque_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: estoque_bp
# FUNÇÃO: tela_estoque
# ====================================================================
