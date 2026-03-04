# app/routes/estoque_routes/editar_conjunto.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError
from app import db
from app.models_sqla import Peca, EstruturaMaquina

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] editar_conjunto_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à edição de conjunto e sua estrutura (BOM)
# ====================================================================
editar_conjunto_bp = Blueprint("editar_conjunto_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] editar_conjunto
# [RESPONSABILIDADE] Atualizar cabeçalho do conjunto e recriar estrutura (BOM) com base nos dados do formulário
# ====================================================================
@editar_conjunto_bp.route("/editar_conjunto/<int:conjunto_id>", methods=["GET", "POST"])
def editar_conjunto(conjunto_id):
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_conjunto_por_id_db
    # [RESPONSABILIDADE] Recuperar conjunto (registro em Peca) pelo identificador informado
    # ====================================================================
    conjunto = Peca.query.get_or_404(conjunto_id)

    if request.method == "POST":
        # --------- 1) Atualiza CABEÇALHO (tabela Peca) ---------
        novo_codigo = (
            request.form.get("novo_codigo_maquina") or conjunto.codigo_pneumark
        ).strip()
        nova_desc = request.form.get("nova_descricao") or conjunto.descricao
        novo_estoq = request.form.get("novo_estoque_atual")

        if novo_estoq is not None and str(novo_estoq).strip() != "":
            try:
                novo_estoq = int(novo_estoq)
            except ValueError:
                flash("Estoque atual inválido.", "danger")
                return redirect(
                    url_for(
                        "editar_conjunto_bp.editar_conjunto", conjunto_id=conjunto.id
                    )
                )

        codigo_original = (
            request.form.get("codigo_maquina_original") or conjunto.codigo_pneumark
        )

        conjunto.codigo_pneumark = novo_codigo
        conjunto.descricao = nova_desc
        if novo_estoq is not None and novo_estoq != "":
            conjunto.estoque_atual = novo_estoq

        # --------- 2) Atualiza ESTRUTURA (BOM) ---------
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] atualizacao_bom_conjunto_db
        # [RESPONSABILIDADE] Remover BOM antiga pelo código original e inserir nova estrutura do conjunto
        # ====================================================================
        # apaga BOM antiga usando o código original
        EstruturaMaquina.query.filter_by(codigo_maquina=codigo_original).delete()

        codigos_pecas = request.form.getlist("codigo_peca[]")
        quantidades = request.form.getlist("quantidade[]")

        for codigo, qtd in zip(codigos_pecas, quantidades):
            if not codigo:
                continue
            try:
                qtd_int = int(qtd)
            except (TypeError, ValueError):
                qtd_int = 0
            db.session.add(
                EstruturaMaquina(
                    codigo_maquina=novo_codigo,  # usa o código (possivelmente) atualizado
                    codigo_peca=codigo,
                    quantidade=qtd_int,
                )
            )

        try:
            db.session.commit()
            flash("Conjunto e estrutura salvos com sucesso!", "success")
        except IntegrityError:
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] tratamento_integrityerror_db
            # [RESPONSABILIDADE] Reverter transação ao detectar violação de integridade (ex: código duplicado)
            # ====================================================================
            db.session.rollback()
            flash("Código Pneumark duplicado para o conjunto. Escolha outro.", "danger")
        except Exception as e:
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] tratamento_erro_generico_db
            # [RESPONSABILIDADE] Reverter transação ao detectar erro não previsto durante o commit
            # ====================================================================
            db.session.rollback()
            flash(f"Erro ao salvar: {e}", "danger")

        return redirect(url_for("listar_pecas_bp.listar_pecas"))

    # GET: carrega estrutura atual do conjunto
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_estrutura_conjunto_db
    # [RESPONSABILIDADE] Buscar itens de estrutura (BOM) vinculados ao código do conjunto
    # ====================================================================
    estrutura = EstruturaMaquina.query.filter_by(
        codigo_maquina=conjunto.codigo_pneumark
    ).all()
    # monta lista com descrições
    estrutura_view = []
    for item in estrutura:
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] consulta_descricao_peca_estrutura_db
        # [RESPONSABILIDADE] Buscar descrição da peça para compor visão da estrutura do conjunto
        # ====================================================================
        p = Peca.query.filter_by(codigo_pneumark=item.codigo_peca).first()
        estrutura_view.append(
            {
                "codigo_peca": item.codigo_peca,
                "descricao": p.descricao if p else "(não encontrada)",
                "quantidade": item.quantidade,
            }
        )

    return render_template(
        "estoque_templates/editar_conjunto.html",
        conjunto=conjunto,
        estrutura=estrutura_view,
    )


# ====================================================================
# [FIM BLOCO] editar_conjunto
# ====================================================================

# ====================================================================
# [FIM BLOCO] editar_conjunto_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: editar_conjunto_bp
# FUNÇÃO: editar_conjunto
# BLOCO_DB: consulta_conjunto_por_id_db
# BLOCO_DB: atualizacao_bom_conjunto_db
# BLOCO_DB: tratamento_integrityerror_db
# BLOCO_DB: tratamento_erro_generico_db
# BLOCO_DB: consulta_estrutura_conjunto_db
# BLOCO_DB: consulta_descricao_peca_estrutura_db
# ====================================================================
