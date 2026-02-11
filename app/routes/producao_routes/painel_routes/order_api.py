# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request

from app import db

# Tenta usar o caminho atual (models_sqla). Se não existir, cai no caminho antigo.
try:
    from app.models_sqla import GPWorkOrder  # tipo preferido/atual
except Exception:  # pragma: no cover
    from app.models.producao_models.gp_execucao import GPWorkOrder  # legado

# -----------------------------------------------------------------------------
# Blueprint para o app registrar rotas de ordens no Painel
# -----------------------------------------------------------------------------
gp_painel_order_api_bp = Blueprint(
    "gp_painel_order_api_bp",
    __name__,
    url_prefix="/producao/gp/painel/api/orders",
)

@gp_painel_order_api_bp.get("/ping")
def ping():
    """Healthcheck simples do serviço de ordens do Painel."""
    return jsonify({"ok": True, "service": "order_api"})

# -----------------------------------------------------------------------------
# Serviço: garante que exista um GPWorkOrder para o serial informado.
# Agora cria já com current_bench = 'sep' para aparecer no card ESTOQUE.
# -----------------------------------------------------------------------------
def ensure_gp_workorder(session: db.session, *, serial: str, modelo: str,
                        model_code: Optional[str] = None) -> GPWorkOrder:
    """
    Garante que exista um GPWorkOrder para o serial informado.
    - Se não existir, cria com status 'queued' e current_bench='sep' (entra em ESTOQUE).
    - Se existir, apenas retorna.
    """
    serial = (serial or "").strip()
    modelo = (modelo or "").strip()
    if not serial:
        raise ValueError("serial vazio em ensure_gp_workorder")

    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if order:
        return order

    # NOTA: hipot_status é NOT NULL no schema. Usamos string vazia como default seguro.
    order = GPWorkOrder(
        serial=serial,
        modelo=modelo,
        status="queued",
        current_bench="sep",       # obrigatório para o board mostrar no ESTOQUE
        hipot_flag=False,
        hipot_status="",           # HOTFIX: evitar IntegrityError (NOT NULL)
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(order)
    # commit fica a cargo do chamador
    return order


# -----------------------------------------------------------------------------
# Nova rota: timeline completa de um serial
# -----------------------------------------------------------------------------
from app.models.producao_models.gp_execucao import GPWorkStage

@gp_painel_order_api_bp.get("/timeline/<serial>")
def timeline(serial):
    """Retorna histórico completo de um serial, com etapas por bancada."""
    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return jsonify({"ok": False, "error": f"serial não encontrado: {serial}"}), 404

    stages = (GPWorkStage.query
              .filter_by(order_id=order.id)
              .order_by(GPWorkStage.started_at.asc())
              .all())

    def _dt(x):
        return x.isoformat() if x else None

    data = []
    for s in stages:
        data.append({
            "bench_id": s.bench_id,
            "started_at": _dt(s.started_at),
            "finished_at": _dt(s.finished_at),
            "operador": getattr(s, "operador", None),
            "result": getattr(s, "result", None),
            "rework_flag": bool(getattr(s, "rework_flag", False)),
            "workstation": getattr(s, "workstation", None),
            "observacoes": getattr(s, "observacoes", None),
        })

    return jsonify({
        "ok": True,
        "serial": order.serial,
        "modelo": order.modelo,
        "finished_at": getattr(order, "finished_at", None) and order.finished_at.isoformat(),
        "stages": data,
    })
