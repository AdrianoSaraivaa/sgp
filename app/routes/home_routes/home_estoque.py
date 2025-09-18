from flask import Blueprint, render_template

estoque_bp = Blueprint('estoque_bp', __name__)

@estoque_bp.route('/estoque')
def tela_estoque():
    return render_template('home_templates/home_estoque.html')
