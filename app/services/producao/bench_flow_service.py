# -*- coding: utf-8 -*-
"""
app/services/producao/bench_flow_service.py

Serviço responsável por fazer o Painel respeitar o fluxo definido no Setup (gp_bench_config).
Expõe 4 funções públicas:
- route_for_model(modelo)             → lista de bancadas ATIVAS em ordem (b1..b8), sempre garantindo b5 e b8.
- next_bench_for_order(order)         → próxima bancada pela rota considerando etapas já finalizadas.
- set_current_bench_on_scan(...)      → normaliza/realinha a bancada, seta current_bench e abre etapa se necessário.
- advance_after_finish(...)           → avança current_bench para a próxima bancada do roteiro após finalizar.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Set, Dict
from datetime import datetime

from app import db
from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage

# ====================================================================
# [BLOCO] CONFIG_LOGGER
# [NOME] logger
# [RESPONSABILIDADE] Inicializar logger do módulo para rastreamento do fluxo de bancadas
# ====================================================================
logger = logging.getLogger(__name__)
# ====================================================================
# [FIM BLOCO] logger
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] ROUTE_ORDER
# [RESPONSABILIDADE] Definir ordem fixa das bancadas para montagem da rota (b1..b8)
# ====================================================================
ROUTE_ORDER: List[str] = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
# ====================================================================
# [FIM BLOCO] ROUTE_ORDER
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] MANDATORY
# [RESPONSABILIDADE] Definir bancadas obrigatórias que sempre devem existir na rota
# ====================================================================
MANDATORY: Set[str] = {"b5", "b8"}
# ====================================================================
# [FIM BLOCO] MANDATORY
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] ESTOQUE
# [RESPONSABILIDADE] Definir identificador especial para estado/bancada de estoque/seleção
# ====================================================================
ESTOQUE = "sep"
# ====================================================================
# [FIM BLOCO] ESTOQUE
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] FINAL
# [RESPONSABILIDADE] Definir identificador especial para estado final do fluxo
# ====================================================================
FINAL = "final"
# ====================================================================
# [FIM BLOCO] FINAL
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _norm_bench_id
# [RESPONSABILIDADE] Normalizar identificadores de bancada para padrão interno (b1..b8, sep, final)
# ====================================================================
def _norm_bench_id(bid: str) -> str:
    bid = (bid or "").strip().lower()
    if bid in ROUTE_ORDER or bid in {ESTOQUE, FINAL}:
        return bid
    if bid.startswith("b") and bid[1:].isdigit():
        return f"b{int(bid[1:])}"
    if bid.isdigit():
        return f"b{int(bid)}"
    return bid


# ====================================================================
# [FIM BLOCO] _norm_bench_id
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _find_model_by_name_or_code
# [RESPONSABILIDADE] Localizar modelo por nome ou código de modelo no banco
# ====================================================================
def _find_model_by_name_or_code(modelo: Optional[str]) -> Optional[GPModel]:
    if not modelo:
        return None
    m = GPModel.query.filter_by(nome=modelo).first()
    if m:
        return m
    try:
        m = GPModel.query.filter_by(code=modelo).first()
        return m
    except Exception:
        return None


# ====================================================================
# [FIM BLOCO] _find_model_by_name_or_code
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_DB
# [NOME] _finished_benches
# [RESPONSABILIDADE] Consultar etapas finalizadas de uma ordem e retornar conjunto de bancadas concluídas
# ====================================================================
def _finished_benches(order_id: int) -> Set[str]:
    rows = (
        GPWorkStage.query.filter_by(order_id=order_id)
        .filter(GPWorkStage.finished_at.isnot(None))
        .all()
    )
    return {(getattr(r, "bench_id", "") or "").lower() for r in rows}


# ====================================================================
# [FIM BLOCO] _finished_benches
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _bench_key_from_cfg
# [RESPONSABILIDADE] Extrair e normalizar a chave da bancada a partir de diferentes campos possíveis na configuração
# ====================================================================
def _bench_key_from_cfg(cfg: GPBenchConfig) -> Optional[str]:
    if hasattr(cfg, "bench_id") and getattr(cfg, "bench_id"):
        return _norm_bench_id(str(getattr(cfg, "bench_id")))
    if hasattr(cfg, "bench") and getattr(cfg, "bench") is not None:
        b = getattr(cfg, "bench")
        return _norm_bench_id(
            f"b{b}" if f"{b}".isdigit() else f"b{str(b).lower().lstrip('b')}"
        )
    if hasattr(cfg, "bench_num") and getattr(cfg, "bench_num") is not None:
        return _norm_bench_id(f"b{getattr(cfg, 'bench_num')}")
    return None


# ====================================================================
# [FIM BLOCO] _bench_key_from_cfg
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _cfg_is_enabled
# [RESPONSABILIDADE] Determinar se uma configuração de bancada está habilitada/ativa
# ====================================================================
def _cfg_is_enabled(cfg: GPBenchConfig) -> bool:
    if hasattr(cfg, "ativo"):
        return bool(getattr(cfg, "ativo"))
    if hasattr(cfg, "enabled"):
        return bool(getattr(cfg, "enabled"))
    if hasattr(cfg, "habilitar"):
        return bool(getattr(cfg, "habilitar"))
    return True


# ====================================================================
# [FIM BLOCO] _cfg_is_enabled
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_DB
# [NOME] route_for_model
# [RESPONSABILIDADE] Montar rota de bancadas ativas por modelo, garantindo bancadas obrigatórias e ordem b1..b8
# ====================================================================
def route_for_model(modelo: str) -> List[str]:
    """
    Retorna lista de bancadas ATIVAS para o modelo.
    Ex: ['b5', 'b6', 'b8'] (se b7 estiver desativada).
    """
    model = _find_model_by_name_or_code(modelo)
    if not model:
        logger.warning(
            f"[bench_flow] Modelo '{modelo}' não encontrado. Usando fallback conservador (b5+b8)."
        )
        return ["b5", "b8"]

    rows = GPBenchConfig.query.filter_by(model_id=model.id).all()
    active: Set[str] = set()
    for r in rows:
        bid = _bench_key_from_cfg(r)
        if not bid:
            continue
        if _cfg_is_enabled(r) and bid.startswith("b") and bid[1:].isdigit():
            active.add(bid)

    active.update(MANDATORY)
    # Ordena baseado na lista fixa b1..b8 para garantir sequencia logica
    rota = [b for b in ROUTE_ORDER if b in active]
    logger.debug(f"[bench_flow] Rota para modelo={modelo}: {rota}")
    return rota


# ====================================================================
# [FIM BLOCO] route_for_model
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] next_bench_for_order
# [RESPONSABILIDADE] Determinar próxima bancada da ordem com base na rota e nas etapas já finalizadas
# ====================================================================
def next_bench_for_order(order: GPWorkOrder) -> str:
    """
    Retorna a primeira bancada da rota que ainda não foi finalizada.
    Se todas finalizadas, retorna 'final'.
    """
    rota = route_for_model(
        getattr(order, "modelo", "") or getattr(order, "model_code", "")
    )
    done = _finished_benches(order.id)
    for b in rota:
        if b not in done:
            return b
    return FINAL


# ====================================================================
# [FIM BLOCO] next_bench_for_order
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_DB
# [NOME] set_current_bench_on_scan
# [RESPONSABILIDADE] Realinhar bancada no scan, atualizar current_bench e abrir etapa em andamento quando aplicável
# ====================================================================
def set_current_bench_on_scan(session, serial: str, bench_id: str) -> Dict[str, str]:
    """
    Chamado quando o usuario scaneia uma bancada especifica.
    Se a bancada nao estiver no roteiro, realinha para a primeira valida.
    """
    bench_id = _norm_bench_id(bench_id)
    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return {"ok": "false", "error": "order_not_found"}

    rota = route_for_model(
        getattr(order, "modelo", "") or getattr(order, "model_code", "")
    )

    # Se tentou scanear algo fora do roteiro (ex: B7 inativa), joga para o inicio ou proxima valida
    if bench_id not in rota and bench_id not in (ESTOQUE, FINAL):
        logger.info(f"[bench_flow] Bench {bench_id} fora do roteiro. Realinhando.")
        # Tenta achar a proxima logica, senao volta pro inicio
        bench_id = next_bench_for_order(order)

    order.current_bench = bench_id

    if bench_id not in (ESTOQUE, FINAL):
        stg = (
            GPWorkStage.query.filter_by(order_id=order.id, bench_id=bench_id)
            .filter(GPWorkStage.finished_at.is_(None))
            .first()
        )
        if not stg:
            stg = GPWorkStage(
                order_id=order.id, bench_id=bench_id, started_at=datetime.utcnow()
            )
            session.add(stg)

    session.commit()
    return {"ok": "true", "current_bench": bench_id}


# ====================================================================
# [FIM BLOCO] set_current_bench_on_scan
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_DB
# [NOME] advance_after_finish
# [RESPONSABILIDADE] Avançar current_bench da ordem após finalização de etapa conforme próxima bancada da rota
# ====================================================================
def advance_after_finish(session, serial: str) -> Dict[str, str]:
    """
    Chamado ao finalizar uma etapa. Calcula a proxima e atualiza a ordem.
    """
    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return {"ok": "false", "error": "order_not_found"}

    nxt = next_bench_for_order(order)
    order.current_bench = nxt
    session.commit()
    return {"ok": "true", "current_bench": nxt}


# ====================================================================
# [FIM BLOCO] advance_after_finish
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] debug_route
# [RESPONSABILIDADE] Expor rota calculada para fins de depuração
# ====================================================================
def debug_route(modelo: str) -> List[str]:
    return route_for_model(modelo)


# ====================================================================
# [FIM BLOCO] debug_route
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_DB
# [NOME] debug_next
# [RESPONSABILIDADE] Expor próxima bancada calculada para uma ordem (por serial) para fins de depuração
# ====================================================================
def debug_next(serial: str) -> str:
    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return "order_not_found"
    return next_bench_for_order(order)


# ====================================================================
# [FIM BLOCO] debug_next
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# CONFIG_LOGGER: logger
# BLOCO_UTIL: ROUTE_ORDER
# BLOCO_UTIL: MANDATORY
# BLOCO_UTIL: ESTOQUE
# BLOCO_UTIL: FINAL
# FUNÇÃO: _norm_bench_id
# FUNÇÃO: _find_model_by_name_or_code
# BLOCO_DB: _finished_benches
# FUNÇÃO: _bench_key_from_cfg
# FUNÇÃO: _cfg_is_enabled
# BLOCO_DB: route_for_model
# BLOCO_UTIL: next_bench_for_order
# BLOCO_DB: set_current_bench_on_scan
# BLOCO_DB: advance_after_finish
# FUNÇÃO: debug_route
# BLOCO_DB: debug_next
# ====================================================================
