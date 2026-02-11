import logging
from datetime import datetime

from app import db
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage
from app.services.producao.bench_flow_service import advance_after_finish

logger = logging.getLogger(__name__)


def aplicar_resultado_hipot(payload: dict) -> dict:
    """
    Processa o resultado do teste HiPot, atualiza a ordem de produção,
    fecha a etapa B5 se aberta e avança conforme o fluxo do modelo.

    Retorna dicionário com campos-chave para consumo em APIs/front.
    """
    serial = (payload or {}).get("serial")
    status = (payload or {}).get("status", "").upper().strip()
    ts_str = (payload or {}).get("received_at")

    if not serial or status not in {"APR", "OK", "REP"}:
        logger.error(f"[hipot_service] Payload inválido: {payload}")
        raise ValueError(
            "Payload inválido: é necessário 'serial' e 'status' em {APR|OK|REP}"
        )

    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        logger.error(f"[hipot_service] Série não encontrada: {serial}")
        raise ValueError(f"Série não encontrada no SGP: {serial}")

    logger.info(
        f"[hipot_service] Aplicando resultado HiPot para serial={serial}, status={status}"
    )

    order.hipot_status = status
    order.hipot_last_at = (
        datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
    )
    order.hipot_flag = status == "REP"

    stage_b5_open = GPWorkStage.query.filter_by(
        order_id=order.id, bench_id="b5", finished_at=None
    ).first()
    if stage_b5_open:
        stage_b5_open.finished_at = datetime.utcnow()
        db.session.add(stage_b5_open)
        logger.debug(
            f"[hipot_service] Etapa B5 fechada automaticamente para serial={serial}"
        )

    db.session.add(order)
    advance_after_finish(db.session, serial)
    db.session.commit()

    logger.info(
        f"[hipot_service] Resultado HiPot aplicado com sucesso para serial={serial}"
    )

    return {
        "serial": order.serial,
        "hipot_status": order.hipot_status,
        "hipot_last_at": (
            order.hipot_last_at.isoformat() if order.hipot_last_at else None
        ),
        "hipot_flag": order.hipot_flag,
    }
