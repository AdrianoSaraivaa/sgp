from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models_sqla import Fornecedor

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] editar_fornecedor_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à edição de fornecedor
# ====================================================================
editar_fornecedor_bp = Blueprint("editar_fornecedor_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] editar_fornecedor
# [RESPONSABILIDADE] Atualizar dados de fornecedor existente pelo ID informado
# ====================================================================
@editar_fornecedor_bp.route("/editar_fornecedor/<int:id>", methods=["GET", "POST"])
def editar_fornecedor(id):
    fornecedor = Fornecedor.query.get_or_404(id)

    if request.method == "POST":
        try:
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] atualizacao_fornecedor_db
            # [RESPONSABILIDADE] Atualizar campos do fornecedor e confirmar transação
            # ====================================================================
            fornecedor.nome_empresa = request.form["nome_empresa"]
            fornecedor.nome_contato = request.form["nome_contato"]
            fornecedor.telefone1 = request.form["telefone1"]
            fornecedor.telefone2 = request.form["telefone2"]
            fornecedor.email1 = request.form["email1"]
            fornecedor.email2 = request.form["email2"]

            db.session.commit()
            flash("Fornecedor atualizado com sucesso!", "success")
            return redirect(url_for("listar_fornecedor_bp.listar_fornecedor"))
        except Exception as e:
            flash(f"Erro ao atualizar fornecedor: {e}", "danger")

    return render_template(
        "estoque_templates/fornecedor_templates/editar_fornecedor.html",
        fornecedor=fornecedor,
    )


# ====================================================================
# [FIM BLOCO] editar_fornecedor
# ====================================================================

# ====================================================================
# [FIM BLOCO] editar_fornecedor_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: editar_fornecedor_bp
# FUNÇÃO: editar_fornecedor
# BLOCO_DB: atualizacao_fornecedor_db
# ====================================================================
