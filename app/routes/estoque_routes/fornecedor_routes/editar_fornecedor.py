
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models_sqla import Fornecedor

editar_fornecedor_bp = Blueprint('editar_fornecedor_bp', __name__)

@editar_fornecedor_bp.route('/editar_fornecedor/<int:id>', methods=['GET', 'POST'])
def editar_fornecedor(id):
    fornecedor = Fornecedor.query.get_or_404(id)

    if request.method == 'POST':
        try:
            fornecedor.nome_empresa = request.form['nome_empresa']
            fornecedor.nome_contato = request.form['nome_contato']
            fornecedor.telefone1 = request.form['telefone1']
            fornecedor.telefone2 = request.form['telefone2']
            fornecedor.email1 = request.form['email1']
            fornecedor.email2 = request.form['email2']

            db.session.commit()
            flash('Fornecedor atualizado com sucesso!', 'success')
            return redirect(url_for('listar_fornecedor_bp.listar_fornecedor'))
        except Exception as e:
            flash(f'Erro ao atualizar fornecedor: {e}', 'danger')

    return render_template('estoque_templates/fornecedor_templates/editar_fornecedor.html', fornecedor=fornecedor)
