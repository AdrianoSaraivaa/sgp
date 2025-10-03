from __future__ import annotations

"""
gp_painel_scan_api.py  (v5-fix – robusta, com realinhamento por roteiro)

- Garante que TODO scan siga o roteiro salvo em gp_bench_config (campo `ativo`).
- Realinha automaticamente quando a bancada lida não está no roteiro (sem bloquear).
- Evita etapa duplicada; fecha outras abertas ao iniciar nova bancada.
- Mantém debounce da B5; trata station/workstation e result/rework_flag.
- Usa fallback se bench_flow_service não estiver disponível.
"""

# ============================================================
# BLOCO 1 — Imports e Blueprint
# ============================================================
import re
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
import logging

from flask import Blueprint, request, jsonify
from app import db
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage

logger = logging.getLogger(__name__)

gp_painel_scan_api_bp = Blueprint(
    "gp_painel_scan_api_bp",
    __name__,
    url_prefix="/producao/gp/painel/api",
)

# ============================================================
# BLOCO 2 — Constantes e Regex
# ============================================================
# Aceita: "B5-123", "B5:123", "B5 123" (insensível a maiúsculas)
# Captura: bench (1-8) e serial (>=3 dígitos)
SCAN_RE = re.compile(r"^\s*(?:[Bb]\s*([1-8])\s*[-:\s]\s*)?(\d{3,})\s*$", re.IGNORECASE)

REOPEN_LOCK_MIN = 10  # debounce da B5 (minutos)

ROUTE_BENCHES = [f"b{i}" for i in range(1, 9)]
TECH_COLUMNS = ("sep", "final")


# ============================================================
# BLOCO 3 — Helpers de resposta JSON
# ============================================================
def _json_error(
    status: int,
    *,
    error: str,
    message: str,
    hint: Optional[str] = None,
    context: Optional[dict] = None,
):
    payload = {"ok": False, "error": error, "message": message}
    if hint:
        payload["hint"] = hint
    if context:
        payload["context"] = context
    return jsonify(payload), status


def _json_ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload), 200


# ============================================================
# BLOCO 4 — Parse da leitura/scan
# ============================================================
def _parse_scan(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna (bench_id, serial)
      - Com prefixo válido: "B5-581150" -> ("b5", "581150")
      - Sem prefixo: "581150" -> (None, "581150")
      - Inválido: (None, None)
    """
    if not text:
        return None, None
    raw = text.strip()
    m = SCAN_RE.match(raw)
    if m:
        bench = m.group(1)
        serial = m.group(2)
        bench_id = f"b{bench}".lower() if bench else None
        return bench_id, serial
    return None, None


# ============================================================
# BLOCO 5 — Roteiro (forçando rota central)
# ============================================================
def _benches_enabled_for_order(order: GPWorkOrder) -> List[str]:
    """
    Retorna a sequência de bancadas habilitadas para o modelo da ordem,
    sempre priorizando a rota central (bench_flow_service.route_for_model).
    """
    # 1) Tenta usar a rota central (fonte única e confiável)
    try:
        from app.services.producao.bench_flow_service import (
            route_for_model as _route_for_model,
        )

        model_code = getattr(order, "modelo", "") or getattr(order, "model_code", "")
        seq = _route_for_model(model_code) or []
        if seq:
            # garante obrigatórias (por segurança)
            if "b5" not in seq:
                seq.append("b5")
            if "b8" not in seq:
                seq.append("b8")
            # normaliza e ordena
            seq = sorted(set(seq), key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)
            return seq
    except Exception:
        pass

    # 2) Fallback local (só se a importação/rota central falhar MESMO)
    fallback_seq = [f"b{i}" for i in range(1, 9)]
    try:
        from app import db as _db
        from app.models.producao_models.gp_modelos import GPBenchConfig, GPModel  # noqa
    except Exception:
        # último recurso: todas
        seq = fallback_seq
        if "b5" not in seq:
            seq.append("b5")
        if "b8" not in seq:
            seq.append("b8")
        return sorted(set(seq), key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)

    model_code = (
        getattr(order, "model_code", None)
        or getattr(order, "modelo", None)
        or getattr(getattr(order, "model", None), "code", None)
        or getattr(getattr(order, "model", None), "modelo", None)
    )
    model_id = getattr(order, "model_id", None) or getattr(
        getattr(order, "model", None), "id", None
    )

    q = None
    try:
        if hasattr(GPBenchConfig, "model_id") and (model_id or model_code):
            if model_id:
                q = _db.session.query(GPBenchConfig).filter(
                    GPBenchConfig.model_id == model_id
                )
            elif model_code and hasattr(GPModel, "code"):
                q = (
                    _db.session.query(GPBenchConfig)
                    .join(GPModel, GPBenchConfig.model_id == GPModel.id)
                    .filter(GPModel.code == model_code)
                )
        if q is None and hasattr(GPBenchConfig, "model_code") and model_code:
            q = GPBenchConfig.query.filter_by(model_code=model_code)
        if q is None:
            # ⚠️ Importante: se não conseguimos filtrar por modelo, NÃO traga a tabela inteira.
            # Em vez disso, volte para o fallback-seguro: b5/b8 e fim.
            return ["b5", "b8"]

        if hasattr(GPBenchConfig, "bench_num"):
            q = q.order_by(GPBenchConfig.bench_num.asc())
        elif hasattr(GPBenchConfig, "bench"):
            q = q.order_by(GPBenchConfig.bench.asc())
        elif hasattr(GPBenchConfig, "bench_id"):
            q = q.order_by(GPBenchConfig.bench_id.asc())

        configs = q.all() or []
    except Exception:
        return ["b5", "b8"]

    enabled: List[str] = []
    for c in configs:
        key = None
        if hasattr(c, "bench_id") and getattr(c, "bench_id"):
            key = str(getattr(c, "bench_id")).lower()
        elif hasattr(c, "bench") and getattr(c, "bench") is not None:
            b = getattr(c, "bench")
            key = f"b{int(b)}" if f"{b}".isdigit() else f"b{str(b).lower().lstrip('b')}"
        elif hasattr(c, "bench_num"):
            key = f"b{getattr(c, 'bench_num')}"
        if not key:
            continue

        if hasattr(c, "ativo"):
            is_enabled = bool(getattr(c, "ativo"))
        elif hasattr(c, "enabled"):
            is_enabled = bool(getattr(c, "enabled"))
        elif hasattr(c, "habilitar"):
            is_enabled = bool(getattr(c, "habilitar"))
        else:
            is_enabled = True

        if is_enabled and key.startswith("b") and key[1:].isdigit():
            enabled.append(f"b{int(key[1:])}")

    if "b5" not in enabled:
        enabled.append("b5")
    if "b8" not in enabled:
        enabled.append("b8")

    return sorted(set(enabled), key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)


def _next_bench_for_order(order: GPWorkOrder, from_bench: Optional[str]) -> str:
    seq = _benches_enabled_for_order(order)
    if not seq:
        return "final"
    if not from_bench or from_bench in TECH_COLUMNS:
        return seq[0]
    if from_bench not in seq:
        return seq[0]
    idx = seq.index(from_bench)
    return seq[idx + 1] if idx + 1 < len(seq) else "final"


# ============================================================
# BLOCO 6 — Helpers de banco (buscar/abrir/fechar stages)
# ============================================================
def _get_order_by_serial(serial: str) -> Optional[GPWorkOrder]:
    return GPWorkOrder.query.filter_by(serial=serial).first()


def _find_open_stage(order_id: int, bench_id: str) -> Optional[GPWorkStage]:
    return (
        GPWorkStage.query.filter_by(
            order_id=order_id, bench_id=bench_id, finished_at=None
        )
        .order_by(GPWorkStage.started_at.desc())
        .first()
    )


def _get_last_b5_stage(order_id: int) -> Optional[GPWorkStage]:
    return (
        GPWorkStage.query.filter_by(order_id=order_id, bench_id="b5")
        .order_by(GPWorkStage.finished_at.desc(), GPWorkStage.started_at.desc())
        .first()
    )


def _open_stage(order: GPWorkOrder, bench_id: str, operador: str = "") -> GPWorkStage:
    stg = GPWorkStage(order_id=order.id, bench_id=bench_id, operador=operador or "")
    stg.started_at = datetime.utcnow()
    db.session.add(stg)
    order.current_bench = bench_id
    return stg


def _finish_stage(order: GPWorkOrder, stage: GPWorkStage) -> str:
    stage.finished_at = datetime.utcnow()
    next_b = _next_bench_for_order(order, stage.bench_id)
    order.current_bench = next_b
    return next_b


# ============================================================
# BLOCO 7 — B5 (debounce)
# ============================================================
def _b5_is_locked(order: GPWorkOrder) -> Tuple[bool, Optional[dict]]:
    ultimo_status = (order.hipot_status or "").upper()
    if ultimo_status not in ("OK", "APR"):
        return False, None
    last_b5 = _get_last_b5_stage(order.id)
    if not (last_b5 and last_b5.finished_at):
        return False, None
    finished_at = last_b5.finished_at
    if getattr(finished_at, "tzinfo", None) is not None:
        finished_at = finished_at.replace(tzinfo=None)
    now = datetime.utcnow()
    delta = now - finished_at
    if delta >= timedelta(minutes=REOPEN_LOCK_MIN):
        return False, None
    remaining = timedelta(minutes=REOPEN_LOCK_MIN) - delta
    rem_min = int(remaining.total_seconds() // 60) + 1
    passed_min = max(0, int(delta.total_seconds() // 60))
    resp = {
        "serial": order.serial,
        "bench": "b5",
        "stage_opened": False,
        "locked": True,
        "locked_minutes_left": rem_min,
        "say": (
            f"HiPot aprovado ha {passed_min} min. "
            f"Aguarde ~{rem_min} min para reabrir. "
            f"Para retestar agora, registre REP."
        ),
    }
    return True, resp


# ============================================================
# BLOCO 8 — Integração (bench_flow_service) com fallback
# ============================================================
def _flow_set_current_bench_on_scan(session, serial: str, bench: str) -> Dict[str, str]:
    try:
        from app.services.producao.bench_flow_service import (
            set_current_bench_on_scan as _svc_set,
        )

        return _svc_set(session, serial, bench)
    except Exception as e:
        # Fallback local: posiciona na bancada (respeitando roteiro) e garante etapa
        order = GPWorkOrder.query.filter_by(serial=serial).first()
        if not order:
            return {"ok": "false", "error": "order_not_found", "hint": str(e)}
        seq = _benches_enabled_for_order(order)
        if bench not in seq and bench not in TECH_COLUMNS:
            bench = seq[0] if seq else "final"
        order.current_bench = bench
        if bench not in TECH_COLUMNS:
            stg = _find_open_stage(order.id, bench)
            if not stg:
                stg = GPWorkStage(
                    order_id=order.id, bench_id=bench, started_at=datetime.utcnow()
                )
                session.add(stg)
        session.commit()
        return {"ok": "true", "current_bench": bench, "fallback": True}


def _flow_advance_after_finish(session, serial: str) -> Dict[str, str]:
    try:
        from app.services.producao.bench_flow_service import (
            advance_after_finish as _svc_adv,
        )

        return _svc_adv(session, serial)
    except Exception as e:
        order = GPWorkOrder.query.filter_by(serial=serial).first()
        if not order:
            return {"ok": "false", "error": "order_not_found", "hint": str(e)}
        nxt = _next_bench_for_order(order, order.current_bench)
        order.current_bench = nxt
        session.commit()
        return {"ok": "true", "current_bench": nxt, "fallback": True}


# ============================================================
# BLOCO 9 — Rotas
# ============================================================
@gp_painel_scan_api_bp.route("/scan-b5", methods=["POST"])
def scan_b5():
    # Shim de compatibilidade: processa como /scan
    return scan_generic()


@gp_painel_scan_api_bp.route("/scan", methods=["POST"])
def scan_generic():
    """
    Rota generica para scan de qualquer bancada (usada pelo board.html).

    Regras (toggle):
      - 1o scan na bancada: abre etapa e seta current_bench.
      - 2o scan na mesma bancada: fecha etapa e avanca para a proxima pelo roteiro.

    Tambem aceita action explicito: "start" / "finish".
    """
    try:
        if not request.is_json:
            return _json_error(
                400,
                error="content_type_invalido",
                message="Conteudo deve ser application/json.",
            )

        data = request.get_json(silent=True) or {}
        raw_scan = (data.get("raw_scan") or "").strip()
        serial = (data.get("serial") or "").strip()
        bench_id = (data.get("bench") or data.get("bench_id") or "").strip().lower()
        action = (data.get("action") or "").strip().lower()
        operador = (data.get("operador") or "").strip()
        station = (data.get("station") or data.get("workstation") or "").strip()
        say = ""

        if raw_scan:
            parsed_bench, parsed_serial = _parse_scan(raw_scan)
            if parsed_serial:
                serial = parsed_serial
            if parsed_bench:
                bench_id = parsed_bench

        if not serial:
            return _json_error(400, error="payload_invalido", message="Serial ausente.")

        order = _get_order_by_serial(serial)
        if not order:
            return _json_error(
                404,
                error="serial_nao_encontrado",
                message=f"Serial {serial} nao encontrado.",
            )

        # Roteiro ativo do modelo — preferir serviço central
        try:
            from app.services.producao.bench_flow_service import (
                route_for_model as _route_for_model,
            )

            model_code = getattr(order, "modelo", "") or getattr(
                order, "model_code", ""
            )
            seq = _route_for_model(model_code) or []
        except Exception:
            seq = _benches_enabled_for_order(order) or []

        bench = (
            bench_id or order.current_bench or (seq[0] if seq else "final")
        ).lower()

        # Realinhamento automatico se fora do roteiro
        original_bench = bench
        if bench not in seq and bench not in TECH_COLUMNS:
            bench = seq[0] if seq else "final"
            say = f"Lido {original_bench.upper()} fora do roteiro. Redirecionado para {bench.upper()}."

        # Status
        if order.status not in ("in_progress", "queued"):
            order.status = "in_progress"

        # Toggle
        open_stage = _find_open_stage(order.id, bench)
        if action not in ("start", "finish"):
            action = "finish" if open_stage else "start"

        did_start = False
        did_finish = False
        bench_done = None

        if action == "start":
            if bench == "b5":
                locked, resp_locked = _b5_is_locked(order)
                if locked:
                    return _json_ok(**resp_locked)

            # Colunas tecnicas nao recebem etapas
            if bench in TECH_COLUMNS:
                say += " Esta coluna nao recebe etapas. Direcione para uma bancada habilitada."
                order.current_bench = _next_bench_for_order(order, "sep")
                db.session.add(order)
                db.session.commit()
                return _json_ok(
                    serial=order.serial,
                    bench_id=order.current_bench,
                    toggled_action="noop",
                    started=False,
                    finished=False,
                    say=say.strip(),
                )

            # Fecha outras etapas abertas (consistencia)
            others = GPWorkStage.query.filter(
                GPWorkStage.order_id == order.id,
                GPWorkStage.finished_at.is_(None),
                GPWorkStage.bench_id != bench,
            ).all()
            for st in others:
                st.finished_at = datetime.utcnow()

            # Integra com servico (ou fallback)
            rv_flow = _flow_set_current_bench_on_scan(db.session, serial, bench)
            if rv_flow.get("ok") != "true":
                db.session.rollback()
                return jsonify(rv_flow), 400
            bench = rv_flow.get("current_bench") or bench

            # Recheca para evitar duplicidade
            open_stage = _find_open_stage(order.id, bench)
            if not open_stage:
                new_stage = _open_stage(order, bench, operador)
                if station:
                    try:
                        new_stage.workstation = station
                        db.session.add(new_stage)
                    except Exception as e:
                        logger.debug(f"[scan] could not set workstation: {e}")

            did_start = True
            say += f" Inicio registrado na {bench.upper()}."

        elif action == "finish":
            # Realinha antes de finalizar
            if bench not in seq and bench not in TECH_COLUMNS:
                bench = order.current_bench or (seq[0] if seq else "final")

            open_stage = _find_open_stage(order.id, bench)
            if open_stage:
                result = (data.get("result") or "OK").strip().upper()
                if result not in ("OK", "FAIL", "APR", "REP"):
                    result = "OK"
                try:
                    open_stage.result = result
                    open_stage.rework_flag = bool(data.get("rework") or False)
                    if station:
                        open_stage.workstation = station
                    db.session.add(open_stage)
                except Exception as e:
                    logger.debug(f"[scan] set result/rework/ws failed: {e}")

                _finish_stage(order, open_stage)
                _flow_advance_after_finish(db.session, serial)
                next_b = order.current_bench

                did_finish = True
                bench_done = bench
                say += f" Etapa finalizada na {bench.upper()}. Mover para {next_b.upper()}."
            else:
                if not order.current_bench:
                    order.current_bench = bench
                say += f" Nao havia etapa aberta na {bench.upper()}. Faca o scan para iniciar."

        db.session.add(order)
        db.session.commit()

        resp = {
            "serial": order.serial,
            "bench_id": order.current_bench,
            "toggled_action": action,
            "started": did_start,
            "finished": did_finish,
            "say": say.strip(),
        }
        if did_finish:
            resp["bench_done"] = bench_done
            resp["moved_to"] = order.current_bench
            resp["modelo"] = getattr(order, "modelo", "")
            resp["operador"] = operador
            if order.current_bench == "final":
                try:
                    if getattr(order, "finished_at", None) is None:
                        order.finished_at = datetime.utcnow()
                        db.session.add(order)
                except Exception as e:
                    logger.debug(f"[scan] could not set finished_at: {e}")
                resp["final_message"] = {
                    "titulo": "Montagem concluida",
                    "mensagem": f"{getattr(order, 'modelo', '')} - {order.serial}",
                    "modelo": getattr(order, "modelo", ""),
                    "serial": order.serial,
                    "operador": operador,
                }

        return _json_ok(**resp)

    except Exception as e:
        import traceback

        db.session.rollback()
        traceback.print_exc()
        return _json_error(
            500,
            error="exception_scan",
            message="Falha interna ao processar o scan na rota /scan.",
            hint=str(e),
            context={"route": "/producao/gp/painel/api/scan"},
        )


# ============================================================
# BLOCO 10 — Rotas de Debug
# ============================================================
@gp_painel_scan_api_bp.route("/debug/stages/<serial>", methods=["GET"])
def debug_stages(serial):
    order = _get_order_by_serial(serial)
    if not order:
        return jsonify({"ok": False, "error": f"serial nao encontrado: {serial}"}), 404

    stages = (
        GPWorkStage.query.filter_by(order_id=order.id)
        .order_by(GPWorkStage.started_at)
        .all()
    )

    def _dt(x):
        return x.isoformat() if x else None

    return _json_ok(
        serial=order.serial,
        stages=[
            {
                "bench_id": s.bench_id,
                "started_at": _dt(s.started_at),
                "finished_at": _dt(s.finished_at),
                "operador": s.operador or "",
            }
            for s in stages
        ],
    )


@gp_painel_scan_api_bp.route("/debug/bench/<serial>", methods=["GET"])
def debug_current_bench(serial):
    order = _get_order_by_serial(serial)
    if not order:
        return jsonify({"ok": False, "error": f"serial nao encontrado: {serial}"}), 404
    return _json_ok(
        serial=order.serial, current_bench=order.current_bench, status=order.status
    )
