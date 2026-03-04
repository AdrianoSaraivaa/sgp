from flask import Blueprint, render_template
from app.models_sqla import Fornecedor

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] listar_fornecedor_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à listagem de fornecedores
# ====================================================================
listar_fornecedor_bp = Blueprint("listar_fornecedor_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] listar_fornecedor
# [RESPONSABILIDADE] Consultar e renderizar lista de fornecedores
# ====================================================================
@listar_fornecedor_bp.route("/listar_fornecedores")
def listar_fornecedor():
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_fornecedores_db
    # [RESPONSABILIDADE] Buscar todos os fornecedores no banco de dados
    # ====================================================================
    fornecedores = Fornecedor.query.all()
    return render_template(
        "estoque_templates/fornecedor_templates/listar_fornecedor.html",
        fornecedores=fornecedores,
    )


# ====================================================================
# [FIM BLOCO] listar_fornecedor
# ====================================================================

# ====================================================================
# [FIM BLOCO] listar_fornecedor_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: listar_fornecedor_bp
# FUNÇÃO: listar_fornecedor
# BLOCO_DB: consulta_fornecedores_db
# ====================================================================
