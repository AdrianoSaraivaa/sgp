# app/services/producao/hipot_service.py
from datetime import datetime
from app import db
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage

# 🔧 TODO: futuramente, ler do setup/receita do modelo.
# Por enquanto, avançamos de b5 -> b6 (ajuste se sua próxima bancada for outra).
def _proxima_bancada(order: GPWorkOrder) -> str:
    # Se já não estiver em b5 por algum motivo, mantemos como está.
    if (order.current_bench or "").lower() != "b5":
        return order.current_bench
    return "b6"  # <-- ajuste aqui se a próxima etapa não for b6

def aplicar_resultado_hipot(payload: dict) -> GPWorkOrder:
    serial = (payload or {}).get("serial")
    status = (payload or {}).get("status", "").upper().strip()
    ts_str = (payload or {}).get("received_at")

    if not serial or status not in {"APR", "OK", "REP"}:
        raise ValueError("Payload inválido: é necessário 'serial' e 'status' em {APR|OK|REP}")

    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        raise ValueError(f"Série não encontrada no SGP: {serial}")

    # Atualiza campos globais do HiPoT
    order.hipot_status = status
    order.hipot_last_at = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()

    # Regras do flag
    order.hipot_flag = (status == "REP")

    # Fechar automaticamente a etapa B5 (se estiver aberta)
    stage_b5_open = GPWorkStage.query.filter_by(
        order_id=order.id, bench_id="b5", finished_at=None
    ).first()
    if stage_b5_open:
        stage_b5_open.finished_at = datetime.utcnow()
        db.session.add(stage_b5_open)

    # 🔴 NOVO: avançar o card para a próxima bancada (mesmo em REP)
    proxima = _proxima_bancada(order)
    if proxima and proxima != order.current_bench:
        order.current_bench = proxima
        # Mantém status em progresso; se você tem outra regra, ajuste aqui
        if order.status not in ("in_progress", "queued"):
            order.status = "in_progress"

    db.session.add(order)
    db.session.commit()
    return order
