from flask import Blueprint, render_template, request, redirect, url_for

login_bp = Blueprint('login_bp', __name__)

USUARIO_VALIDO = 'admin'
SENHA_VALIDA = '1234'

@login_bp.route('/', methods=['GET', 'POST'])
def login():
    erro = None

    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        if usuario == USUARIO_VALIDO and senha == SENHA_VALIDA:
            return redirect(url_for('modulos_bp.tela_modulos'))
        else:
            erro = 'Usuário ou senha inválidos.'

    return render_template('home_templates/login.html', erro=erro)
