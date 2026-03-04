from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db

# Import from SQLAlchemy models so that .query methods are available
from app.models_sqla import Peca, EstruturaMaquina
from sqlalchemy.exc import IntegrityError
from app.routes.producao_routes.painel_routes.rop_service import handle_rop_on_change


# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] editar_peca_bp
# [RESPONSABILIDADE] Registrar rotas relacionadas à edição de peça e estrutura de conjunto
# ====================================================================
editar_peca_bp = Blueprint("editar_peca_bp", __name__)


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] editar_peca
# [RESPONSABILIDADE] Atualizar dados de uma peça normal pelo ID informado
# ====================================================================
# Rota para editar uma peça normal
@editar_peca_bp.route("/editar_peca/<int:peca_id>", methods=["GET", "POST"])
def editar_peca(peca_id):
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_peca_por_id_db
    # [RESPONSABILIDADE] Recuperar peça pelo identificador informado para edição
    # ====================================================================
    peca = Peca.query.get_or_404(peca_id)

    if request.method == "POST":
        try:
            # campos de texto
            peca.codigo_pneumark = (
                request.form.get("codigo_pneumark") or peca.codigo_pneumark
            ).strip()
            peca.codigo_omie = request.form.get("codigo_omie") or peca.codigo_omie
            peca.descricao = request.form.get("descricao") or peca.descricao

            # campos numéricos (com fallback seguro)
            peca.estoque_minimo = int(
                request.form.get("estoque_minimo") or peca.estoque_minimo or 0
            )
            peca.ponto_pedido = int(
                request.form.get("ponto_pedido") or peca.ponto_pedido or 0
            )
            peca.estoque_maximo = int(
                request.form.get("estoque_maximo") or peca.estoque_maximo or 0
            )
            peca.estoque_atual = int(
                request.form.get("estoque_atual") or peca.estoque_atual or 0
            )
            peca.margem = float(request.form.get("margem") or peca.margem or 0)
            peca.custo = float(request.form.get("custo") or peca.custo or 0)

            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] commit_edicao_peca_db
            # [RESPONSABILIDADE] Confirmar atualização dos dados da peça no banco de dados
            # ====================================================================
            db.session.commit()
            flash("Peça atualizada com sucesso!", "success")
            return redirect(url_for("listar_pecas_bp.listar_pecas"))

        except IntegrityError:
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] rollback_integrityerror_peca_db
            # [RESPONSABILIDADE] Reverter transação ao detectar violação de integridade (ex: código duplicado)
            # ====================================================================
            db.session.rollback()
            flash("Código Pneumark duplicado. Escolha outro.", "danger")
        except Exception as e:
            # ====================================================================
            # [BLOCO] BLOCO_DB
            # [NOME] rollback_erro_generico_peca_db
            # [RESPONSABILIDADE] Reverter transação ao detectar erro não previsto durante a atualização
            # ====================================================================
            db.session.rollback()
            flash(f"Erro ao atualizar a peça: {e}", "danger")

    return render_template("estoque_templates/editar_peca.html", peca=peca)


# ====================================================================
# [FIM BLOCO] editar_peca
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] editar_estrutura_conjunto
# [RESPONSABILIDADE] Carregar estrutura (BOM) do conjunto para edição
# ====================================================================
# Rota para editar estrutura do conjunto (GET)
@editar_peca_bp.route("/editar_estrutura/<int:peca_id>", methods=["GET"])
def editar_estrutura_conjunto(peca_id):
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_conjunto_para_edicao_db
    # [RESPONSABILIDADE] Recuperar conjunto pelo identificador informado
    # ====================================================================
    conjunto = Peca.query.get_or_404(peca_id)
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_estrutura_bruta_db
    # [RESPONSABILIDADE] Buscar itens da estrutura vinculados ao código do conjunto
    # ====================================================================
    estrutura_bruta = EstruturaMaquina.query.filter_by(
        codigo_maquina=conjunto.codigo_pneumark
    ).all()

    estrutura = []
    for item in estrutura_bruta:
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] consulta_peca_por_codigo_estrutura_db
        # [RESPONSABILIDADE] Buscar peça por código para montar visão da estrutura do conjunto
        # ====================================================================
        peca = Peca.query.filter_by(codigo_pneumark=item.codigo_peca).first()
        if peca:
            estrutura.append(
                {
                    "codigo_peca": item.codigo_peca,
                    "descricao": peca.descricao,
                    "quantidade": item.quantidade,
                }
            )

    return render_template(
        "estoque_templates/editar_conjunto.html", conjunto=conjunto, estrutura=estrutura
    )


# ====================================================================
# [FIM BLOCO] editar_estrutura_conjunto
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] salvar_estrutura_conjunto
# [RESPONSABILIDADE] Recriar e salvar estrutura (BOM) do conjunto a partir dos dados do formulário
# ====================================================================
# Rota para salvar alterações da estrutura (POST)
@editar_peca_bp.route("/salvar_estrutura/<int:peca_id>", methods=["POST"])
def salvar_estrutura_conjunto(peca_id):
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_conjunto_para_salvar_estrutura_db
    # [RESPONSABILIDADE] Recuperar conjunto pelo identificador informado para salvar estrutura
    # ====================================================================
    conjunto = Peca.query.get_or_404(peca_id)
    novo_codigo_maquina = (conjunto.codigo_pneumark or "").strip()

    try:
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] limpeza_estrutura_antiga_db
        # [RESPONSABILIDADE] Remover itens antigos da estrutura do conjunto antes de inserir os novos
        # ====================================================================
        # Remove a estrutura antiga
        EstruturaMaquina.query.filter_by(codigo_maquina=novo_codigo_maquina).delete()

        # Lê os dados do formulário
        codigos_pecas = request.form.getlist("codigo_peca[]")
        quantidades = request.form.getlist("quantidade[]")

        if len(codigos_pecas) != len(quantidades):
            raise ValueError(
                "Listas de peças e quantidades possuem tamanhos diferentes."
            )

        inseridos = 0

        # Cria nova estrutura (ignora linhas vazias ou quantidades <= 0)
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] insercao_nova_estrutura_db
        # [RESPONSABILIDADE] Inserir nova estrutura do conjunto com validações de código e quantidade
        # ====================================================================
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
                codigo_maquina=novo_codigo_maquina, codigo_peca=codigo, quantidade=qtd
            )
            db.session.add(nova_estrutura)
            inseridos += 1

        db.session.commit()

        # (Opcional) Dispara checagem ROP após salvar a estrutura
        # ====================================================================
        # [BLOCO] BLOCO_UTIL
        # [NOME] disparo_rop_pos_salvar_estrutura
        # [RESPONSABILIDADE] Acionar verificação de ROP após salvar estrutura do conjunto (sem quebrar fluxo)
        # ====================================================================
        try:
            from app.routes.producao_routes.painel_routes.rop_service import (
                handle_rop_on_change,
            )

            if (conjunto.tipo or "").lower() == "conjunto":
                handle_rop_on_change(conjunto, db.session)
        except Exception as e:
            # não quebra o fluxo se falhar
            print(f"[ROP] Aviso ao processar ROP no salvar_estrutura: {e}")

        flash(
            f"Estrutura do conjunto atualizada com sucesso! Itens: {inseridos}",
            "success",
        )
        return redirect(url_for("listar_pecas_bp.listar_pecas"))

    except Exception as e:
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] rollback_erro_salvar_estrutura_db
        # [RESPONSABILIDADE] Reverter transação ao detectar erro ao salvar estrutura do conjunto
        # ====================================================================
        db.session.rollback()
        flash(f"Erro ao salvar estrutura: {e}", "danger")
        return redirect(url_for("listar_pecas_bp.listar_pecas"))


# ====================================================================
# [FIM BLOCO] salvar_estrutura_conjunto
# ====================================================================

# ====================================================================
# [FIM BLOCO] editar_peca_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: editar_peca_bp
# FUNÇÃO: editar_peca
# BLOCO_DB: consulta_peca_por_id_db
# BLOCO_DB: commit_edicao_peca_db
# BLOCO_DB: rollback_integrityerror_peca_db
# BLOCO_DB: rollback_erro_generico_peca_db
# FUNÇÃO: editar_estrutura_conjunto
# BLOCO_DB: consulta_conjunto_para_edicao_db
# BLOCO_DB: consulta_estrutura_bruta_db
# BLOCO_DB: consulta_peca_por_codigo_estrutura_db
# FUNÇÃO: salvar_estrutura_conjunto
# BLOCO_DB: consulta_conjunto_para_salvar_estrutura_db
# BLOCO_DB: limpeza_estrutura_antiga_db
# BLOCO_DB: insercao_nova_estrutura_db
# BLOCO_UTIL: disparo_rop_pos_salvar_estrutura
# BLOCO_DB: rollback_erro_salvar_estrutura_db
# ====================================================================
