from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models_sqla import Usuario

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] login_bp
# [RESPONSABILIDADE] Registrar rotas de autenticação (login, registro e logout)
# ====================================================================
login_bp = Blueprint("login_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] login
# [RESPONSABILIDADE] Autenticar usuário e redirecionar para a tela de módulos quando válido
# ====================================================================
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
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] consulta_usuario_login_db
        # [RESPONSABILIDADE] Buscar usuário pelo username informado para autenticação
        # ====================================================================
        user = Usuario.query.filter_by(username=usuario_form).first()

        # Verifica se existe e se a senha bate
        if user and user.check_password(senha_form):
            login_user(user)
            return redirect(url_for("modulos_bp.tela_modulos"))
        else:
            erro = "Usuário ou senha incorretos."

    return render_template("home_templates/login.html", erro=erro)


# ====================================================================
# [FIM BLOCO] login
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] registro
# [RESPONSABILIDADE] Cadastrar novo usuário e persistir no banco quando válido
# ====================================================================
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
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] validacao_username_existente_db
            # [RESPONSABILIDADE] Verificar se o username já está cadastrado
            # ====================================================================
            erro = "Este nome de usuário já existe."
        else:
            # Cria novo usuário
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] criacao_usuario_db
            # [RESPONSABILIDADE] Criar e salvar novo usuário no banco de dados
            # ====================================================================
            novo_usuario = Usuario(username=usuario_form)
            novo_usuario.set_password(senha_form)

            db.session.add(novo_usuario)
            db.session.commit()

            sucesso = "Conta criada com sucesso! Faça login."
            # Opcional: redirecionar direto para login
            return redirect(url_for("login_bp.login"))

    return render_template("home_templates/registro.html", erro=erro, sucesso=sucesso)


# ====================================================================
# [FIM BLOCO] registro
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] logout
# [RESPONSABILIDADE] Encerrar sessão do usuário e redirecionar para a tela de login
# ====================================================================
@login_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_bp.login"))


# ====================================================================
# [FIM BLOCO] logout
# ====================================================================

# ====================================================================
# [FIM BLOCO] login_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: login_bp
# FUNÇÃO: login
# BLOCO_DB: consulta_usuario_login_db
# FUNÇÃO: registro
# BLOCO_DB: validacao_username_existente_db
# BLOCO_DB: criacao_usuario_db
# FUNÇÃO: logout
# ====================================================================
