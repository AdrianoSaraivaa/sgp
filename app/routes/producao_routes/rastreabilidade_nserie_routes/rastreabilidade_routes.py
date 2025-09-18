# app/routes/producao_routes/rastreabilidade_nserie_routes/rastreabilidade_routes.py
from __future__ import annotations

"""
Rotas de Rastreabilidade por Nº de Série (SGP)
- Protegidas por uma senha simples de sessão (campo SESSION_KEY).
- Páginas: home, senha, detalhes.
- APIs: /rastreabilidade/api/search (lista) e /rastreabilidade/api/<serial> (detalhe).
"""

from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
)
from app import db
from app.models.producao_models.gp_execucao import GPWorkOrder

# Imports opcionais — o módulo funciona mesmo se estes modelos ainda não existirem
try:
    from app.models.producao_models.gp_modelos import GPBenchConfig  # Configuração por modelo/bench
except Exception:  # pragma: no cover
    GPBenchConfig = None  # type: ignore

try:
    from app.models.producao_models.gp_hipot import GPHipotResult  # Resultados de HiPot
except Exception:  # pragma: no cover
    GPHipotResult = None  # type: ignore

try:
    from app.models.producao_models.gp_checklist import GPChecklistExec, GPChecklistItemLog  # Checklist da Bancada 8
except Exception:  # pragma: no cover
    GPChecklistExec = GPChecklistItemLog = None  # type: ignore


# ------------------------------------------------------------------------------
# Blueprint & Constantes
# ------------------------------------------------------------------------------
gp_rastreabilidade_bp = Blueprint(
    "gp_rastreabilidade_bp",
    __name__,
    url_prefix="/producao/gp",
)

SESSION_KEY = "rastreamento_ok"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _is_authed() -> bool:
    """Retorna True se a sessão estiver autenticada pela senha simples."""
    return bool(session.get(SESSION_KEY))


def _require_auth_redirect():
    """Redireciona para a tela de senha se a sessão não estiver autenticada."""
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
    """Converte 'YYYY-MM-DD' para datetime no início do dia local. Retorna None se inválido/vazio."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        # Sem timezone — use conforme o fuso do servidor
        return datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        return None


def _end_of_day(dt: datetime) -> datetime:
    """Retorna o último microsegundo do dia de 'dt'."""
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def _fmt_dt_iso(dt: Optional[datetime]) -> Optional[str]:
    """Formata datetime para ISO 8601 (ou None)."""
    if not dt:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


# ------------------------------------------------------------------------------
# Views (HTML)
# ------------------------------------------------------------------------------
@gp_rastreabilidade_bp.route("/rastreabilidade/", methods=["GET"])
def rastreabilidade_home():
    if (redir := _require_auth_redirect()) is not None:
        return redir
    return render_template("producao_templates/rastreabilidade_templates/rastreamento.html")


@gp_rastreabilidade_bp.route("/rastreabilidade/senha", methods=["GET", "POST"])
def rastreabilidade_senha():
    """
    Tela simples de senha. Aceita 'sgp' (case-insensitive). Em produção, substituir por auth real.
    """
    if request.method == "POST":
        submitted = (request.form.get("senha") or "").strip()
        if submitted.lower() == "sgp":
            session[SESSION_KEY] = True
            return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_home"))
        flash("Senha incorreta. Tente novamente.", "error")
    return render_template("producao_templates/rastreabilidade_templates/senha_rastreamento.html")


@gp_rastreabilidade_bp.route("/rastreabilidade/sair", methods=["POST"])
def rastreabilidade_sair():
    """Limpa a sessão de rastreabilidade e volta para a tela de senha."""
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
    """
    Lista de ordens filtrável por: serial, modelo, status e intervalo de datas (updated_at).
    Query params:
      - serial, modelo, status
      - data_ini, data_fim (YYYY-MM-DD)
      - page (>=1), page_size (1..100)
    """
    if not _is_authed():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    serial = (request.args.get("serial") or "").strip()
    modelo = (request.args.get("modelo") or "").strip()
    status = (request.args.get("status") or "").strip()
    data_ini = (request.args.get("data_ini") or "").strip()
    data_fim = (request.args.get("data_fim") or "").strip()
    page = max(_parse_int(request.args.get("page", 1), 1), 1)
    page_size = _parse_page_size(request.args.get("page_size", DEFAULT_PAGE_SIZE))

    q = db.session.query(GPWorkOrder)

    if serial:
        q = q.filter(GPWorkOrder.serial.ilike(f"%{serial}%"))
    if modelo:
        q = q.filter(GPWorkOrder.modelo.ilike(f"%{modelo}%"))
    if status:
        q = q.filter(GPWorkOrder.status == status)

    # Intervalo de datas por updated_at (altere para created_at se preferir)
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
                "status": getattr(o, "status", None),  # p.ex.: in_progress, done
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
    """
    Detalhe completo de rastreabilidade por serial.
    Inclui cabeçalho da ordem + placeholders de separação, bancadas, HiPot, Checklist,
    liberação e preservação (popular quando as tabelas estiverem disponíveis).
    """
    if not _is_authed():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # 1) Ordem
    order = db.session.query(GPWorkOrder).filter(GPWorkOrder.serial == str(serial)).first()
    if not order:
        return jsonify({"ok": False, "error": "not_found", "message": f"Serial {serial} não encontrado"}), 404

    # 2) Cabeçalho básico (campos protegidos por getattr)
    payload: Dict[str, Any] = {
        "serial": getattr(order, "serial", None),
        "modelo": getattr(order, "modelo", None),
        "lote": getattr(order, "lote", None),
        # se o seu ID da ordem é 'id', mantenha; se for 'ordem_producao', ajuste aqui
        "ordem_producao": getattr(order, "id", None),
        "criado_em": _fmt_dt_iso(getattr(order, "created_at", None)),
        "criado_por": getattr(order, "created_by", None),
        "status_atual": getattr(order, "status", None),
        "current_bench": getattr(order, "current_bench", None),
        "ultima_atualizacao": _fmt_dt_iso(getattr(order, "updated_at", None)),
    }

    # 3) Separação — placeholder
    payload["separacao"] = {
        "inicio": None,
        "fim": None,
        "duracao_min": None,
        "responsavel": None,
        "ocorrencias": [],
    }

    # 4) Bancadas — carrega habilitação via GPBenchConfig, se disponível
    payload["bancadas"] = []
    if GPBenchConfig and payload.get("modelo"):
        try:
            configs = (
                db.session.query(GPBenchConfig)
                .filter(GPBenchConfig.modelo == payload["modelo"])
                .all()
            )
            enabled_map: Dict[int, bool] = {}
            for cfg in configs:
                bench_id = getattr(cfg, "bench_id", None)
                enabled = getattr(cfg, "enabled", True)
                if bench_id is not None:
                    enabled_map[int(bench_id)] = bool(enabled)

            for i in range(1, 9):
                payload["bancadas"].append(
                    {
                        "bench_id": i,
                        "nome": f"Bancada {i}",
                        "habilitada": enabled_map.get(i, True),
                        "inicio": None,
                        "fim": None,
                        "duracao_min": None,
                        "responsavel": None,
                        "ocorrencias": [],
                    }
                )
        except Exception:
            # Se der problema na leitura da config, deixa lista vazia (front lida)
            payload["bancadas"] = []

    # 5) HiPot — placeholder (popular quando GPHipotResult estiver integrado)
    payload["hipot"] = {
        "executado": False,
        "equipamento": None,
        "calibracao": None,
        "gb1": None,
        "hp1": None,
        "resultado_final": None,
        "observacao_reprovacao": None,
    }

    # 6) Checklist — placeholder (popular quando GPChecklistExec/Logs estiverem integrados)
    payload["checklist"] = {
        "executado": False,
        "itens": [],
        "resultado_final": None,
    }

    # 7) Liberação / Preservação — placeholders
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
