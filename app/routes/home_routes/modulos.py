from flask import Blueprint, render_template
from flask_login import login_required  # <--- Importante: Ferramenta de segurança

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] modulos_bp
# [RESPONSABILIDADE] Registrar rotas da tela principal de módulos do sistema
# ====================================================================
modulos_bp = Blueprint("modulos_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] tela_modulos
# [RESPONSABILIDADE] Renderizar tela inicial de módulos com acesso restrito a usuários autenticados
# ====================================================================
@modulos_bp.route("/modulos")
@login_required  # <--- O CADEADO: Só entra se estiver logado!
def tela_modulos():
    return render_template("home_templates/modulosIniciais.html")


# ====================================================================
# [FIM BLOCO] tela_modulos
# ====================================================================

# ====================================================================
# [FIM BLOCO] modulos_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: modulos_bp
# FUNÇÃO: tela_modulos
# ====================================================================
