
from flask import Blueprint, render_template
from app.models_sqla import Fornecedor

listar_fornecedor_bp = Blueprint('listar_fornecedor_bp', __name__)

@listar_fornecedor_bp.route('/listar_fornecedores')
def listar_fornecedor():
    fornecedores = Fornecedor.query.all()
    return render_template('estoque_templates/fornecedor_templates/listar_fornecedor.html', fornecedores=fornecedores)
