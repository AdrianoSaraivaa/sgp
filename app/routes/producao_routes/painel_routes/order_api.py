from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import inspect
from app.models.producao_models.gp_execucao import GPWorkOrder  # usa os models que já criamos

gp_painel_order_api_bp = Blueprint(
    "gp_painel_order_api_bp",
    __name__,
    url_prefix="/producao/gp/painel/api"
)

def _ensure_tables():
    insp = inspect(db.engine)
    for t in ("gp_work_order", "gp_work_stage"):
        if not insp.has_table(t):
            db.create_all()
            break

@gp_painel_order_api_bp.post("/order/create")
def create_order():
    _ensure_tables()
    data = request.get_json(force=True) or {}
    serial = (data.get("serial") or "").strip()
    modelo = (data.get("modelo") or "DESCONHECIDO").strip()

    if not serial:
        return jsonify({"ok": False, "error": "serial_requerido"}), 400

    # upsert simples por serial
    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        order = GPWorkOrder(serial=serial, modelo=modelo, current_bench="sep", status="queued")
        db.session.add(order)
        db.session.commit()

    return jsonify({"ok": True, "order_id": order.id, "current_bench": order.current_bench, "status": order.status})
