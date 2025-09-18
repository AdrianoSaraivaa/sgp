from flask import Blueprint, render_template

modulos_bp = Blueprint('modulos_bp', __name__)

# Home disponível em "/" e também em "/modulos"
@modulos_bp.route('/')
@modulos_bp.route('/modulos')
def tela_modulos():
    return render_template('home_templates/modulosIniciais.html')
