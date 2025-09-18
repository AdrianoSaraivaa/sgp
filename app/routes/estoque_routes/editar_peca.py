
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
# Import from SQLAlchemy models so that .query methods are available
from app.models_sqla import Peca, EstruturaMaquina
from sqlalchemy.exc import IntegrityError
from app.routes.producao_routes.painel_routes.rop_service import handle_rop_on_change



editar_peca_bp = Blueprint('editar_peca_bp', __name__)

# Rota para editar uma peça normal
@editar_peca_bp.route('/editar_peca/<int:peca_id>', methods=['GET', 'POST'])
def editar_peca(peca_id):
    peca = Peca.query.get_or_404(peca_id)

    if request.method == 'POST':
        try:
            # campos de texto
            peca.codigo_pneumark = (request.form.get('codigo_pneumark') or peca.codigo_pneumark).strip()
            peca.codigo_omie     = request.form.get('codigo_omie') or peca.codigo_omie
            peca.descricao       = request.form.get('descricao') or peca.descricao

            # campos numéricos (com fallback seguro)
            peca.estoque_minimo  = int(request.form.get('estoque_minimo') or peca.estoque_minimo or 0)
            peca.ponto_pedido    = int(request.form.get('ponto_pedido')   or peca.ponto_pedido   or 0)
            peca.estoque_maximo  = int(request.form.get('estoque_maximo') or peca.estoque_maximo or 0)
            peca.estoque_atual   = int(request.form.get('estoque_atual')  or peca.estoque_atual  or 0)
            peca.margem          = float(request.form.get('margem')       or peca.margem         or 0)
            peca.custo           = float(request.form.get('custo')        or peca.custo          or 0)

            db.session.commit()
            flash('Peça atualizada com sucesso!', 'success')
            return redirect(url_for('listar_pecas_bp.listar_pecas'))

        except IntegrityError:
            db.session.rollback()
            flash('Código Pneumark duplicado. Escolha outro.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar a peça: {e}', 'danger')

    return render_template('estoque_templates/editar_peca.html', peca=peca)




# Rota para editar estrutura do conjunto (GET)
@editar_peca_bp.route('/editar_estrutura/<int:peca_id>', methods=['GET'])
def editar_estrutura_conjunto(peca_id):
    conjunto = Peca.query.get_or_404(peca_id)
    estrutura_bruta = EstruturaMaquina.query.filter_by(codigo_maquina=conjunto.codigo_pneumark).all()

    estrutura = []
    for item in estrutura_bruta:
        peca = Peca.query.filter_by(codigo_pneumark=item.codigo_peca).first()
        if peca:
            estrutura.append({
                'codigo_peca': item.codigo_peca,
                'descricao': peca.descricao,
                'quantidade': item.quantidade
            })

    return render_template('estoque_templates/editar_conjunto.html', conjunto=conjunto, estrutura=estrutura)


# Rota para salvar alterações da estrutura (POST)
@editar_peca_bp.route('/salvar_estrutura/<int:peca_id>', methods=['POST'])
def salvar_estrutura_conjunto(peca_id):
    conjunto = Peca.query.get_or_404(peca_id)
    novo_codigo_maquina = (conjunto.codigo_pneumark or "").strip()

    try:
        # Remove a estrutura antiga
        EstruturaMaquina.query.filter_by(codigo_maquina=novo_codigo_maquina).delete()

        # Lê os dados do formulário
        codigos_pecas = request.form.getlist('codigo_peca[]')
        quantidades   = request.form.getlist('quantidade[]')

        if len(codigos_pecas) != len(quantidades):
            raise ValueError("Listas de peças e quantidades possuem tamanhos diferentes.")

        inseridos = 0

        # Cria nova estrutura (ignora linhas vazias ou quantidades <= 0)
        for codigo, qtd_str in zip(codigos_pecas, quantidades):
            codigo = (codigo or "").strip()
            if not codigo:
                continue
            try:
                qtd = int(qtd_str)
            except (TypeError, ValueError):
                qtd = 0
            if qtd <= 0:
                continue

            nova_estrutura = EstruturaMaquina(
                codigo_maquina=novo_codigo_maquina,
                codigo_peca=codigo,
                quantidade=qtd
            )
            db.session.add(nova_estrutura)
            inseridos += 1

        db.session.commit()

        # (Opcional) Dispara checagem ROP após salvar a estrutura
        try:
            from app.routes.producao_routes.painel_routes.rop_service import handle_rop_on_change
            if (conjunto.tipo or "").lower() == "conjunto":
                handle_rop_on_change(conjunto, db.session)
        except Exception as e:
            # não quebra o fluxo se falhar
            print(f"[ROP] Aviso ao processar ROP no salvar_estrutura: {e}")

        flash(f'Estrutura do conjunto atualizada com sucesso! Itens: {inseridos}', 'success')
        return redirect(url_for('listar_pecas_bp.listar_pecas'))

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar estrutura: {e}', 'danger')
        return redirect(url_for('listar_pecas_bp.listar_pecas'))
