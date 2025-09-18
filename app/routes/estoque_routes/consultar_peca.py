
from flask import Blueprint, render_template
from app.models_sqla import Peca

consultar_peca_bp = Blueprint('consultar_peca_bp', __name__)

@consultar_peca_bp.route('/consultar_peca/<int:peca_id>')
def consultar_peca(peca_id):
    peca = Peca.query.get_or_404(peca_id)
    return render_template('estoque_templates/consultar_peca.html', peca=peca)
