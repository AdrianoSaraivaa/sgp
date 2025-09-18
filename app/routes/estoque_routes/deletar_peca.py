
from flask import Blueprint, redirect, url_for, flash
from app import db
from app.models_sqla import Peca

deletar_peca_bp = Blueprint('deletar_peca_bp', __name__)

@deletar_peca_bp.route('/deletar_peca/<int:peca_id>', methods=['POST'])
def deletar_peca(peca_id):
    peca = Peca.query.get_or_404(peca_id)
    
    try:
        db.session.delete(peca)
        db.session.commit()
        flash('Peça deletada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao deletar peça: {e}', 'danger')

    return redirect(url_for('listar_pecas_bp.listar_pecas'))
