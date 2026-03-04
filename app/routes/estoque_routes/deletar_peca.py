from flask import Blueprint, redirect, url_for, flash
from app import db
from app.models_sqla import Peca

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] deletar_peca_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à exclusão de peça
# ====================================================================
deletar_peca_bp = Blueprint("deletar_peca_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] deletar_peca
# [RESPONSABILIDADE] Excluir peça do banco de dados pelo ID informado
# ====================================================================
@deletar_peca_bp.route("/deletar_peca/<int:peca_id>", methods=["POST"])
def deletar_peca(peca_id):
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_peca_para_exclusao_db
    # [RESPONSABILIDADE] Recuperar registro de peça para exclusão pelo identificador informado
    # ====================================================================
    peca = Peca.query.get_or_404(peca_id)

    try:
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] exclusao_peca_db
        # [RESPONSABILIDADE] Remover peça da sessão e confirmar transação
        # ====================================================================
        db.session.delete(peca)
        db.session.commit()
        flash("Peça deletada com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao deletar peça: {e}", "danger")

    return redirect(url_for("listar_pecas_bp.listar_pecas"))


# ====================================================================
# [FIM BLOCO] deletar_peca
# ====================================================================

# ====================================================================
# [FIM BLOCO] deletar_peca_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: deletar_peca_bp
# FUNÇÃO: deletar_peca
# BLOCO_DB: consulta_peca_para_exclusao_db
# BLOCO_DB: exclusao_peca_db
# ====================================================================
