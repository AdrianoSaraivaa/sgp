# app/routes/producao_routes/gerenciamento_producao_routes/gp_painel_scan_api.py
from __future__ import annotations

"""
Versão refatorada em BLOCOS (revisada v4b).
- Rota genérica /scan controla TODAS as bancadas (inclusive B5).
- BLOCO 5 agnóstico ao schema (model_id/model_code).
- BLOCO 8 é shim: /scan-b5 -> scan_generic().
- Toggle start/finish com timer iniciando no primeiro scan.
- FIX: GPWorkStage não aceita 'order' no construtor → usar order_id=order.id.
- FIX v4b: resposta do FINISH monta dict e faz `_json_ok(**resp)` (evita
  'got multiple values for keyword argument serial').
"""

# ============================================================
# BLOCO 1 — Imports e Blueprint
# ============================================================
import re
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
import json

from flask import Blueprint, request, jsonify
from app import db
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage

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

# Trava de reabertura da B5 após aprovação (minutos) — mantida para uso futuro
REOPEN_LOCK_MIN = 10

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
# BLOCO 5 — Fluxo pelo Setup (GPBenchConfig)  [PATCHADO]
# ============================================================
def _benches_enabled_for_order(order) -> List[str]:
    """
    Retorna a sequência de bancadas habilitadas para o modelo da ordem,
    independente de o schema usar model_id ou model_code.
    Normaliza sempre em ["b1","b2",...]. Garante "b5" e "b8".
    """
    fallback_seq = [f"b{i}" for i in range(1, 9)]

    try:
        from app import db as _db
        from app.models.producao_models.gp_modelos import GPBenchConfig, GPModel  # noqa
    except Exception as e:
        print("[SCAN] GPBenchConfig/GPModel indisponíveis:", repr(e))
        seq = fallback_seq
        if "b5" not in seq: seq.append("b5")
        if "b8" not in seq: seq.append("b8")
        return sorted(set(seq), key=lambda k: int(str(k).lstrip("b")) if str(k).lstrip("b").isdigit() else 999)

    model_code = (
        getattr(order, "model_code", None)
        or getattr(order, "modelo", None)
        or getattr(getattr(order, "model", None), "code", None)
        or getattr(getattr(order, "model", None), "modelo", None)
    )
    model_id = getattr(order, "model_id", None) or getattr(getattr(order, "model", None), "id", None)

    q = None
    try:
        if hasattr(GPBenchConfig, "model_id") and (model_id or model_code):
            if model_id:
                q = _db.session.query(GPBenchConfig).filter(GPBenchConfig.model_id == model_id)
            elif model_code and hasattr(GPModel, "code"):
                q = (
                    _db.session.query(GPBenchConfig)
                    .join(GPModel, GPBenchConfig.model_id == GPModel.id)
                    .filter(GPModel.code == model_code)
                )

        if q is None and hasattr(GPBenchConfig, "model_code") and model_code:
            q = GPBenchConfig.query.filter_by(model_code=model_code)

        if q is None:
            q = _db.session.query(GPBenchConfig)

        if hasattr(GPBenchConfig, "bench_num"):
            q = q.order_by(GPBenchConfig.bench_num.asc())
        elif hasattr(GPBenchConfig, "bench"):
            q = q.order_by(GPBenchConfig.bench.asc())

        configs = q.all() or []
    except Exception as e:
        print("[SCAN] Falha ao consultar GPBenchConfig:", repr(e))
        configs = []

    enabled: List[str] = []
    for c in configs:
        # Identificar a bancada
        key = None
        if hasattr(c, "bench_id") and getattr(c, "bench_id"):
            key = str(getattr(c, "bench_id")).lower()
        elif hasattr(c, "bench") and getattr(c, "bench") is not None:
            b = getattr(c, "bench")
            key = f"b{int(b)}" if isinstance(b, int) or str(b).isdigit() else f"b{str(b).lower().lstrip('b')}"
        elif hasattr(c, "bench_num"):
            key = f"b{getattr(c, 'bench_num')}"

        if not key:
            continue

        # Habilitação
        is_enabled = bool(
            getattr(c, "enabled", None)
            if hasattr(c, "enabled")
            else getattr(c, "habilitar", True)
        )

        if is_enabled and key.startswith("b") and str(key[1:]).isdigit():
            enabled.append(f"b{int(str(key[1:]))}")  # normaliza "b05" → "b5"

    if not enabled:
        enabled = list(fallback_seq)

    if "b5" not in enabled: enabled.append("b5")
    if "b8" not in enabled: enabled.append("b8")

    enabled = sorted(set(enabled), key=lambda k: int(str(k).lstrip("b")) if str(k).lstrip("b").isdigit() else 999)
    return enabled

def _next_bench_for_order(order, from_bench: Optional[str]) -> str:
    """
    Dada a bancada atual, retorna a próxima habilitada pelo Setup.
    - Se from_bench não estiver na lista, vai para a primeira habilitada.
    - Se já for a última, retorna 'final'.
    - Se a ordem estiver em 'sep' (estoque) ou None, retorna a primeira habilitada.
    """
    seq = _benches_enabled_for_order(order)

    if not seq:
        return "final"

    if not from_bench or from_bench == "sep":
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
        GPWorkStage.query
        .filter_by(order_id=order_id, bench_id=bench_id, finished_at=None)
        .order_by(GPWorkStage.started_at.desc())
        .first()
    )

def _get_last_b5_stage(order_id: int) -> Optional[GPWorkStage]:
    return (
        GPWorkStage.query
        .filter_by(order_id=order_id, bench_id="b5")
        .order_by(GPWorkStage.finished_at.desc(), GPWorkStage.started_at.desc())
        .first()
    )

def _open_stage(order: GPWorkOrder, bench_id: str, operador: str = "") -> GPWorkStage:
    # FIX: construtor deve receber order_id, não 'order'
    stage = GPWorkStage(order_id=order.id, bench_id=bench_id, operador=operador or "")
    stage.started_at = datetime.utcnow()  # IMPORTANTE para o timer
    db.session.add(stage)
    order.current_bench = bench_id
    return stage

def _finish_stage(order: GPWorkOrder, stage: GPWorkStage) -> str:
    stage.finished_at = datetime.utcnow()
    next_b = _next_bench_for_order(order, stage.bench_id)
    order.current_bench = next_b
    return next_b

# ============================================================
# BLOCO 7 — (mantido) Regras especiais B5 (debounce) — não usado pelo shim
# ============================================================
def _b5_is_locked(order: GPWorkOrder) -> Tuple[bool, Optional[dict]]:
    """Retorna (locked, resposta_json) — se locked=True, resposta_json já vem pronta."""
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
            f"HiPot aprovado há {passed_min} min. "
            f"Aguarde ~{rem_min} min para reabrir. "
            f"Para retestar agora, registre REP."
        ),
    }
    return True, resp

# ============================================================
# BLOCO 8 — Rota específica: /scan-b5  [SHIM → usa a genérica]
# ============================================================
@gp_painel_scan_api_bp.route("/scan-b5", methods=["POST"])
def scan_b5():
    # Compatibilidade temporária: processa exatamente como /scan
    return scan_generic()

# ============================================================
# BLOCO 9 — Rota genérica: /scan (toggle/start/finish)
# ============================================================
print("scan_generic entrou")
print("scan_generic entrou — DIAG")

@gp_painel_scan_api_bp.route("/scan", methods=["POST"])
def scan_generic():
    """
    Rota genérica para scan de qualquer bancada (usada pelo board.html).

    Regras (modo “toggle”):
      - 1º scan na bancada: abre stage (started_at=utcnow) e coloca current_bench = bancada.
      - 2º scan na mesma bancada: fecha stage (finished_at=utcnow) e avança current_bench pelo Setup.

    Também aceita serial/bench/action explícitos:
      - action = "start"  → força iniciar/confirmar a abertura
      - action = "finish" → força finalizar (se houver etapa aberta)
      - action vazio      → modo toggle automático
    """
    try:
        if not request.is_json:
            return _json_error(
                400,
                error="content_type_invalido",
                message="Conteúdo deve ser application/json.",
            )
        
        data = request.get_json(silent=True) or {}

        raw_scan = (data.get("raw_scan") or "").strip()
        serial   = (data.get("serial") or "").strip()
        bench_id = (data.get("bench") or data.get("bench_id") or "").strip().lower()
        action   = (data.get("action") or "").strip().lower()
        operador = (data.get("operador") or "").strip()

        # Se veio raw_scan, tenta parsear
        if raw_scan:
            parsed_bench, parsed_serial = _parse_scan(raw_scan)
            if parsed_serial:
                serial = parsed_serial
            if parsed_bench:
                bench_id = parsed_bench

        if not serial:
            return _json_error(400, error="payload_invalido", message="Serial ausente.")

        # Busca ordem
        order = _get_order_by_serial(serial)
        if not order:
            return _json_error(404, error="serial_nao_encontrado", message=f"Serial {serial} não encontrado.")

        # Bancada alvo: informada → atual → primeira do Setup
        seq = _benches_enabled_for_order(order) or []
        bench = (bench_id or order.current_bench or (seq[0] if seq else "final"))
        bench = str(bench).lower()
        print("[DBG] /scan vars:", {"serial": serial, "bench": bench, "action": action, "seq": seq})

        # Realinha se a bancada não estiver no Setup habilitado
        if bench not in seq and bench not in ("sep", "final"):
            bench = seq[0] if seq else "final"

        # Garante status em progresso
        if order.status not in ("in_progress", "queued"):
            order.status = "in_progress"

        # Verifica se há stage aberto nessa bancada
        open_stage = _find_open_stage(order.id, bench)
        print("[DBG] /scan open_stage:", bool(open_stage), "order_id=", order.id, "bench=", bench)

        say = ""
        did_start = False
        did_finish = False
        bench_done = None

        # Toggle automático se não veio action
        if action not in ("start", "finish"):
            action = "finish" if open_stage else "start"

        if action == "start":
            print("[DBG] /scan START for", bench)
            # Impede abrir etapa em colunas técnicas
            if bench in ("sep", "final"):
                say = "Esta coluna não recebe etapas. Direcione para uma bancada habilitada."
                order.current_bench = _next_bench_for_order(order, "sep")
                db.session.add(order)
                db.session.commit()
                resp = {
                    "serial": order.serial,
                    "bench_id": order.current_bench,
                    "toggled_action": "noop",
                    "started": False,
                    "finished": False,
                    "say": say,
                }
                return _json_ok(**resp)

            # Reposiciona se a bancada não faz parte do Setup
            if bench not in seq:
                bench = seq[0] if seq else "final"
                open_stage = _find_open_stage(order.id, bench)

            if open_stage:
                if operador and not getattr(open_stage, "operador", ""):
                    open_stage.operador = operador
                order.current_bench = bench
                say = f"Etapa já aberta na {bench}. Continue o trabalho."
            else:
                # Fecha qualquer outra etapa aberta, se houver (consistência)
                other_open = (
                    GPWorkStage.query
                    .filter(
                        GPWorkStage.order_id == order.id,
                        GPWorkStage.finished_at.is_(None),
                        GPWorkStage.bench_id != bench,
                    )
                    .all()
                )
                for st in other_open:
                    st.finished_at = datetime.utcnow()

                _open_stage(order, bench, operador)  # started_at = utcnow (timer)
                did_start = True
                say = f"Início registrado na {bench}."

        elif action == "finish":
            print("[DBG] /scan FINISH for", bench, "open?", bool(open_stage))
            if open_stage:
                next_b = _finish_stage(order, open_stage)
                did_finish = True
                bench_done = bench
                say = f"Etapa finalizada na {bench}. Mover para {next_b}."
            else:
                if not order.current_bench:
                    order.current_bench = bench
                say = f"Não havia etapa aberta na {bench}. Faça o scan para iniciar."

        db.session.add(order)
        db.session.commit()

        # ----- MONTA RESPOSTA (evita duplicidade de kwargs) -----
        resp = {
            "serial": order.serial,
            "bench_id": order.current_bench,
            "toggled_action": action,
            "started": did_start,
            "finished": did_finish,
            "say": say,
        }
        if did_finish:
            resp["bench_done"] = bench_done
            resp["moved_to"] = order.current_bench
            resp["modelo"] = getattr(order, "modelo", "")
            resp["operador"] = operador

            if order.current_bench == "final":
                resp["final_message"] = {
                    "titulo": "Montagem concluída",
                    "mensagem": f"{getattr(order, 'modelo', '')} • {order.serial}",
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
    """DEBUG: lista as etapas (stages) do serial, mostrando started/finished."""
    order = _get_order_by_serial(serial)
    if not order:
        return jsonify({"ok": False, "error": f"serial não encontrado: {serial}"}), 404

    stages = (
        GPWorkStage.query
        .filter_by(order_id=order.id)
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
        return jsonify({"ok": False, "error": f"serial não encontrado: {serial}"}), 404
    return _json_ok(
        serial=order.serial,
        current_bench=order.current_bench,
        status=order.status,
    )
