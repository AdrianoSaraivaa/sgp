
from flask import Blueprint, render_template, request, redirect, url_for
from app import db
# Use the SQLAlchemy models instead of dataclasses. Import from the
# auto-generated models_sqla package to ensure that ``.query`` is available.
from app.models_sqla import Peca, FornecedoresPorPeca as FornecedorPorPeca, EstruturaMaquina


cadastrar_peca_bp = Blueprint('cadastrar_peca_bp', __name__)

@cadastrar_peca_bp.route('/cadastrar_peca', methods=['GET', 'POST'])
def cadastrar_peca():
    if request.method == 'POST':
        # === Dados principais ===
        tipo_item = request.form.get('tipo_item')  # "peca" ou "conjunto"
        descricao = request.form.get('descricao')
        codigo_pneumark = request.form.get('codigo_pneumark')
        codigo_omie = request.form.get('codigo_omie')
        estoque_minimo = int(request.form.get('estoque_minimo') or 0)
        ponto_pedido = int(request.form.get('ponto_pedido') or 0)
        estoque_maximo = int(request.form.get('estoque_maximo') or 0)
        estoque_atual = int(request.form.get('estoque_atual') or 0)
        margem = float(request.form.get('margem') or 0)

        # === Fornecedores ===
        custo_total = 0
        fornecedores = []

        for i in range(1, 6):
            fornecedor = request.form.get(f'fornecedor{i}')
            etapa = request.form.get(f'etapa{i}')
            preco = request.form.get(f'preco{i}')
            if fornecedor and etapa and preco:
                preco = float(preco)
                custo_total += preco
                fornecedores.append({
                    'fornecedor': fornecedor,
                    'etapa': etapa,
                    'preco': preco
                })

        custo_total_final = custo_total + (custo_total * (margem / 100))

        # === Salvar peça/conjunto ===
        nova_peca = Peca(
            tipo=tipo_item,
            descricao=descricao,
            codigo_pneumark=codigo_pneumark,
            codigo_omie=codigo_omie,
            estoque_minimo=estoque_minimo,
            ponto_pedido=ponto_pedido,
            estoque_maximo=estoque_maximo,
            estoque_atual=estoque_atual,
            margem=margem,
            custo=custo_total_final
        )
        db.session.add(nova_peca)
        db.session.commit()

        # === Salvar fornecedores ===
        for f in fornecedores:
            fornecedor_peca = FornecedorPorPeca(
                peca_id=nova_peca.id,
                fornecedor=f['fornecedor'],
                etapa=f['etapa'],
                preco=f['preco']
            )
            db.session.add(fornecedor_peca)

        # === Estrutura do conjunto (se for tipo conjunto) ===
        if tipo_item == 'conjunto':
            estrutura_raw = request.form.get('estrutura_conjunto')  # "2|PEÇA A|001-A;1|PEÇA B|002-B;"
            if estrutura_raw:
                itens = estrutura_raw.strip(';').split(';')
                for item in itens:
                    partes = item.split('|')
                    if len(partes) == 3:
                        quantidade, nome, codigo = partes
                        estrutura = EstruturaMaquina(
                            codigo_maquina=codigo_pneumark,
                            codigo_peca=codigo,
                            quantidade=int(quantidade)
                        )
                        db.session.add(estrutura)

        db.session.commit()
        return redirect(url_for('cadastrar_peca_bp.cadastrar_peca'))
    # Import ``Fornecedor`` from the SQLAlchemy models.  The original code
    # referenced ``app.models.estoque_models.fornecedor``, which no longer
    # defines a SQLAlchemy model.
    from app.models_sqla import Fornecedor

    # Busca todos os nomes dos fornecedores cadastrados no banco
    fornecedores_disponiveis = [
        f.nome_empresa for f in Fornecedor.query.order_by(Fornecedor.nome_empresa).all()
    ]

    return render_template(
        'estoque_templates/cadastrar_peca.html',
        fornecedores=fornecedores_disponiveis
    )
