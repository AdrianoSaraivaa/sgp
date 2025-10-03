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
    GPHipotRun
)

trace_api_bp = Blueprint(
    "trace_api_bp",
    __name__,
    url_prefix="/producao/gp"
)

@trace_api_bp.route("/trace/<serial>", methods=["GET"])
def get_trace_timeline(serial):
    """
    Retorna uma timeline consolidada de rastreabilidade para um número de série.
    Combina dados de WorkStages, Checklist Executions, HiPot Runs em ordem cronológica.
    """
    try:
        # Buscar a ordem de trabalho
        work_order = db.session.scalars(
            select(GPWorkOrder).where(GPWorkOrder.serial == serial)
        ).first()
        
        if not work_order:
            return jsonify({"error": f"Número de série {serial} não encontrado"}), 404
        
        timeline = []
        
        # 1. Work Stages (bancadas)
        work_stages = db.session.scalars(
            select(GPWorkStage)
            .where(GPWorkStage.order_id == work_order.id)
            .order_by(GPWorkStage.started_at)
        ).all()
        
        for stage in work_stages:
            timeline.append({
                "timestamp": stage.started_at.isoformat() if stage.started_at else None,
                "type": "work_stage",
                "event": "Início de Etapa",
                "details": {
                    "bench_id": stage.bench_id,
                    "operador": stage.operador,
                    "started_at": stage.started_at.isoformat() if stage.started_at else None,
                    "finished_at": stage.finished_at.isoformat() if stage.finished_at else None,
                    "result": getattr(stage, 'result', None),
                    "observacoes": stage.observacoes,
                    "workstation": getattr(stage, 'workstation', None),
                    "rework_flag": getattr(stage, 'rework_flag', False)
                }
            })
        
        # 2. Checklist Executions
        checklist_execs = db.session.scalars(
            select(GPChecklistExecution)
            .where(GPChecklistExecution.order_id == work_order.id)
            .order_by(GPChecklistExecution.started_at)
        ).all()
        
        for exec_item in checklist_execs:
            # Buscar itens da execução
            exec_items = db.session.scalars(
                select(GPChecklistExecutionItem)
                .where(GPChecklistExecutionItem.exec_id == exec_item.id)
                .order_by(GPChecklistExecutionItem.ordem)
            ).all()
            
            timeline.append({
                "timestamp": exec_item.started_at.isoformat() if exec_item.started_at else None,
                "type": "checklist",
                "event": "Execução de Checklist",
                "details": {
                    "template_id": exec_item.template_id,
                    "bench_id": exec_item.bench_id,
                    "operador": exec_item.operador,
                    "started_at": exec_item.started_at.isoformat() if exec_item.started_at else None,
                    "finished_at": exec_item.finished_at.isoformat() if exec_item.finished_at else None,
                    "result": getattr(exec_item, 'result', None),
                    "total_items": len(exec_items),
                    "items_ok": len([item for item in exec_items if getattr(item, 'status', '') == 'sim']),
                    "items_nok": len([item for item in exec_items if getattr(item, 'status', '') == 'nao']),
                    "observacoes": exec_item.observacoes
                }
            })
        
        # 3. HiPot Runs
        hipot_runs = db.session.scalars(
            select(GPHipotRun)
            .where(GPHipotRun.order_id == work_order.id)
            .order_by(GPHipotRun.started_at)
        ).all()
        
        for hipot in hipot_runs:
            timeline.append({
                "timestamp": hipot.started_at.isoformat() if hipot.started_at else None,
                "type": "hipot",
                "event": "Teste HiPot",
                "details": {
                    "bench_id": hipot.bench_id,
                    "operador": hipot.operador,
                    "started_at": hipot.started_at.isoformat() if hipot.started_at else None,
                    "finished_at": hipot.finished_at.isoformat() if hipot.finished_at else None,
                    "hp_v": hipot.hp_v,
                    "hp_t_s": hipot.hp_t_s,
                    "final_ok": hipot.final_ok,
                    "observacoes": hipot.observacoes
                }
            })
        
        # Ordenar timeline por timestamp
        timeline.sort(key=lambda x: x["timestamp"] or "1900-01-01T00:00:00")
        
        # Informações gerais da ordem
        order_info = {
            "serial": work_order.serial,
            "modelo": work_order.modelo,
            "current_bench": work_order.current_bench,
            "status": work_order.status,
            "created_at": work_order.created_at.isoformat() if work_order.created_at else None,
            "updated_at": work_order.updated_at.isoformat() if work_order.updated_at else None,
            "finished_at": getattr(work_order, 'finished_at', None),
            "hipot_flag": work_order.hipot_flag,
            "hipot_status": work_order.hipot_status,
            "hipot_last_at": work_order.hipot_last_at.isoformat() if work_order.hipot_last_at else None
        }
        
        if order_info["finished_at"]:
            order_info["finished_at"] = order_info["finished_at"].isoformat()
        
        return jsonify({
            "order": order_info,
            "timeline": timeline,
            "summary": {
                "total_events": len(timeline),
                "work_stages": len(work_stages),
                "checklist_executions": len(checklist_execs),
                "hipot_runs": len(hipot_runs)
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@trace_api_bp.route("/trace/<serial>/summary", methods=["GET"])
def get_trace_summary(serial):
    """
    Retorna um resumo consolidado da rastreabilidade para um número de série.
    """
    try:
        work_order = db.session.scalars(
            select(GPWorkOrder).where(GPWorkOrder.serial == serial)
        ).first()
        
        if not work_order:
            return jsonify({"error": f"Número de série {serial} não encontrado"}), 404
        
        # Contar eventos por tipo
        work_stages_count = db.session.scalars(
            select(GPWorkStage)
            .where(GPWorkStage.order_id == work_order.id)
        ).all()
        
        checklist_count = db.session.scalars(
            select(GPChecklistExecution)
            .where(GPChecklistExecution.order_id == work_order.id)
        ).all()
        
        hipot_count = db.session.scalars(
            select(GPHipotRun)
            .where(GPHipotRun.order_id == work_order.id)
        ).all()
        
        # Último evento
        last_stage = db.session.scalars(
            select(GPWorkStage)
            .where(GPWorkStage.order_id == work_order.id)
            .order_by(desc(GPWorkStage.started_at))
        ).first()
        
        return jsonify({
            "serial": work_order.serial,
            "modelo": work_order.modelo,
            "status": work_order.status,
            "current_bench": work_order.current_bench,
            "summary": {
                "work_stages": len(work_stages_count),
                "checklist_executions": len(checklist_count),
                "hipot_runs": len(hipot_count),
                "last_activity": {
                    "bench_id": last_stage.bench_id if last_stage else None,
                    "timestamp": last_stage.started_at.isoformat() if last_stage and last_stage.started_at else None,
                    "operador": last_stage.operador if last_stage else None
                }
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
