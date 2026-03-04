# app/routes/producao_routes/gerenciamento_producao_routes/gp_checklist_api.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict

from flask import Blueprint, request, jsonify
from sqlalchemy import select, delete

from app import db

# Modelos ORM oficiais (corrigido para usar models_sqla)
from app.models_sqla import (
    GPChecklistTemplate as ChecklistTemplate,
    GPChecklistItem as ChecklistTemplateItem,
    GPChecklistExecution as ChecklistExec,
    GPChecklistExecutionItem as ChecklistExecItemLog,
)

# Nota: ChecklistNCR não existe no models_sqla, usando estrutura simplificada
# Para NCRs, utilizaremos o campo JSON existente em GPChecklistExecutionItem

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] gp_checklist_api_bp
# [RESPONSABILIDADE] Registrar endpoints de API para templates e execuções de checklist de produção
# ====================================================================
gp_checklist_api_bp = Blueprint(
    "gp_checklist_api_bp",
    __name__,
    url_prefix="/api/gp/checklist",
)


# ===============================
# Helpers
# ===============================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _iso
# [RESPONSABILIDADE] Converter datetime opcional para string ISO
# ====================================================================
def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# ====================================================================
# [FIM BLOCO] _iso
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _parse_iso
# [RESPONSABILIDADE] Fazer parse seguro de string ISO para datetime opcional
# ====================================================================
def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ====================================================================
# [FIM BLOCO] _parse_iso
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _ok
# [RESPONSABILIDADE] Padronizar resposta de sucesso em JSON
# ====================================================================
def _ok(**kw):
    return jsonify({"ok": True, **kw}), 200


# ====================================================================
# [FIM BLOCO] _ok
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _err
# [RESPONSABILIDADE] Padronizar resposta de erro em JSON com status code
# ====================================================================
def _err(msg: str, status: int = 400, **ctx):
    return jsonify({"ok": False, "error": msg, **ctx}), status


# ====================================================================
# [FIM BLOCO] _err
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _infer_model_by_serial
# [RESPONSABILIDADE] Inferir modelo a partir do número de série conforme regra simplificada
# ====================================================================
def _infer_model_by_serial(serial: str) -> Optional[str]:
    s = "".join(ch for ch in (serial or "") if ch.isdigit())
    if len(s) < 3:
        return None
    # regra simples (ajuste conforme seu padrão de série)
    MAP = {"1": "PM2100", "2": "PM2200", "7": "PM700"}
    return MAP.get(s[2])


# ====================================================================
# [FIM BLOCO] _infer_model_by_serial
# ====================================================================


# ===============================
# Templates (CRUD mínimo)
# ===============================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] list_templates
# [RESPONSABILIDADE] Listar modelos disponíveis a partir dos templates cadastrados
# ====================================================================
@gp_checklist_api_bp.get("/templates")
def list_templates():
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_templates_db
    # [RESPONSABILIDADE] Consultar todos os templates de checklist cadastrados
    # ====================================================================
    rows = db.session.scalars(select(ChecklistTemplate)).all()
    modelos = sorted(
        {
            getattr(r, "model_code", None) or getattr(r, "modelo", None)
            for r in rows
            if r
        }
    )
    return _ok(modelos=modelos)


# ====================================================================
# [FIM BLOCO] list_templates
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] get_template
# [RESPONSABILIDADE] Carregar template e itens por modelo e serializar no formato compatível
# ====================================================================
@gp_checklist_api_bp.get("/template/<modelo>")
def get_template(modelo: str):
    modelo = (modelo or "").strip()
    if not modelo:
        return _err("Modelo é obrigatório.", 400)

    # Compat: alguns schemas usam campo 'model_code', outros 'modelo'
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_template_por_modelo_db
    # [RESPONSABILIDADE] Buscar template de checklist pelo modelo informado
    # ====================================================================
    tpl = db.session.scalar(
        select(ChecklistTemplate).where(
            (ChecklistTemplate.modelo == modelo)  # type: ignore[attr-defined]
        )
    )
    if not tpl:
        return _err("Template não encontrado para este modelo.", 404)

    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_itens_template_db
    # [RESPONSABILIDADE] Buscar itens do template ordenados pela ordem definida
    # ====================================================================
    itens = db.session.scalars(
        select(ChecklistTemplateItem)
        .where(ChecklistTemplateItem.template_id == tpl.id)
        .order_by(ChecklistTemplateItem.ordem.asc())
    ).all()

    # Serialização compatível com o Builder da Onda 2
    data = {
        "modelo": getattr(tpl, "model_code", None) or getattr(tpl, "modelo", None),
        "tolerancia_inicio": getattr(tpl, "tolerancia_inicio", 0.9),
        "permitir_pular_item": bool(getattr(tpl, "permitir_pular_item", False)),
        "itens": [
            {
                "id": it.id,
                "ordem": it.ordem,
                "descricao": it.descricao,
                "tempo_alvo_s": getattr(it, "tempo_alvo_s", None)
                or getattr(it, "tempo_seg", None),
                "min_s": getattr(it, "min_s", None),
                "max_s": getattr(it, "max_s", None),
                "bloqueante": bool(getattr(it, "bloqueante", False)),
                "exige_nota_se_nao": bool(getattr(it, "exige_nota_se_nao", False)),
                "habilitado": bool(getattr(it, "habilitado", True)),
            }
            for it in itens
        ],
    }
    return _ok(data=data)


# ====================================================================
# [FIM BLOCO] get_template
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] upsert_template
# [RESPONSABILIDADE] Criar ou atualizar template e itens do checklist para um modelo
# ====================================================================
@gp_checklist_api_bp.post("/template")
def upsert_template():
    # Body esperado (Builder Onda 2)
    # {
    #   "modelo": "PM2100",
    #   "tolerancia_inicio": 0.9,
    #   "permitir_pular_item": false,
    #   "itens": [
    #     {
    #       "ordem": 1,
    #       "descricao": "Ajustar ...",
    #       "tempo_alvo_s": 120,
    #       "min_s": 100,
    #       "max_s": 180,
    #       "bloqueante": true,
    #       "exige_nota_se_nao": true,
    #       "habilitado": true
    #     },
    #     ...
    #   ]
    # }
    data = request.get_json(silent=True) or {}
    modelo = (data.get("modelo") or "").strip()
    if not modelo:
        return _err("Modelo é obrigatório.", 400)

    itens = data.get("itens")
    if not isinstance(itens, list) or not itens:
        return _err("Lista de itens é obrigatória.", 400)
    if len(itens) > 10:
        return _err("Máximo de 10 itens por template.", 400)

    tol = data.get("tolerancia_inicio", 0.9)
    try:
        tol = float(tol)
    except Exception:
        return _err("tolerancia_inicio inválida.", 400)

    permitir_pular = bool(data.get("permitir_pular_item", False))

    # Validação item a item
    ordens_vistas = set()
    itens_ok: List[Dict] = []
    for idx, it in enumerate(itens, start=1):
        desc = (it.get("descricao") or "").strip()
        if not desc:
            return _err(f"Item {idx}: 'descricao' obrigatória.", 400)

        ordem = it.get("ordem", idx)
        try:
            ordem = int(ordem)
            if ordem <= 0 or ordem in ordens_vistas:
                raise ValueError()
        except Exception:
            return _err(f"Item {idx}: 'ordem' inválida/duplicada.", 400)
        ordens_vistas.add(ordem)

        try:
            alvo = int(it.get("tempo_alvo_s"))
            if alvo <= 0:
                raise ValueError()
        except Exception:
            return _err(f"Item {idx}: 'tempo_alvo_s' deve ser inteiro > 0.", 400)

        def _int_or_none(v):
            try:
                return int(v) if v is not None else None
            except Exception:
                return None

        item_ok = {
            "ordem": ordem,
            "descricao": desc,
            "tempo_alvo_s": alvo,
            "min_s": _int_or_none(it.get("min_s")),
            "max_s": _int_or_none(it.get("max_s")),
            "bloqueante": bool(it.get("bloqueante", False)),
            "exige_nota_se_nao": bool(it.get("exige_nota_se_nao", False)),
            "habilitado": bool(it.get("habilitado", True)),
        }
        itens_ok.append(item_ok)

    # UPSERT template por modelo (campo model_code ou modelo)
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] upsert_template_db
    # [RESPONSABILIDADE] Criar/atualizar template e substituir itens associados ao modelo
    # ====================================================================
    tpl = db.session.scalar(
        select(ChecklistTemplate).where(
            (ChecklistTemplate.modelo == modelo)  # type: ignore[attr-defined]
        )
    )
    now = datetime.utcnow()
    if not tpl:
        tpl = ChecklistTemplate(
            # model_code=modelo if hasattr(ChecklistTemplate, "model_code") else None,
            modelo=modelo if hasattr(ChecklistTemplate, "modelo") else None,
            tolerancia_inicio=(
                tol if hasattr(ChecklistTemplate, "tolerancia_inicio") else None
            ),
            permitir_pular_item=(
                permitir_pular
                if hasattr(ChecklistTemplate, "permitir_pular_item")
                else None
            ),
            created_at=now if hasattr(ChecklistTemplate, "created_at") else None,
            updated_at=now if hasattr(ChecklistTemplate, "updated_at") else None,
        )
        db.session.add(tpl)
        db.session.flush()
    else:
        if hasattr(tpl, "tolerancia_inicio"):
            tpl.tolerancia_inicio = tol
        if hasattr(tpl, "permitir_pular_item"):
            tpl.permitir_pular_item = permitir_pular
        if hasattr(tpl, "updated_at"):
            tpl.updated_at = now
        db.session.add(tpl)

    # Substitui os itens (delete + insert)
    db.session.execute(
        delete(ChecklistTemplateItem).where(ChecklistTemplateItem.template_id == tpl.id)
    )

    for it in sorted(itens_ok, key=lambda x: x["ordem"]):
        db.session.add(
            ChecklistTemplateItem(
                template_id=tpl.id,
                ordem=it["ordem"],
                descricao=it["descricao"],
                tempo_alvo_s=(
                    it["tempo_alvo_s"]
                    if hasattr(ChecklistTemplateItem, "tempo_alvo_s")
                    else None
                ),
                tempo_seg=(
                    it["tempo_alvo_s"]
                    if hasattr(ChecklistTemplateItem, "tempo_seg")
                    else None
                ),  # compat
                min_s=it["min_s"] if hasattr(ChecklistTemplateItem, "min_s") else None,
                max_s=it["max_s"] if hasattr(ChecklistTemplateItem, "max_s") else None,
                bloqueante=(
                    it["bloqueante"]
                    if hasattr(ChecklistTemplateItem, "bloqueante")
                    else None
                ),
                exige_nota_se_nao=(
                    it["exige_nota_se_nao"]
                    if hasattr(ChecklistTemplateItem, "exige_nota_se_nao")
                    else None
                ),
                habilitado=(
                    it["habilitado"]
                    if hasattr(ChecklistTemplateItem, "habilitado")
                    else True
                ),
            )
        )

    db.session.commit()
    return _ok(modelo=modelo, template_id=tpl.id)


# ====================================================================
# [FIM BLOCO] upsert_template
# ====================================================================


# ===============================
# Execução (front-only consolidado)
# ===============================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] salvar_execucao
# [RESPONSABILIDADE] Persistir execução consolidada de checklist e seus itens a partir do payload do front
# ====================================================================
@gp_checklist_api_bp.post("/exec")
def salvar_execucao():
    # Recebe o JSON de forma segura
    data = request.get_json(silent=True) or {}

    # 1. Validações Iniciais (Cabeçalho da Execução)
    serial = (data.get("serial") or "").strip()
    if not serial:
        return _err("Serial é obrigatório.", 400)

    modelo = (data.get("modelo") or _infer_model_by_serial(serial) or "").strip()
    operador = (data.get("operador") or "").strip() or None
    started_at = _parse_iso(data.get("started_at")) or datetime.utcnow()
    finished_at = _parse_iso(data.get("finished_at"))

    status = (data.get("status") or "").strip().lower() or None
    if status not in (None, "ok", "fail"):
        return _err("Status da execução inválido (use 'ok' ou 'fail').", 400)

    # 2. Validação dos Itens do Checklist
    itens = data.get("itens") or []
    if not isinstance(itens, list):
        return _err("Itens inválidos (esperado lista).", 400)

    for i, it in enumerate(itens, start=1):
        resultado = (it.get("resultado") or "").strip().lower()

        # ✅ Validação do tipo de resultado (incluindo retrabalho)
        if resultado not in ("ok", "nao", "retrabalho"):
            return _err(
                f"Item {i}: resultado inválido (use 'ok', 'nao' ou 'retrabalho').", 400
            )

        # ✅ tempo_alvo_s é obrigatório (DB: tempo_estimado_seg é NOT NULL)
        try:
            tempo_alvo_s = int(it.get("tempo_alvo_s"))
            if tempo_alvo_s <= 0:
                raise ValueError()
        except Exception:
            return _err(
                f"Item {i}: tempo_alvo_s é obrigatório e deve ser inteiro > 0.", 400
            )

        # ✅ Exigência de nota/justificativa quando não for "ok"
        if resultado in ("nao", "retrabalho"):
            nota = (it.get("nota") or "").strip()
            if not nota:
                return _err(
                    f"Item {i}: nota/observação é obrigatória para '{resultado}'.", 400
                )

    # 3. Persistência (Cabeçalho)
    exec_ = ChecklistExec(
        serial=serial,
        modelo=modelo if hasattr(ChecklistExec, "modelo") else None,
        operador=operador if hasattr(ChecklistExec, "operador") else None,
        started_at=started_at if hasattr(ChecklistExec, "started_at") else None,
        finished_at=finished_at if hasattr(ChecklistExec, "finished_at") else None,
        # No modelo real, o campo do cabeçalho é "result" (não "status")
        result=(status if hasattr(ChecklistExec, "result") else None),
    )
    db.session.add(exec_)
    db.session.flush()  # garante exec_.id

    # 4. Persistência (Itens)
    for idx, it in enumerate(itens, start=1):
        ordem = int(it.get("ordem") or idx)
        desc = (it.get("descricao") or "").strip()[:500]
        started_item = _parse_iso(it.get("started_at"))
        finished_item = _parse_iso(it.get("finished_at"))

        try:
            elapsed = (
                int(it.get("elapsed_s")) if it.get("elapsed_s") is not None else None
            )
        except Exception:
            elapsed = None

        resultado = (it.get("resultado") or "").strip().lower()

        # NCRs (mantém compatível com o front atual, se enviar)
        ncrs_data = []
        for n in it.get("ncrs") or []:
            ncrs_data.append(
                {
                    "categoria": (n.get("categoria") or "").strip()[:80],
                    "descricao": (n.get("descricao") or "").strip()[:1000],
                    "foto_path": n.get("foto_path"),
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
        # ✅ Persistir a nota/observação dentro do JSON ncrs
        nota_txt = (it.get("nota") or "").strip()
        if nota_txt:
            ncrs_data.append(
                {
                    "categoria": "OBS",
                    "descricao": nota_txt[:1000],
                    "foto_path": None,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

        item_log = ChecklistExecItemLog(
            exec_id=exec_.id,
            ordem=ordem,
            descricao=desc,
            tempo_estimado_seg=int(it.get("tempo_alvo_s")),
            status=resultado,  # agora aceita: ok | nao | retrabalho
            started_at=started_item,
            finished_at=finished_item,
            elapsed_seg=elapsed,
            ncrs=ncrs_data if ncrs_data else None,
        )
        # Observação: "nota" não é persistida aqui porque o modelo/tabela atual
        # não tem coluna para isso. (Valida e exige no payload, mas não salva.)
        db.session.add(item_log)

    # 5. Se não veio status, inferir pelo conjunto dos itens
    if status is None and hasattr(exec_, "result"):
        any_fail = any(
            (str((it.get("resultado") or "")).strip().lower() in ("nao", "retrabalho"))
            for it in itens
        )
        exec_.result = "fail" if any_fail else "ok"

    db.session.commit()

    return _ok(exec_id=exec_.id)
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] criacao_execucao_checklist_db
    # [RESPONSABILIDADE] Criar registro de execução de checklist e obter ID para vínculo dos itens
    # ====================================================================
    exec_ = ChecklistExec(
        serial=serial,
        modelo=modelo if hasattr(ChecklistExec, "modelo") else None,
        template_id=(
            data.get("template_id") if hasattr(ChecklistExec, "template_id") else None
        ),
        operador=operador if hasattr(ChecklistExec, "operador") else None,
        started_at=started_at if hasattr(ChecklistExec, "started_at") else None,
        finished_at=finished_at if hasattr(ChecklistExec, "finished_at") else None,
        status=status if hasattr(ChecklistExec, "status") else None,
    )
    db.session.add(exec_)
    db.session.flush()

    itens = data.get("itens") or []
    for idx, it in enumerate(itens, start=1):
        ordem = int(it.get("ordem") or idx)
        desc = (it.get("descricao") or "").strip()[:500]
        started = _parse_iso(it.get("started_at"))
        finished = _parse_iso(it.get("finished_at"))
        elapsed = it.get("elapsed_s")
        try:
            elapsed = int(elapsed) if elapsed is not None else None
        except Exception:
            elapsed = None

        resultado = (it.get("resultado") or "").lower() or None
        if resultado not in (None, "ok", "nao"):
            return _err(f"Item {idx}: resultado inválido.", 400)

        nota = (it.get("nota") or "").strip() or None
        pin_used = bool(it.get("pin_used", False))
        pin_reason = (it.get("pin_reason") or "").strip() or None

        # NCRs vinculadas ao item (armazenadas no campo JSON)
        ncrs_data = []
        for n in it.get("ncrs") or []:
            ncr = {
                "categoria": (n.get("categoria") or "").strip()[:80],
                "descricao": (n.get("descricao") or "").strip()[:1000],
                "foto_path": n.get("foto_path"),
                "created_at": datetime.utcnow().isoformat(),
            }
            ncrs_data.append(ncr)

        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] insercao_itens_execucao_db
        # [RESPONSABILIDADE] Inserir logs de itens executados vinculados à execução do checklist
        # ====================================================================
        item_log = ChecklistExecItemLog(
            exec_id=exec_.id,
            ordem=ordem,
            descricao=desc,
            tempo_estimado_seg=it.get("tempo_alvo_s"),
            status=resultado,
            started_at=started,
            finished_at=finished,
            elapsed_seg=elapsed,
            ncrs=ncrs_data if ncrs_data else None,
        )
        db.session.add(item_log)

    # Se não foi informado, inferir status final: qualquer "resultado=='nao'" -> fail
    if status is None:
        # Verificar se algum item teve resultado "nao"
        any_fail = False
        # ====================================================================
        # [BLOCO] BLOCO_DB
        # [NOME] inferencia_status_final_db
        # [RESPONSABILIDADE] Consultar status dos itens para inferir resultado final da execução
        # ====================================================================
        rows = db.session.scalars(
            select(ChecklistExecItemLog.status).where(
                ChecklistExecItemLog.exec_id == exec_.id
            )
        ).all()
        any_fail = any((r or "").lower() == "nao" for r in rows)
        status_calc = "fail" if any_fail else "ok"

        if hasattr(exec_, "result"):
            exec_.result = status_calc

    db.session.commit()
    return _ok(exec_id=exec_.id)


# ====================================================================
# [FIM BLOCO] salvar_execucao
# ====================================================================


# ===============================
# Atalhos úteis
# ===============================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] get_checklist_items
# [RESPONSABILIDADE] Buscar e serializar itens de checklist por modelo para consumo do front
# ====================================================================
def get_checklist_items(modelo: str):
    # 1) Busca o template pelo modelo
    # ====================================================================
    # [BLOCO] BLOCO_DB
    # [NOME] consulta_template_items_por_modelo_db
    # [RESPONSABILIDADE] Buscar template e seus itens associados pelo modelo informado
    # ====================================================================
    template = (
        db.session.query(ChecklistTemplate)
        .filter(ChecklistTemplate.modelo == modelo)
        .first()
    )

    if not template:
        print("❌ Modelo não encontrado:", repr(modelo))
        return []

    # 🔥 PRINT DO ID E MODELO
    print(f"✅ TEMPLATE ENCONTRADO | id={template.id} | modelo='{template.modelo}'")

    # 2) Busca os itens do template
    items = (
        db.session.query(ChecklistTemplateItem)
        .filter(ChecklistTemplateItem.template_id == template.id)
        .order_by(ChecklistTemplateItem.ordem)
        .all()
    )

    print(f"📦 ITENS ENCONTRADOS: {len(items)}")

    # 3) Serializa
    return [
        {
            "id": item.id,
            "ordem": item.ordem,
            "descricao": item.descricao,
            "tempo_seg": item.tempo_seg,
            "tempo_alvo_s": item.tempo_alvo_s,
            "min_s": item.min_s,
            "max_s": item.max_s,
            "bloqueante": item.bloqueante,
            "exige_nota_se_nao": item.exige_nota_se_nao,
            "habilitado": item.habilitado,
            "ncr_tags": item.ncr_tags,
        }
        for item in items
    ]


# ====================================================================
# [FIM BLOCO] get_checklist_items
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] get_template_by_serial
# [RESPONSABILIDADE] Inferir modelo por serial e reutilizar carregamento de template do modelo
# ====================================================================
@gp_checklist_api_bp.get("/template-by-serial/<serial>")
def get_template_by_serial(serial: str):
    modelo = _infer_model_by_serial(serial)
    if not modelo:
        return _err("Não foi possível inferir o modelo por este número de série.", 404)
    # reutiliza get_template
    return get_template(modelo)


# ====================================================================
# [FIM BLOCO] get_template_by_serial
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] items
# [RESPONSABILIDADE] Endpoint para buscar itens do checklist pelo parâmetro de modelo
# ====================================================================
# Endpoint para buscar itens do checklist pelo modelo
@gp_checklist_api_bp.route("/items", methods=["GET"])
def items():
    modelo = request.args.get("modelo")

    if not modelo:
        return jsonify({"error": "Parâmetro 'modelo' é obrigatório"}), 400

    try:
        items = get_checklist_items(modelo)  # Função que busca no banco
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ====================================================================
# [FIM BLOCO] items
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] debug_db
# [RESPONSABILIDADE] Expor contagens de templates e itens para depuração
# ====================================================================
@gp_checklist_api_bp.route("/debug", methods=["GET"])
def debug_db():
    return {
        "templates": ChecklistTemplate.query.count(),
        "items": ChecklistTemplateItem.query.count(),
    }


# ====================================================================
# [FIM BLOCO] debug_db
# ====================================================================


# ====================================================================
# [FIM BLOCO] gp_checklist_api_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: gp_checklist_api_bp
# FUNÇÃO: _iso
# FUNÇÃO: _parse_iso
# FUNÇÃO: _ok
# FUNÇÃO: _err
# FUNÇÃO: _infer_model_by_serial
# FUNÇÃO: list_templates
# BLOCO_DB: consulta_templates_db
# FUNÇÃO: get_template
# BLOCO_DB: consulta_template_por_modelo_db
# BLOCO_DB: consulta_itens_template_db
# FUNÇÃO: upsert_template
# BLOCO_DB: upsert_template_db
# FUNÇÃO: salvar_execucao
# BLOCO_DB: criacao_execucao_checklist_db
# BLOCO_DB: insercao_itens_execucao_db
# BLOCO_DB: inferencia_status_final_db
# FUNÇÃO: get_checklist_items
# BLOCO_DB: consulta_template_items_por_modelo_db
# FUNÇÃO: get_template_by_serial
# FUNÇÃO: items
# FUNÇÃO: debug_db
# ====================================================================
