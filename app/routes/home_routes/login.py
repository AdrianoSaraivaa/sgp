from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models_sqla import Usuario

login_bp = Blueprint("login_bp", __name__)


@login_bp.route("/", methods=["GET", "POST"])
def login():
    # Se já estiver logado, manda direto pro sistema
    if current_user.is_authenticated:
        return redirect(url_for("modulos_bp.tela_modulos"))

    erro = None
    if request.method == "POST":
        usuario_form = request.form.get("usuario")
        senha_form = request.form.get("senha")

        # Busca usuário no banco
        user = Usuario.query.filter_by(username=usuario_form).first()

        # Verifica se existe e se a senha bate
        if user and user.check_password(senha_form):
            login_user(user)
            return redirect(url_for("modulos_bp.tela_modulos"))
        else:
            erro = "Usuário ou senha incorretos."

    return render_template("home_templates/login.html", erro=erro)


@login_bp.route("/registro", methods=["GET", "POST"])
def registro():
    """
    Rota para novos usuários se cadastrarem.
    Você pode mandar o link: seudominio.com/registro
    """
    if current_user.is_authenticated:
        return redirect(url_for("modulos_bp.tela_modulos"))

    erro = None
    sucesso = None

    if request.method == "POST":
        usuario_form = request.form.get("usuario")
        senha_form = request.form.get("senha")
        confirmar_senha = request.form.get("confirmar_senha")

        # Validações simples
        if not usuario_form or not senha_form:
            erro = "Preencha todos os campos."
        elif senha_form != confirmar_senha:
            erro = "As senhas não coincidem."
        elif Usuario.query.filter_by(username=usuario_form).first():
            erro = "Este nome de usuário já existe."
        else:
            # Cria novo usuário
            novo_usuario = Usuario(username=usuario_form)
            novo_usuario.set_password(senha_form)

            db.session.add(novo_usuario)
            db.session.commit()

            sucesso = "Conta criada com sucesso! Faça login."
            # Opcional: redirecionar direto para login
            return redirect(url_for("login_bp.login"))

    return render_template("home_templates/registro.html", erro=erro, sucesso=sucesso)


@login_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_bp.login"))
