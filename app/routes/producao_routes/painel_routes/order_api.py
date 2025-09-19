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
