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

logger = logging.getLogger(__name__)

ROUTE_ORDER: List[str] = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
MANDATORY: Set[str] = {"b5", "b8"}
ESTOQUE = "sep"
FINAL = "final"


def _norm_bench_id(bid: str) -> str:
    bid = (bid or "").strip().lower()
    if bid in ROUTE_ORDER or bid in {ESTOQUE, FINAL}:
        return bid
    if bid.startswith("b") and bid[1:].isdigit():
        return f"b{int(bid[1:])}"
    if bid.isdigit():
        return f"b{int(bid)}"
    return bid


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


def _finished_benches(order_id: int) -> Set[str]:
    rows = (
        GPWorkStage.query.filter_by(order_id=order_id)
        .filter(GPWorkStage.finished_at.isnot(None))
        .all()
    )
    return {(getattr(r, "bench_id", "") or "").lower() for r in rows}


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


def _cfg_is_enabled(cfg: GPBenchConfig) -> bool:
    if hasattr(cfg, "ativo"):
        return bool(getattr(cfg, "ativo"))
    if hasattr(cfg, "enabled"):
        return bool(getattr(cfg, "enabled"))
    if hasattr(cfg, "habilitar"):
        return bool(getattr(cfg, "habilitar"))
    return True


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


def debug_route(modelo: str) -> List[str]:
    return route_for_model(modelo)


def debug_next(serial: str) -> str:
    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return "order_not_found"
    return next_bench_for_order(order)
