from flask import Blueprint, redirect, url_for, flash
from app import db
from app.models.estoque_models.fornecedor import Fornecedor

deletar_fornecedor_bp = Blueprint('deletar_fornecedor_bp', __name__)

@deletar_fornecedor_bp.route('/deletar_fornecedor/<int:id>', methods=['POST'])
def deletar_fornecedor(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    try:
        db.session.delete(fornecedor)
        db.session.commit()
        flash('Fornecedor excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir fornecedor: {e}', 'danger')

    return redirect(url_for('listar_fornecedor_bp.listar_fornecedor'))
