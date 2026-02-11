# app/routes/producao_routes/rastreabilidade_nserie_routes/trace_api.py

from flask import Blueprint, jsonify
from sqlalchemy import select, desc
from datetime import datetime
from app import db
from app.models_sqla import (
    GPWorkOrder,
    GPWorkStage,
    GPChecklistExecution,
    GPChecklistExecutionItem,
    GPHipotRun,
)

trace_api_bp = Blueprint("trace_api_bp", __name__, url_prefix="/producao/gp")


def _iso(dt):
    try:
        return dt.isoformat() if dt else None
    except Exception:
        return str(dt) if dt else None


@trace_api_bp.route("/trace/<serial>", methods=["GET"])
def get_trace_timeline(serial):
    try:
        work_order = db.session.scalars(
            select(GPWorkOrder).where(GPWorkOrder.serial == str(serial))
        ).first()
        if not work_order:
            return jsonify({"error": f"Número de série {serial} não encontrado"}), 404

        timeline = []

        work_stages = db.session.scalars(
            select(GPWorkStage)
            .where(getattr(GPWorkStage, "order_id") == getattr(work_order, "id"))
            .order_by(getattr(GPWorkStage, "started_at"))
        ).all()

        for stage in work_stages:
            started_at = getattr(stage, "started_at", None)
            finished_at = getattr(stage, "finished_at", None)
            timeline.append(
                {
                    "timestamp": _iso(started_at),
                    "type": "work_stage",
                    "event": "Início de Etapa",
                    "details": {
                        "bench_id": getattr(stage, "bench_id", None),
                        "operador": getattr(stage, "operador", None),
                        "started_at": _iso(started_at),
                        "finished_at": _iso(finished_at),
                        "result": getattr(stage, "result", None),
                        "observacoes": getattr(stage, "observacoes", None),
                        "workstation": getattr(stage, "workstation", None),
                        "rework_flag": getattr(stage, "rework_flag", False),
                    },
                }
            )

        checklist_execs = db.session.scalars(
            select(GPChecklistExecution)
            .where(
                getattr(GPChecklistExecution, "serial") == getattr(work_order, "serial")
            )
            .order_by(getattr(GPChecklistExecution, "started_at"))
        ).all()

        for exec_item in checklist_execs:
            exec_id = getattr(exec_item, "id", None)
            exec_items = db.session.scalars(
                select(GPChecklistExecutionItem)
                .where(getattr(GPChecklistExecutionItem, "exec_id") == exec_id)
                .order_by(getattr(GPChecklistExecutionItem, "ordem"))
            ).all()
            items_ok = len(
                [
                    it
                    for it in exec_items
                    if str(getattr(it, "status", "")).strip().lower() == "sim"
                ]
            )
            items_nok = len(
                [
                    it
                    for it in exec_items
                    if str(getattr(it, "status", "")).strip().lower() == "nao"
                ]
            )
            started_at = getattr(exec_item, "started_at", None)
            finished_at = getattr(exec_item, "finished_at", None)
            timeline.append(
                {
                    "timestamp": _iso(started_at),
                    "type": "checklist",
                    "event": "Execução de Checklist",
                    "details": {
                        "template_id": getattr(exec_item, "template_id", None),
                        "bench_id": getattr(exec_item, "bench_id", None),
                        "operador": getattr(exec_item, "operador", None),
                        "started_at": _iso(started_at),
                        "finished_at": _iso(finished_at),
                        "result": getattr(exec_item, "result", None),
                        "total_items": len(exec_items),
                        "items_ok": items_ok,
                        "items_nok": items_nok,
                        "observacoes": getattr(exec_item, "observacoes", None),
                    },
                }
            )

        hipot_runs = db.session.scalars(
            select(GPHipotRun)
            .where(getattr(GPHipotRun, "serial") == getattr(work_order, "serial"))
            .order_by(getattr(GPHipotRun, "started_at"))
        ).all()

        for hipot in hipot_runs:
            started_at = getattr(hipot, "started_at", None)
            finished_at = getattr(hipot, "finished_at", None)
            timeline.append(
                {
                    "timestamp": _iso(started_at),
                    "type": "hipot",
                    "event": "Teste HiPot",
                    "details": {
                        "bench_id": getattr(hipot, "bench_id", None),
                        "operador": getattr(hipot, "operador", None),
                        "started_at": _iso(started_at),
                        "finished_at": _iso(finished_at),
                        "hp_v_obs_v": getattr(
                            hipot, "hp_v_obs_v", getattr(hipot, "hp_v", None)
                        ),
                        "hp_t_s": getattr(hipot, "hp_t_s", None),
                        "final_ok": getattr(hipot, "final_ok", None),
                        "observacoes": getattr(hipot, "observacoes", None),
                    },
                }
            )

        timeline.sort(key=lambda ev: ev.get("timestamp") or "1900-01-01T00:00:00")

        order_info = {
            "serial": getattr(work_order, "serial", None),
            "modelo": getattr(work_order, "modelo", None),
            "current_bench": getattr(work_order, "current_bench", None),
            "status": getattr(work_order, "status", None),
            "created_at": _iso(getattr(work_order, "created_at", None)),
            "updated_at": _iso(getattr(work_order, "updated_at", None)),
            "finished_at": _iso(getattr(work_order, "finished_at", None)),
            "hipot_flag": getattr(work_order, "hipot_flag", None),
            "hipot_status": getattr(work_order, "hipot_status", None),
            "hipot_last_at": _iso(getattr(work_order, "hipot_last_at", None)),
        }

        return jsonify(
            {
                "order": order_info,
                "timeline": timeline,
                "summary": {
                    "total_events": len(timeline),
                    "work_stages": len(work_stages),
                    "checklist_executions": len(checklist_execs),
                    "hipot_runs": len(hipot_runs),
                },
            }
        )

    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


@trace_api_bp.route("/trace/<serial>/summary", methods=["GET"])
def get_trace_summary(serial):
    try:
        work_order = db.session.scalars(
            select(GPWorkOrder).where(GPWorkOrder.serial == str(serial))
        ).first()
        if not work_order:
            return jsonify({"error": f"Número de série {serial} não encontrado"}), 404

        work_stages_count = db.session.scalars(
            select(GPWorkStage).where(
                getattr(GPWorkStage, "order_id") == getattr(work_order, "id")
            )
        ).all()
        checklist_count = db.session.scalars(
            select(GPChecklistExecution).where(
                getattr(GPChecklistExecution, "serial") == getattr(work_order, "serial")
            )
        ).all()
        hipot_count = db.session.scalars(
            select(GPHipotRun).where(
                getattr(GPHipotRun, "serial") == getattr(work_order, "serial")
            )
        ).all()
        last_stage = db.session.scalars(
            select(GPWorkStage)
            .where(getattr(GPWorkStage, "order_id") == getattr(work_order, "id"))
            .order_by(desc(getattr(GPWorkStage, "started_at")))
        ).first()

        return jsonify(
            {
                "serial": getattr(work_order, "serial", None),
                "modelo": getattr(work_order, "modelo", None),
                "status": getattr(work_order, "status", None),
                "current_bench": getattr(work_order, "current_bench", None),
                "summary": {
                    "work_stages": len(work_stages_count),
                    "checklist_executions": len(checklist_count),
                    "hipot_runs": len(hipot_count),
                    "last_activity": {
                        "bench_id": (
                            getattr(last_stage, "bench_id", None)
                            if last_stage
                            else None
                        ),
                        "timestamp": (
                            _iso(getattr(last_stage, "started_at", None))
                            if last_stage
                            else None
                        ),
                        "operador": (
                            getattr(last_stage, "operador", None)
                            if last_stage
                            else None
                        ),
                    },
                },
            }
        )
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
