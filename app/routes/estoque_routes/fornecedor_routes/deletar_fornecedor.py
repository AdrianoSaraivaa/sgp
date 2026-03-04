from flask import Blueprint, redirect, url_for, flash
from app import db
from app.models.estoque_models.fornecedor import Fornecedor

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] deletar_fornecedor_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à exclusão de fornecedor
# ====================================================================
deletar_fornecedor_bp = Blueprint("deletar_fornecedor_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] deletar_fornecedor
# [RESPONSABILIDADE] Excluir fornecedor do banco de dados pelo ID informado
# ====================================================================
@deletar_fornecedor_bp.route("/deletar_fornecedor/<int:id>", methods=["POST"])
def deletar_fornecedor(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    try:
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] exclusao_fornecedor_db
        # [RESPONSABILIDADE] Remover fornecedor da sessão e confirmar transação
        # ====================================================================
        db.session.delete(fornecedor)
        db.session.commit()
        flash("Fornecedor excluído com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao excluir fornecedor: {e}", "danger")

    return redirect(url_for("listar_fornecedor_bp.listar_fornecedor"))


# ====================================================================
# [FIM BLOCO] deletar_fornecedor
# ====================================================================

# ====================================================================
# [FIM BLOCO] deletar_fornecedor_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: deletar_fornecedor_bp
# FUNÇÃO: deletar_fornecedor
# BLOCO_DB: exclusao_fornecedor_db
# ====================================================================
