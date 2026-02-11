
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models_sqla import Fornecedor

cadastrar_fornecedor_bp = Blueprint('cadastrar_fornecedor_bp', __name__)

@cadastrar_fornecedor_bp.route('/cadastrar_fornecedor', methods=['GET', 'POST'])
def cadastrar_fornecedor():
    if request.method == 'POST':
        novo = Fornecedor(
            nome_empresa=request.form['nome_empresa'],
            nome_contato=request.form['nome_contato'],
            telefone1=request.form['telefone1'],
            telefone2=request.form['telefone2'],
            email1=request.form['email1'],
            email2=request.form['email2'],
        )
        db.session.add(novo)
        db.session.commit()
        flash("Fornecedor cadastrado com sucesso!")
        return redirect(url_for('cadastrar_fornecedor_bp.cadastrar_fornecedor'))

    return render_template('estoque_templates/fornecedor_templates/cadastrar_fornecedor.html')
