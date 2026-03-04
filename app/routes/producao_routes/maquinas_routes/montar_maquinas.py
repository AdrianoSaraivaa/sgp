# app/routes/producao_routes/maquinas_routes/montar_maquinas.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import logging

from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import inspect
from flask_login import login_required

from app import db
from app.services.serials import generate_serials
from app.services.montagem import capacidade_service
from app.models_sqla import Montagem, GPWorkOrder, EstruturaMaquina, Peca

import app.services.montagem.capacidade_service as cap_srv
from app.services.montagem.capacidade_service import (
    calcular_capacidade_modelo,
    calcular_todas_capacidades,
    calcular_otimizacao,
)

from app.routes.producao_routes.maquinas_routes.consumo_service import (
    reservar_componentes_para_montagem,
    EstoqInsuficiente,
)

from app.routes.producao_routes.painel_routes.order_api import ensure_gp_workorder

# Integração com ROP
from app.routes.producao_routes.painel_routes import rop_service

# ============================================================
# Logger
# ============================================================
# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] logger
# [RESPONSABILIDADE] Configurar logger do módulo para registrar eventos e erros das rotas
# ====================================================================
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
# ====================================================================
# [FIM BLOCO] logger
# ====================================================================

# ============================================================
# Blueprint
# ============================================================
# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] maquinas_bp
# [RESPONSABILIDADE] Definir blueprint e prefixo das rotas de montagem de máquinas
# ====================================================================
maquinas_bp = Blueprint("maquinas_bp", __name__, url_prefix="/producao/montagem")
# ====================================================================
# [FIM BLOCO] maquinas_bp
# ====================================================================

MODELOS = ["PM2100", "PM2200", "PM700", "PM25"]

MODEL_TO_CONJUNTO = {
    "PM2100": "7-000",
    "PM2200": "2-000",
    "PM700": "28-000",
    "PM25": "PM0025",
}


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _resolver_codigo_conjunto
# [RESPONSABILIDADE] Resolver o código do conjunto/BOM a partir do modelo e registrar logs de diagnóstico
# ====================================================================
def _resolver_codigo_conjunto(modelo: str) -> str | None:
    codigo = MODEL_TO_CONJUNTO.get(modelo)
    if not codigo:
        logger.error(
            f"[resolver] Sem mapeamento para modelo='{modelo}'. Atualize MODEL_TO_CONJUNTO."
        )
    else:
        logger.debug(f"[resolver] Modelo '{modelo}' -> Conjunto '{codigo}'")
    return codigo


# ====================================================================
# [FIM BLOCO] _resolver_codigo_conjunto
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _assert_bom_existe
# [RESPONSABILIDADE] Validar existência de BOM/estrutura para o conjunto informado
# ====================================================================
def _assert_bom_existe(codigo_conjunto: str) -> bool:
    qtd = (
        db.session.query(EstruturaMaquina)
        .filter(EstruturaMaquina.codigo_maquina == codigo_conjunto)
        .limit(1)
        .count()
    )
    logger.debug(
        f"[pré-checagem] BOM para '{codigo_conjunto}': {'ENCONTRADA' if qtd > 0 else 'NÃO ENCONTRADA'}"
    )
    return qtd > 0


# ====================================================================
# [FIM BLOCO] _assert_bom_existe
# ====================================================================


# ============================================================
# Views / APIs
# ============================================================
@maquinas_bp.route("/", methods=["GET"])
@login_required
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] pagina_montagem
# [RESPONSABILIDADE] Renderizar página principal de montagem de máquina
# ====================================================================
def pagina_montagem():
    return render_template("producao_templates/montagem_templates/montar_maquina.html")


# ====================================================================
# [FIM BLOCO] pagina_montagem
# ====================================================================


@maquinas_bp.route("/api/capacidade", methods=["GET"])
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] api_capacidade
# [RESPONSABILIDADE] Retornar capacidades calculadas por modelo e registrar resumo em log
# ====================================================================
def api_capacidade():
    try:
        capacidades = calcular_todas_capacidades(MODELOS)
        resumo = ", ".join(
            [f"{k}: {v.get('capacidade')}" for k, v in capacidades["modelos"].items()]
        )
        logger.info(f"[cap] resumo: {{ {resumo} }}")
        return jsonify(capacidades)
    except Exception as e:
        logger.exception("Erro ao calcular capacidade")
        return jsonify({"ok": False, "erro": str(e)}), 500


# ====================================================================
# [FIM BLOCO] api_capacidade
# ====================================================================


@maquinas_bp.route("/api/otimizacao", methods=["GET"])
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] api_otimizacao
# [RESPONSABILIDADE] Calcular e retornar plano otimizado a partir das capacidades atuais
# ====================================================================
def api_otimizacao():
    try:
        capacidades = calcular_todas_capacidades(MODELOS)["modelos"]
        plano = calcular_otimizacao(capacidades)
        return jsonify(plano)
    except Exception as e:
        logger.exception("Erro ao calcular plano otimizado")
        return jsonify({"ok": False, "erro": str(e)}), 500


# ====================================================================
# [FIM BLOCO] api_otimizacao
# ====================================================================


@maquinas_bp.route("/api/validar", methods=["POST"])
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] api_validar
# [RESPONSABILIDADE] Validar payload de montagem (modelo/quantidade) e checar mapeamento/BOM
# ====================================================================
def api_validar():
    payload = request.get_json(silent=True) or {}
    erros = []

    for modelo, qtd in payload.items():
        try:
            qtd = int(qtd)
        except (ValueError, TypeError):
            erros.append({"modelo": modelo, "motivo": "Quantidade inválida"})
            continue
        if qtd < 0:
            erros.append({"modelo": modelo, "motivo": "Quantidade negativa"})
            continue
        if modelo not in MODELOS:
            erros.append({"modelo": modelo, "motivo": "Modelo desconhecido"})
            continue

        codigo_conjunto = _resolver_codigo_conjunto(modelo)
        if not codigo_conjunto:
            erros.append(
                {"modelo": modelo, "motivo": "Modelo sem mapeamento para conjunto/BOM"}
            )
            continue
        if not _assert_bom_existe(codigo_conjunto):
            erros.append(
                {
                    "modelo": modelo,
                    "motivo": f"BOM não encontrada para '{codigo_conjunto}'",
                }
            )

    ok = len(erros) == 0
    return jsonify({"ok": ok, "erros": erros})


# ====================================================================
# [FIM BLOCO] api_validar
# ====================================================================


@maquinas_bp.route("/api/montadas", methods=["GET"])
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] api_montadas
# [RESPONSABILIDADE] Listar montagens recentes e formatar data/hora para horário local
# ====================================================================
def api_montadas():
    itens = Montagem.query.order_by(Montagem.id.desc()).limit(300).all()

    def _fmt_datetime(dt):
        try:
            if not dt:
                return ""
            dt_local = dt.replace(tzinfo=timezone.utc).astimezone(
                timezone(timedelta(hours=-3))
            )
            return dt_local.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            return str(dt)

    return jsonify(
        [
            {
                **m.as_dict(),
                "serie": m.serial,
                "data_hora": _fmt_datetime(m.data_hora),
            }
            for m in itens
        ]
    )


# ====================================================================
# [FIM BLOCO] api_montadas
# ====================================================================


@maquinas_bp.route("/api/montar", methods=["POST"])
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] api_montar
# [RESPONSABILIDADE] Montar lote: gerar seriais, reservar componentes, criar ordens no painel e checar ROP/OMIE
# ====================================================================
def api_montar():
    data = request.get_json() or {}
    modelo = (data.get("modelo") or "").strip()
    quantidade = int(data.get("quantidade") or 0)
    usuario = (data.get("usuario") or "Operador").strip()

    if not modelo or quantidade <= 0:
        return (
            jsonify(
                {
                    "ok": False,
                    "erros": [
                        {
                            "modelo": modelo or "-",
                            "motivo": "Informe modelo e quantidade > 0",
                        }
                    ],
                }
            ),
            400,
        )
    if modelo not in MODELOS:
        return (
            jsonify(
                {
                    "ok": False,
                    "erros": [{"modelo": modelo, "motivo": "Modelo desconhecido"}],
                }
            ),
            400,
        )

    codigo_conjunto = _resolver_codigo_conjunto(modelo)
    if not codigo_conjunto:
        return (
            jsonify(
                {
                    "ok": False,
                    "erros": [
                        {"modelo": modelo, "motivo": "Sem mapeamento para conjunto/BOM"}
                    ],
                }
            ),
            400,
        )
    if not _assert_bom_existe(codigo_conjunto):
        return (
            jsonify(
                {
                    "ok": False,
                    "erros": [
                        {
                            "modelo": modelo,
                            "motivo": f"BOM não encontrada para '{codigo_conjunto}'",
                        }
                    ],
                }
            ),
            400,
        )

    try:
        seriais = generate_serials(modelo, quantidade, usuario)
    except Exception as e:
        logger.exception("Erro ao gerar seriais")
        return (
            jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": str(e)}]}),
            500,
        )

    criadas = []
    for s in seriais:
        m = Montagem(
            modelo=modelo,
            serial=s,
            usuario=usuario,
            data_hora=datetime.utcnow(),
            status="OK",
            label_printed=False,
            label_print_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(m)
        criadas.append(m)

    try:
        referencia = (
            f"LOTE-{modelo}-{codigo_conjunto}-{seriais[0]}..{seriais[-1]}"
            if len(seriais) > 1
            else f"{codigo_conjunto}-{seriais[0]}"
        )
        reservar_componentes_para_montagem(
            modelo=codigo_conjunto,
            quantidade_unidades=quantidade,
            usuario=usuario,
            referencia=referencia,
            session=db.session,
        )
        db.session.commit()
    except EstoqInsuficiente as e:
        db.session.rollback()
        faltas = [
            {
                "codigo_peca": f.codigo_peca,
                "necessario": f.necessario,
                "disponivel": f.disponivel,
            }
            for f in e.faltas
        ]
        return (
            jsonify({"ok": False, "motivo": "ESTOQUE_INSUFICIENTE", "faltas": faltas}),
            409,
        )
    except Exception as e:
        db.session.rollback()
        logger.exception("Erro ao salvar montagens/reserva")
        return (
            jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": str(e)}]}),
            400,
        )

    warn = None
    try:
        insp = inspect(db.engine)
        if not insp.has_table("gp_work_order"):
            db.create_all()

        for m in criadas:
            order = ensure_gp_workorder(
                db.session, serial=str(m.serial), modelo=str(m.modelo)
            )
            if not getattr(order, "current_bench", None):
                order.current_bench = "sep"

        db.session.commit()

        # 5) (novo passo) Atualiza alertas ROP de produção (conjuntos)
        try:
            conjunto = (
                db.session.query(Peca)
                .filter_by(codigo_pneumark=codigo_conjunto)
                .one_or_none()
            )
            if conjunto:
                rop_service.handle_rop_on_change(conjunto, db.session)
                logger.info(
                    f"[ROP] Estoque do conjunto {codigo_conjunto} atualizado; verificação de ROP realizada."
                )
            else:
                logger.error(
                    f"[ROP] Peça conjunto {codigo_conjunto} não encontrada para verificar ROP."
                )
        except Exception as e:
            logger.exception(
                f"[ROP] Erro ao atualizar alerta de Ponto de Pedido para {codigo_conjunto}: {e}"
            )

        # 6) (novo passo) Verifica ROP de peças consumidas e integra com OMIE
        try:
            # Obter lista de componentes da BOM do conjunto e seus estoques atualizados
            componentes = (
                db.session.query(EstruturaMaquina)
                .filter_by(codigo_maquina=codigo_conjunto)
                .all()
            )
            for comp in componentes:
                peca_consumida = (
                    db.session.query(Peca)
                    .filter_by(codigo_pneumark=comp.codigo_peca)
                    .one_or_none()
                )
                if peca_consumida and peca_consumida.ponto_pedido is not None:
                    estoque = peca_consumida.estoque_atual or 0
                    ponto = peca_consumida.ponto_pedido or 0
                    if estoque <= ponto:
                        # Gera requisição de compra no OMIE
                        from app.utils import omie_utils

                        try:
                            quantidade_sugerida = (
                                peca_consumida.estoque_maximo or estoque
                            ) - estoque
                            if quantidade_sugerida > 0:
                                omie_utils.solicitar_requisicao_compra(
                                    peca_consumida, quantidade_sugerida
                                )
                                logger.info(
                                    f"[OMIE] Requisição de compra gerada para peça {peca_consumida.codigo_pneumark} (estoque {estoque} <= PP {ponto})."
                                )
                        except Exception as e:
                            logger.error(
                                f"[OMIE] Falha ao solicitar compra para peça {peca_consumida.codigo_pneumark}: {e}"
                            )
            # (nenhum commit aqui, omie_utils deve tratar persistência em sua implementação)
        except Exception as e:
            logger.exception(f"Erro ao verificar ROP de peças após montagem: {e}")

    except Exception as e:
        db.session.rollback()
        warn = f"Falha ao garantir/enfileirar ordens no Painel: {e}"
        logger.exception("[painel] Erro ao garantir/enfileirar ordens no Painel")

    resp = {"ok": True, "itens": [m.as_dict() for m in criadas]}
    if warn:
        resp["warning"] = warn
    return jsonify(resp)


# ====================================================================
# [FIM BLOCO] api_montar
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: logger
# BLOCO_UTIL: maquinas_bp
# FUNÇÃO: _resolver_codigo_conjunto
# FUNÇÃO: _assert_bom_existe
# FUNÇÃO: pagina_montagem
# FUNÇÃO: api_capacidade
# FUNÇÃO: api_otimizacao
# FUNÇÃO: api_validar
# FUNÇÃO: api_montadas
# FUNÇÃO: api_montar
# ====================================================================
