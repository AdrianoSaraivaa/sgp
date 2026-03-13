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

# ====================================================================
# [BLOCO] BLOCO_CONFIG
# [NOME] gp_rastreabilidade_bp
# [RESPONSABILIDADE] Registro do Blueprint de rastreabilidade por número de série
# ====================================================================
gp_rastreabilidade_bp = Blueprint(
    "gp_rastreabilidade_bp",
    __name__,
    url_prefix="/producao/gp",
)
# ====================================================================
# [FIM BLOCO] gp_rastreabilidade_bp
# ====================================================================


# ------------------------------------------------------------------------------
# Imports de modelos: sempre protegidos para NUNCA quebrar o import do módulo
# ------------------------------------------------------------------------------

# ====================================================================
# [BLOCO] BLOCO_IMPORT
# [NOME] GPWorkOrder / GPWorkStage
# [RESPONSABILIDADE] Imports protegidos de modelos de Ordem e Estágios
# ====================================================================
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
# ====================================================================
# [FIM BLOCO] GPWorkOrder / GPWorkStage
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_IMPORT
# [NOME] GPBenchConfig
# [RESPONSABILIDADE] Import protegido de configuração de habilitação por bancada
# ====================================================================
# Configuração de habilitação por bancada
GPBenchConfig = None  # type: ignore
try:
    from app.models.producao_models.gp_modelos import GPBenchConfig as _BC  # type: ignore

    GPBenchConfig = _BC
except Exception:
    pass
# ====================================================================
# [FIM BLOCO] GPBenchConfig
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_IMPORT
# [NOME] GPHipotRun
# [RESPONSABILIDADE] Import protegido de modelo de execuções de HiPot
# ====================================================================
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
# ====================================================================
# [FIM BLOCO] GPHipotRun
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_IMPORT
# [NOME] GPChecklistExecution / GPChecklistExecutionItem
# [RESPONSABILIDADE] Imports protegidos de modelos de execução de checklist e itens
# ====================================================================
# Checklist (preferir Execution/Item)
GPChecklistExecution = None  # type: ignore
GPChecklistExecutionItem = None  # type: ignore
GPChecklistTemplate = None  # type: ignore
GPChecklistItem = None  # type: ignore
# Tentativa 1: caminho novo (gp_models)
try:
    from app.models.producao_models.gp_models.gp_checklist import (
        GPChecklistExecution as _CE,
        GPChecklistExecutionItem as _CEI,
        GPChecklistTemplate as _CT,
        GPChecklistItem as _CI,
    )

    GPChecklistExecution, GPChecklistExecutionItem = _CE, _CEI
    GPChecklistTemplate, GPChecklistItem = _CT, _CI
except Exception:
    # Tentativa 2: caminho antigo (mantém compatibilidade)
    try:
        from app.models.producao_models.gp_checklist import (
            GPChecklistExecution as _CE,
            GPChecklistExecutionItem as _CEI,
            GPChecklistTemplate as _CT,
            GPChecklistItem as _CI,
        )

        GPChecklistExecution, GPChecklistExecutionItem = _CE, _CEI
        GPChecklistTemplate, GPChecklistItem = _CT, _CI
    except Exception:
        # Tentativa 3: legado (nomes antigos)
        try:
            from app.models.producao_models.gp_checklist import (
                GPChecklistExec as _CE,
                GPChecklistItemLog as _CEI,
            )

            GPChecklistExecution, GPChecklistExecutionItem = _CE, _CEI
        except Exception:
            pass
# Fallback adicional: models_sqla (se existir) — não quebra se faltar
if GPChecklistExecution is None or GPChecklistExecutionItem is None:
    try:
        from app.models_sqla import (
            GPChecklistExecucao as _CE,
            GPChecklistExecItem as _CEI,
            GPChecklistTemplate as _CT,
            GPChecklistItem as _CI,
        )

        GPChecklistExecution, GPChecklistExecutionItem = _CE, _CEI
        GPChecklistTemplate, GPChecklistItem = _CT, _CI
    except Exception:
        pass
# ====================================================================
# [FIM BLOCO] GPChecklistExecution / GPChecklistExecutionItem
# ====================================================================


# ------------------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------------------

# ====================================================================
# [BLOCO] BLOCO_CONFIG
# [NOME] Constantes de rastreabilidade
# [RESPONSABILIDADE] Definição de chaves e limites de paginação
# ====================================================================
SESSION_KEY = "rastreamento_ok"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
# ====================================================================
# [FIM BLOCO] Constantes de rastreabilidade
# ====================================================================


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _is_authed
# [RESPONSABILIDADE] Verificar se a sessão está autenticada para rastreabilidade
# ====================================================================
def _is_authed() -> bool:
    return bool(session.get(SESSION_KEY))


# ====================================================================
# [FIM BLOCO] _is_authed
# ====================================================================


# ==================================================================
# [BLOCO] FUNÇÃO
# [NOME] _require_auth_redirect
# [RESPONSABILIDADE] Redirecionar para a tela de senha quando não autenticado
# ====================================================================
def _require_auth_redirect():
    if not _is_authed():
        return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_senha"))
    return None


# ====================================================================
# [FIM BLOCO] _require_auth_redirect
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _parse_int
# [RESPONSABILIDADE] Converter valor para inteiro com fallback padrão
# ====================================================================
def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


# ====================================================================
# [FIM BLOCO] _parse_int
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _parse_page_size
# [RESPONSABILIDADE] Normalizar page_size respeitando limites mínimo e máximo
# ====================================================================
def _parse_page_size(raw: Any) -> int:
    size = max(_parse_int(raw, DEFAULT_PAGE_SIZE), 1)
    return min(size, MAX_PAGE_SIZE)


# ====================================================================
# [FIM BLOCO] _parse_page_size
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _parse_date_yyyy_mm_dd
# [RESPONSABILIDADE] Converter string YYYY-MM-DD em datetime (ou None)
# ====================================================================
def _parse_date_yyyy_mm_dd(raw: str) -> Optional[datetime]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except Exception:
        return None


# ====================================================================
# [FIM BLOCO] _parse_date_yyyy_mm_dd
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _end_of_day
# [RESPONSABILIDADE] Ajustar datetime para o final do dia (23:59:59.999999)
# ====================================================================
def _end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


# ====================================================================
# [FIM BLOCO] _end_of_day
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _fmt_dt_iso
# [RESPONSABILIDADE] Formatar datetime em ISO de forma segura
# ====================================================================
def _fmt_dt_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


# ====================================================================
# [FIM BLOCO] _fmt_dt_iso
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _safe_int_minutes
# [RESPONSABILIDADE] Calcular duração em minutos entre dois datetimes de forma segura
# ====================================================================
def _safe_int_minutes(a: Optional[datetime], b: Optional[datetime]) -> Optional[int]:
    if not a or not b:
        return None
    try:
        return int((b - a).total_seconds() / 60)
    except Exception:
        return None


# ====================================================================
# [FIM BLOCO] _safe_int_minutes
# ====================================================================


# ------------------------------------------------------------------------------
# Rotas
# ------------------------------------------------------------------------------


# ====================================================================
# [BLOCO] ROTA
# [NOME] rastreabilidade_home
# [RESPONSABILIDADE] Página inicial de rastreabilidade
# ====================================================================
@gp_rastreabilidade_bp.route("/rastreabilidade")
def rastreabilidade_home():
    auth_redirect = _require_auth_redirect()
    if auth_redirect:
        return auth_redirect
    return render_template(
        "producao_templates/rastreabilidade_templates/rastreamento.html"
    )


# ====================================================================
# [FIM BLOCO] rastreabilidade_home
# ====================================================================


# ====================================================================
# [BLOCO] ROTA
# [NOME] rastreabilidade_senha
# [RESPONSABILIDADE] Página de autenticação para rastreabilidade
# ====================================================================
@gp_rastreabilidade_bp.route("/rastreabilidade/senha", methods=["GET", "POST"])
def rastreabilidade_senha():
    if request.method == "POST":
        password = (
            (request.form.get("senha") or request.form.get("password") or "")
            .strip()
            .lower()
        )

        # debug (antes de qualquer return)
        print("[RASTREABILIDADE] password recebido:", repr(password))

        if password == "sgp":  # sua senha
            session[SESSION_KEY] = True
            flash("Autenticação bem-sucedida!", "success")
            return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_home"))

        flash("Senha incorreta.", "danger")
        # NÃO precisa retornar aqui; deixa cair para o render do final

    return render_template(
        "producao_templates/rastreabilidade_templates/senha_rastreamento.html"
    )


# ====================================================================
# [FIM BLOCO] rastreabilidade_senha
# ====================================================================


# ====================================================================
# [BLOCO] ROTA
# [NOME] rastreabilidade_sair
# [RESPONSABILIDADE] Rota para deslogar da sessão de rastreabilidade
# ====================================================================
@gp_rastreabilidade_bp.route("/rastreabilidade/sair")
def rastreabilidade_sair():
    session.pop(SESSION_KEY, None)
    flash("Você saiu da sessão de rastreabilidade.", "info")
    return redirect(url_for("gp_rastreabilidade_bp.rastreabilidade_senha"))


# ====================================================================
# [FIM BLOCO] rastreabilidade_sair
# ====================================================================


# ====================================================================
# [BLOCO] ROTA
# [NOME] rastreabilidade_detalhes
# [RESPONSABILIDADE] Página de detalhes de rastreabilidade por número de série
# ====================================================================
@gp_rastreabilidade_bp.route("/rastreabilidade/<serial>")
def rastreabilidade_detalhes(serial: str):
    auth_redirect = _require_auth_redirect()
    if auth_redirect:
        return auth_redirect
    return render_template(
        "producao_templates/rastreabilidade_templates/detalhes_rastreamento.html",
        serial=serial,
    )


# ====================================================================
# [FIM BLOCO] rastreabilidade_detalhes
# ====================================================================


# ====================================================================
# [BLOCO] API
# [NOME] rastreabilidade_api_search
# [RESPONSABILIDADE] API para buscar ordens de serviço por número de série
# ====================================================================
@gp_rastreabilidade_bp.route("/rastreabilidade/api/search")
def rastreabilidade_api_search():
    auth_redirect = _require_auth_redirect()
    if auth_redirect:
        return auth_redirect

    serial = (request.args.get("serial") or "").strip()
    page = max(_parse_int(request.args.get("page"), 1), 1)
    page_size = _parse_page_size(request.args.get("page_size"))

    if GPWorkOrder is None:
        return (
            jsonify(
                {"ok": False, "error": "Modelos de Ordem de Serviço não carregados."}
            ),
            500,
        )

    try:
        query = db.session.query(GPWorkOrder)

        if serial:
            query = query.filter(getattr(GPWorkOrder, "serial") == serial)

        order_col = getattr(GPWorkOrder, "updated_at", None)
        if order_col is None:
            order_col = getattr(GPWorkOrder, "created_at", None)
        if order_col is None:
            order_col = getattr(GPWorkOrder, "id")

        query = query.order_by(order_col.desc())

        total_items = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        results = []
        for item in items:
            results.append(
                {
                    "id": getattr(item, "id", None),
                    "serial": getattr(item, "serial", None),
                    "modelo": getattr(item, "modelo", None),
                    "status": getattr(item, "status", None),
                    "current_bench": getattr(item, "current_bench", None),
                    "started_at": _fmt_dt_iso(getattr(item, "started_at", None)),
                    "finished_at": _fmt_dt_iso(getattr(item, "finished_at", None)),
                    "created_at": _fmt_dt_iso(getattr(item, "created_at", None)),
                    "updated_at": _fmt_dt_iso(getattr(item, "updated_at", None)),
                }
            )

        return jsonify(
            {
                "ok": True,
                "data": {
                    "serial": serial or None,
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_items,
                    "total_pages": (total_items + page_size - 1) // page_size,
                    "items": results,
                },
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ====================================================================
# [FIM BLOCO] rastreabilidade_api_search
# ====================================================================


# ====================================================================
# [BLOCO] API
# [NOME] rastreabilidade_api_detalhe
# [RESPONSABILIDADE] API para buscar detalhes de rastreabilidade por número de série
# ====================================================================
@gp_rastreabilidade_bp.route("/rastreabilidade/api/<serial>")
def rastreabilidade_api_detalhe(serial: str):
    auth_redirect = _require_auth_redirect()
    if auth_redirect:
        return auth_redirect

    if GPWorkOrder is None:
        return (
            jsonify(
                {"ok": False, "error": "Modelos de Ordem de Serviço não carregados."}
            ),
            500,
        )

    work_order = (
        db.session.query(GPWorkOrder)
        .filter(getattr(GPWorkOrder, "serial") == serial)
        .first()
    )
    if not work_order:
        return jsonify({"ok": False, "error": "Número de série não encontrado."}), 404

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
        # compat (não quebra se não existir)
        "started_at": _fmt_dt_iso(getattr(work_order, "started_at", None)),
        "finished_at": _fmt_dt_iso(getattr(work_order, "finished_at", None)),
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

    # Checklist (Nível C — Auditoria forte) — Bancada 8
    # - Sempre listar TODOS os itens do template
    # - Status: Aprovado / Retrabalho / Reprovado / Não informado
    # - Observações do operador por item
    # - NCRs por item
    # - Histórico de reexecuções (se houver)

    def _norm_check_result(val: Any) -> str:
        s = str(val or "").strip().lower()
        if not s:
            return "Não informado"
        if s in ("aprovado", "ok", "sim", "conforme", "true", "1"):
            return "Aprovado"
        if s in ("retrabalho", "rework"):
            return "Retrabalho"
        if s in (
            "reprovado",
            "nao",
            "não",
            "nok",
            "n_ok",
            "nconforme",
            "reprovado",
            "fail",
            "false",
            "0",
        ):
            return "Reprovado"
        # heurística
        if "retrabalho" in s:
            return "Retrabalho"
        if "reprov" in s or "não" in s or "nao" in s or "nok" in s:
            return "Reprovado"
        if "aprov" in s or s == "ok":
            return "Aprovado"
        return "Não informado"

    def _safe_json_list(val: Any) -> List[Dict[str, Any]]:
        if val is None:
            return []
        if isinstance(val, list):
            out: List[Dict[str, Any]] = []
            for x in val:
                if isinstance(x, dict):
                    out.append(x)
                else:
                    out.append({"descricao": str(x)})
            return out
        if isinstance(val, dict):
            return [val]
        if isinstance(val, str):
            raw = val.strip()
            if not raw:
                return []
            try:
                import json as _json  # stdlib

                parsed = _json.loads(raw)
                return _safe_json_list(parsed)
            except Exception:
                return [{"descricao": raw}]
        return [{"descricao": str(val)}]

    def _pick_template(modelo_val: Any, exec_obj: Any) -> Any:
        # Prioridade:
        # 1) template_id na execução
        # 2) template por modelo (campo 'modelo' no template)
        if GPChecklistTemplate is None:
            return None
        try:
            tpl_id = getattr(exec_obj, "template_id", None)
            if tpl_id:
                return (
                    db.session.query(GPChecklistTemplate)
                    .filter(getattr(GPChecklistTemplate, "id") == tpl_id)
                    .first()
                )
        except Exception:
            pass
        if modelo_val:
            try:
                if hasattr(GPChecklistTemplate, "modelo"):
                    return (
                        db.session.query(GPChecklistTemplate)
                        .filter(
                            getattr(GPChecklistTemplate, "modelo") == str(modelo_val)
                        )
                        .first()
                    )
            except Exception:
                pass
        return None

    def _load_template_items(template_obj: Any) -> List[Dict[str, Any]]:
        # Retorna lista ordenada [{ordem, descricao}]
        if not template_obj or GPChecklistItem is None:
            return []
        try:
            tpl_id = getattr(template_obj, "id", None)
            q = db.session.query(GPChecklistItem)
            if hasattr(GPChecklistItem, "template_id"):
                q = q.filter(getattr(GPChecklistItem, "template_id") == tpl_id)
            elif hasattr(GPChecklistItem, "template"):
                q = q.filter(getattr(GPChecklistItem, "template") == tpl_id)
            q = q.order_by(getattr(GPChecklistItem, "ordem").asc())
            rows = q.all()
        except Exception:
            rows = []
        out: List[Dict[str, Any]] = []
        for r in rows or []:
            ordem = getattr(r, "ordem", None) or getattr(r, "order", None)
            desc = (
                getattr(r, "descricao", None)
                or getattr(r, "descricao_item", None)
                or getattr(r, "desc", None)
            )
            if ordem is None:
                continue
            out.append({"ordem": int(ordem), "descricao": desc})
        return out

    def _fetch_exec_items(exec_obj: Any) -> List[Any]:
        if GPChecklistExecutionItem is None:
            return []
        try:
            if hasattr(GPChecklistExecutionItem, "exec_id"):
                return (
                    db.session.query(GPChecklistExecutionItem)
                    .filter(
                        getattr(GPChecklistExecutionItem, "exec_id")
                        == getattr(exec_obj, "id")
                    )
                    .order_by(getattr(GPChecklistExecutionItem, "ordem").asc())
                    .all()
                )
            return (
                db.session.query(GPChecklistExecutionItem)
                .filter(
                    getattr(GPChecklistExecutionItem, "execution_id")
                    == getattr(exec_obj, "id")
                )
                .order_by(getattr(GPChecklistExecutionItem, "ordem").asc())
                .all()
            )
        except Exception:
            return []

    def _extract_item_observacao(it: Any) -> Optional[str]:
        for k in (
            "observacao",
            "observacoes",
            "obs",
            "comentario",
            "comentarios",
            "nota",
            "notas",
        ):
            v = getattr(it, k, None)
            if v is not None and str(v).strip():
                return str(v).strip()

        ncrs = _safe_json_list(getattr(it, "ncrs", None))
        for n in ncrs:
            txt = (
                n.get("descricao")
                or n.get("observacao")
                or n.get("obs")
                or n.get("texto")
            )
            if txt and str(txt).strip():
                return str(txt).strip()
        return None

    checklist_b8: Dict[str, Any] = {
        "executado": False,
        "latest": None,
        "executions": [],
    }

    if GPChecklistExecution is not None:
        try:
            execs_all = (
                db.session.query(GPChecklistExecution)
                .filter(getattr(GPChecklistExecution, "serial") == str(serial))
                .order_by(getattr(GPChecklistExecution, "started_at").asc())
                .all()
            )
        except Exception:
            execs_all = []

        # Filtrar bancada 8 quando existir informação de bancada
        execs_b8: List[Any] = []
        for e in execs_all or []:
            b = getattr(e, "bench_id", None)
            if b is None:
                continue
            try:
                if int(str(b).strip()) == 8:
                    execs_b8.append(e)
            except Exception:
                if str(b).strip().lower() in ("8", "b8", "bench8", "bench_8"):
                    execs_b8.append(e)

        # Fallback: se não existir bench_id, usa todas (but still by serial)
        execs_used = execs_b8 if execs_b8 else execs_all

        if execs_used:
            checklist_b8["executado"] = True

            modelo_val = payload.get("modelo")
            template_obj = _pick_template(modelo_val, execs_used[-1])
            template_items = _load_template_items(template_obj)

            for ex in execs_used:
                ex_items = _fetch_exec_items(ex)

                by_ord: Dict[int, Any] = {}
                for it in ex_items or []:
                    o = getattr(it, "ordem", None) or getattr(it, "order", None)
                    if o is None:
                        continue
                    try:
                        by_ord[int(o)] = it
                    except Exception:
                        pass

                itens_out: List[Dict[str, Any]] = []

                base_ordens: List[int] = []
                if template_items:
                    base_ordens = [int(x["ordem"]) for x in template_items]
                else:
                    base_ordens = sorted(by_ord.keys())

                tpl_desc_map: Dict[int, Any] = {
                    int(x["ordem"]): x.get("descricao") for x in (template_items or [])
                }

                for ordem in base_ordens:
                    it = by_ord.get(int(ordem))
                    desc = tpl_desc_map.get(int(ordem))
                    if not desc and it is not None:
                        desc = (
                            getattr(it, "descricao", None)
                            or getattr(it, "descricao_item", None)
                            or getattr(it, "desc", None)
                        )

                    if it is None:
                        itens_out.append(
                            {
                                "ordem": int(ordem),
                                "descricao": desc,
                                "status": "Não informado",
                                "observacao": None,
                                "ncrs": [],
                            }
                        )
                        continue

                    st_raw = getattr(it, "status", None) or getattr(
                        it, "resultado", None
                    )
                    status_norm = _norm_check_result(st_raw)

                    itens_out.append(
                        {
                            "ordem": int(ordem),
                            "descricao": desc,
                            "status": status_norm,
                            "observacao": _extract_item_observacao(it),
                            "ncrs": _safe_json_list(getattr(it, "ncrs", None)),
                        }
                    )

                has_reprov = any(x["status"] == "Reprovado" for x in itens_out)
                has_retrab = any(x["status"] == "Retrabalho" for x in itens_out)
                resultado_final = (
                    "Reprovado"
                    if has_reprov
                    else "Retrabalho" if has_retrab else "Aprovado"
                )

                started_at = getattr(ex, "started_at", None)
                finished_at = getattr(ex, "finished_at", None)

                checklist_b8["executions"].append(
                    {
                        "exec_id": getattr(ex, "id", None),
                        "bench_id": getattr(ex, "bench_id", None),
                        "started_at": _fmt_dt_iso(started_at),
                        "finished_at": _fmt_dt_iso(finished_at),
                        "duracao_min": _safe_int_minutes(started_at, finished_at),
                        "operador": getattr(ex, "operador", None)
                        or getattr(ex, "usuario", None),
                        "resultado_final": resultado_final,
                        "itens": itens_out,
                    }
                )

            checklist_b8["latest"] = (
                checklist_b8["executions"][-1] if checklist_b8["executions"] else None
            )

    # Compat: mantém payload["checklist"] (resumo da última execução)
    if checklist_b8.get("latest"):
        latest = checklist_b8["latest"]
        payload["checklist"] = {
            "executado": True,
            "itens": [
                {
                    "ordem": it.get("ordem"),
                    "desc": it.get("descricao"),
                    "status": it.get("status"),
                    "observacao": it.get("observacao"),
                    "ncrs": it.get("ncrs", []),
                }
                for it in (latest.get("itens") or [])
            ],
            "resultado_final": latest.get("resultado_final"),
            "started_at": latest.get("started_at"),
            "finished_at": latest.get("finished_at"),
            "operador": latest.get("operador"),
        }
    else:
        payload["checklist"] = {
            "executado": False,
            "itens": [],
            "resultado_final": None,
        }

    # Novo bloco completo para relatório (B8)
    payload["checklist_b8"] = checklist_b8

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


# ====================================================================
# [FIM BLOCO] rastreabilidade_api_detalhe
# ====================================================================


# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_CONFIG: gp_rastreabilidade_bp
# BLOCO_IMPORT: GPWorkOrder / GPWorkStage
# BLOCO_IMPORT: GPBenchConfig
# BLOCO_IMPORT: GPHipotRun
# BLOCO_IMPORT: GPChecklistExecution / GPChecklistExecutionItem
# BLOCO_CONFIG: Constantes de rastreabilidade
# FUNÇÃO: _is_authed
# FUNÇÃO: _require_auth_redirect
# FUNÇÃO: _parse_int
# FUNÇÃO: _parse_page_size
# FUNÇÃO: _parse_date_yyyy_mm_dd
# FUNÇÃO: _end_of_day
# FUNÇÃO: _fmt_dt_iso
# FUNÇÃO: _safe_int_minutes
# FUNÇÃO: rastreabilidade_home
# FUNÇÃO: rastreabilidade_senha
# FUNÇÃO: rastreabilidade_sair
# FUNÇÃO: rastreabilidade_detalhes
# FUNÇÃO: rastreabilidade_api_search
# FUNÇÃO: rastreabilidade_api_detalhe
# ====================================================================
