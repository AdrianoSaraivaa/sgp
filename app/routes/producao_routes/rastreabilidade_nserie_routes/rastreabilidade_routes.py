# app/routes/producao_routes/rastreabilidade_nserie_routes/rastreabilidade_routes.py
from __future__ import annotations

"""
Rotas de Rastreabilidade por Nº de Série (SGP)
- Protegidas por uma senha simples de sessão (SESSION_KEY).
- Páginas: home, senha, detalhes.
- APIs: /rastreabilidade/api/search  e  /rastreabilidade/api/<serial>
"""

from datetime import datetime
from typing import Optional, Any, Dict, List

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from app import db

# ------------------------------------------------------------------------------
# Blueprint primeiro (evita falhas por imports posteriores)
# ------------------------------------------------------------------------------
gp_rastreabilidade_bp = Blueprint(
    "gp_rastreabilidade_bp",
    __name__,
    url_prefix="/producao/gp",
)

# ------------------------------------------------------------------------------
# Imports de modelos: sempre protegidos para NUNCA quebrar o import do módulo
# ------------------------------------------------------------------------------
# Ordem / Estágios
GPWorkOrder = None  # type: ignore
GPWorkStage = None  # type: ignore
try:
    from app.models.producao_models.gp_execucao import GPWorkOrder as _WO, GPWorkStage as _WS  # type: ignore

    GPWorkOrder, GPWorkStage = _WO, _WS
except Exception:
    try:
        from app.models.producao_models.gp_execucao import GPWorkOrder as _WO  # type: ignore

        GPWorkOrder = _WO
    except Exception:
        pass  # continua com None; handlers checam None

# Configuração de habilitação por bancada
GPBenchConfig = None  # type: ignore
try:
    from app.models.producao_models.gp_modelos import GPBenchConfig as _BC  # type: ignore

    GPBenchConfig = _BC
except Exception:
    pass

# HiPot (preferir GPHipotRun; cair para GPHipotResult)
GPHipotRun = None  # type: ignore
try:
    from app.models.producao_models.gp_hipot import GPHipotRun as _HR  # type: ignore

    GPHipotRun = _HR
except Exception:
    try:
        from app.models.producao_models.gp_hipot import GPHipotResult as _HR  # type: ignore

        GPHipotRun = _HR
    except Exception:
        pass

# Checklist (preferir Execution/Item)
GPChecklistExecution = None  # type: ignore
GPChecklistExecutionItem = None  # type: ignore
try:
    from app.models.producao_models.gp_checklist import (  # type: ignore
        GPChecklistExecution as _CE,
        GPChecklistExecutionItem as _CEI,
    )

    GPChecklistExecution, GPChecklistExecutionItem = _CE, _CEI
except Exception:
    try:
        from app.models.producao_models.gp_checklist import (  # type: ignore
            GPChecklistExec as _CE,
            GPChecklistItemLog as _CEI,
        )

        GPChecklistExecution, GPChecklistExecutionItem = _CE, _CEI
    except Exception:
        pass

# ------------------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------------------
SESSION_KEY = "rastreamento_ok"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _is_authed() -> bool:
    return bool(session.get(SESSION_KEY))


def _require_auth_redirect():
    if not _is_authed():
        return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_senha"))
    return None


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _parse_page_size(raw: Any) -> int:
    size = max(_parse_int(raw, DEFAULT_PAGE_SIZE), 1)
    return min(size, MAX_PAGE_SIZE)


def _parse_date_yyyy_mm_dd(raw: str) -> Optional[datetime]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        return None


def _end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def _fmt_dt_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def _safe_int_minutes(
    started_at: Optional[datetime], finished_at: Optional[datetime]
) -> Optional[int]:
    if started_at and finished_at:
        try:
            return int((finished_at - started_at).total_seconds() // 60)
        except Exception:
            return None
    return None


# ------------------------------------------------------------------------------
# Views (HTML)
# ------------------------------------------------------------------------------
@gp_rastreabilidade_bp.route("/rastreabilidade/", methods=["GET"])
def rastreabilidade_home():
    if (redir := _require_auth_redirect()) is not None:
        return redir
    # CORREÇÃO: Apontando para o arquivo correto e atualizado
    return render_template(
        "producao_templates/rastreabilidade_templates/relatorio_rastreamento.html"
    )


@gp_rastreabilidade_bp.route("/rastreabilidade/senha", methods=["GET", "POST"])
def rastreabilidade_senha():
    if request.method == "POST":
        submitted = (request.form.get("senha") or "").strip()
        if submitted.lower() == "sgp":
            session[SESSION_KEY] = True
            return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_home"))
        flash("Senha incorreta. Tente novamente.", "error")
    return render_template(
        "producao_templates/rastreabilidade_templates/senha_rastreamento.html"
    )


@gp_rastreabilidade_bp.route("/rastreabilidade/sair", methods=["POST"])
def rastreabilidade_sair():
    session.pop(SESSION_KEY, None)
    return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_senha"))


@gp_rastreabilidade_bp.route("/rastreabilidade/<serial>", methods=["GET"])
def rastreabilidade_detalhes(serial: str):
    if (redir := _require_auth_redirect()) is not None:
        return redir
    return render_template(
        "producao_templates/rastreabilidade_templates/detalhes_rastreamento.html",
        serial=serial,
    )


# ------------------------------------------------------------------------------
# APIs
# ------------------------------------------------------------------------------
@gp_rastreabilidade_bp.route("/rastreabilidade/api/search", methods=["GET"])
def rastreabilidade_api_search():
    if not _is_authed():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    serial = (request.args.get("serial") or "").strip()
    modelo = (request.args.get("modelo") or "").strip()
    status = (request.args.get("status") or "").strip()
    data_ini = (request.args.get("data_ini") or "").strip()
    data_fim = (request.args.get("data_fim") or "").strip()
    page = max(_parse_int(request.args.get("page", 1), 1), 1)
    page_size = _parse_page_size(request.args.get("page_size", DEFAULT_PAGE_SIZE))

    # Se modelo não está disponível, devolve lista vazia de forma segura
    if GPWorkOrder is None:
        return jsonify(
            {"ok": True, "page": page, "page_size": page_size, "total": 0, "items": []}
        )

    q = db.session.query(GPWorkOrder)

    if serial:
        q = q.filter(GPWorkOrder.serial.ilike(f"%{serial}%"))
    if modelo:
        q = q.filter(GPWorkOrder.modelo.ilike(f"%{modelo}%"))
    if status:
        q = q.filter(GPWorkOrder.status == status)

    dt_ini = _parse_date_yyyy_mm_dd(data_ini)
    dt_fim = _parse_date_yyyy_mm_dd(data_fim)
    if dt_ini:
        q = q.filter(GPWorkOrder.updated_at >= dt_ini)
    if dt_fim:
        q = q.filter(GPWorkOrder.updated_at <= _end_of_day(dt_fim))

    q = q.order_by(GPWorkOrder.updated_at.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    data: List[Dict[str, Any]] = []
    for o in items:
        data.append(
            {
                "modelo": getattr(o, "modelo", None),
                "serial": getattr(o, "serial", None),
                "status": getattr(o, "status", None),
                "ultima_atualizacao": _fmt_dt_iso(getattr(o, "updated_at", None)),
                "current_bench": getattr(o, "current_bench", None),
            }
        )

    return jsonify(
        {
            "ok": True,
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": data,
        }
    )


@gp_rastreabilidade_bp.route("/rastreabilidade/api/<serial>", methods=["GET"])
def rastreabilidade_api_detalhe(serial: str):
    if not _is_authed():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    if GPWorkOrder is None:
        return jsonify({"ok": False, "error": "model_missing"}), 500

    work_order = (
        db.session.query(GPWorkOrder).filter(GPWorkOrder.serial == str(serial)).first()
    )
    if not work_order:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "not_found",
                    "message": f"Serial {serial} não encontrado",
                }
            ),
            404,
        )

    payload: Dict[str, Any] = {
        "serial": getattr(work_order, "serial", None),
        "modelo": getattr(work_order, "modelo", None),
        "lote": getattr(work_order, "lote", None),
        "ordem_producao": getattr(work_order, "id", None),
        "criado_em": _fmt_dt_iso(getattr(work_order, "created_at", None)),
        "criado_por": getattr(work_order, "created_by", None),
        "status_atual": getattr(work_order, "status", None),
        "current_bench": getattr(work_order, "current_bench", None),
        "ultima_atualizacao": _fmt_dt_iso(getattr(work_order, "updated_at", None)),
    }

    # Bancadas
    payload["bancadas"] = []
    stages: List[Any] = []
    if GPWorkStage is not None:
        try:
            stages = (
                db.session.query(GPWorkStage)
                .filter(getattr(GPWorkStage, "order_id") == getattr(work_order, "id"))
                .order_by(getattr(GPWorkStage, "started_at").asc())
                .all()
            )
        except Exception:
            stages = []

    # Mapa de habilitação (opcional)
    enabled_map: Dict[int, bool] = {}
    if GPBenchConfig and payload.get("modelo"):
        try:
            cfgs = (
                db.session.query(GPBenchConfig)
                .filter(getattr(GPBenchConfig, "modelo") == payload["modelo"])
                .all()
            )
            for cfg in cfgs:
                bench_id = getattr(cfg, "bench_id", None)
                if bench_id is not None:
                    enabled_map[int(bench_id)] = bool(getattr(cfg, "enabled", True))
        except Exception:
            enabled_map = {}

    for i in range(1, 9):
        stg = None
        for s in stages or []:
            s_bid = getattr(s, "bench_id", None)
            if isinstance(s_bid, str) and s_bid.lower() == f"b{i}":
                stg = s
                break
            if isinstance(s_bid, (int,)) and s_bid == i:
                stg = s
                break

        started_at = getattr(stg, "started_at", None) if stg else None
        finished_at = getattr(stg, "finished_at", None) if stg else None
        payload["bancadas"].append(
            {
                "bench_id": i,
                "nome": f"Bancada {i}",
                "habilitada": enabled_map.get(i, True),
                "inicio": _fmt_dt_iso(started_at),
                "fim": _fmt_dt_iso(finished_at),
                "duracao_min": _safe_int_minutes(started_at, finished_at),
                "responsavel": getattr(stg, "operador", None) if stg else None,
                "ocorrencias": [],
            }
        )

    # HiPot — último run
    if GPHipotRun is not None:
        try:
            last_hipot = (
                db.session.query(GPHipotRun)
                .filter(getattr(GPHipotRun, "serial") == str(serial))
                .order_by(getattr(GPHipotRun, "started_at").desc())
                .first()
            )
        except Exception:
            last_hipot = None
    else:
        last_hipot = None

    if last_hipot:
        gb_ok = getattr(last_hipot, "gb_ok", None)
        hp_ok = getattr(last_hipot, "hp_ok", None)
        final_ok = getattr(last_hipot, "final_ok", None)
        payload["hipot"] = {
            "executado": True,
            "equipamento": getattr(last_hipot, "equipamento", None),
            "calibracao": getattr(last_hipot, "calibracao", None),
            "gb1": {
                "valor": (
                    getattr(last_hipot, "gb_r_mohms", None)
                    or getattr(last_hipot, "gb_r_mohm", None)
                    or getattr(last_hipot, "gb_valor", None)
                ),
                "status": "ok" if gb_ok else "nao" if gb_ok is not None else None,
            },
            "hp1": {
                "valor": (
                    getattr(last_hipot, "hp_v_obs_v", None)
                    or getattr(last_hipot, "hp_v", None)
                    or getattr(last_hipot, "hp_valor", None)
                ),
                "status": "ok" if hp_ok else "nao" if hp_ok is not None else None,
            },
            "resultado_final": (
                "ok" if final_ok else "nao" if final_ok is not None else None
            ),
            "observacao_reprovacao": getattr(last_hipot, "observacoes", None),
        }
    else:
        payload["hipot"] = {
            "executado": False,
            "equipamento": None,
            "calibracao": None,
            "gb1": None,
            "hp1": None,
            "resultado_final": None,
            "observacao_reprovacao": None,
        }

    # Checklist
    checklist_payload: Dict[str, Any] = {
        "executado": False,
        "itens": [],
        "resultado_final": None,
    }
    if GPChecklistExecution is not None:
        try:
            execs = (
                db.session.query(GPChecklistExecution)
                .filter(getattr(GPChecklistExecution, "serial") == str(serial))
                .order_by(getattr(GPChecklistExecution, "started_at").asc())
                .all()
            )
        except Exception:
            execs = []
        if execs:
            last = execs[-1]
            items = []
            if GPChecklistExecutionItem is not None:
                try:
                    if hasattr(GPChecklistExecutionItem, "exec_id"):
                        items = (
                            db.session.query(GPChecklistExecutionItem)
                            .filter(
                                getattr(GPChecklistExecutionItem, "exec_id")
                                == getattr(last, "id")
                            )
                            .all()
                        )
                    else:
                        items = (
                            db.session.query(GPChecklistExecutionItem)
                            .filter(
                                getattr(GPChecklistExecutionItem, "execution_id")
                                == getattr(last, "id")
                            )
                            .all()
                        )
                except Exception:
                    items = []

            ok = 0
            nok = 0
            itens_serializados: List[Dict[str, Any]] = []
            for it in items:
                st = getattr(it, "status", None)
                if st is not None:
                    s_norm = str(st).strip().lower()
                    if s_norm in ("sim", "ok", "conforme", "aprovado"):
                        ok += 1
                    elif s_norm in (
                        "nao",
                        "não",
                        "n_ok",
                        "nconforme",
                        "reprovado",
                        "fail",
                    ):
                        nok += 1
                itens_serializados.append(
                    {
                        "ordem": getattr(it, "ordem", None)
                        or getattr(it, "order", None),
                        "desc": getattr(it, "descricao", None)
                        or getattr(it, "descricao_item", None),
                        "status": getattr(it, "status", None),
                    }
                )

            checklist_payload = {
                "executado": True,
                "itens": itens_serializados,
                "resultado_final": "ok" if nok == 0 else "nao",
                "started_at": _fmt_dt_iso(getattr(last, "started_at", None)),
                "finished_at": _fmt_dt_iso(getattr(last, "finished_at", None)),
                "operador": getattr(last, "operador", None)
                or getattr(last, "usuario", None),
            }

    payload["checklist"] = checklist_payload

    # Placeholders compatíveis
    payload["separacao"] = {
        "inicio": None,
        "fim": None,
        "duracao_min": None,
        "responsavel": None,
        "ocorrencias": [],
    }
    payload["liberacao"] = {
        "status": "pendente",
        "liberado_por": None,
        "liberado_em": None,
        "observacao": None,
    }
    payload["preservacao"] = {
        "embalagem_ok": None,
        "registrado_por": None,
        "registrado_em": None,
        "observacao": None,
        "fotos": [],
    }

    return jsonify({"ok": True, "data": payload})
