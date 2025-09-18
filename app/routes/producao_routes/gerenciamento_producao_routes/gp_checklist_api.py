# app/routes/producao_routes/gerenciamento_producao_routes/gp_checklist_api.py
from __future__ import annotations
from flask import Blueprint, request, jsonify
from sqlalchemy import select, delete
from app import db
from app.models.producao_models.gp_models.gp_checklist import (
    ChecklistTemplate, ChecklistItem,
    ChecklistExec, ChecklistExecItem
)
from datetime import datetime

gp_checklist_api_bp = Blueprint(
    "gp_checklist_api_bp",
    __name__,
    url_prefix="/api/gp/checklist"
)

# ---- Regra simples para inferir modelo pelo serial (ajuste depois se desejar) ----
# Regra REAL: 3º dígito do serial define o modelo.
# Ex.: 5 (ano) 8 (mês) 1 (modelo=PM2100) 095 (sequencial)
def inferir_modelo_por_serial(serial: str) -> str | None:
    if not serial:
        return None

    # Mantém só dígitos (caso o QR venha com prefixo/letras/traços)
    s = "".join(ch for ch in serial.strip() if ch.isdigit())
    if len(s) < 3:
        return None

    modelo_digit = s[2]  # 0-based: índice 2 = 3º dígito

    MAP = {
        "1": "PM2100",
        "2": "PM2200",
        "7": "PM700",
        # adicione aqui outros mapeamentos se existirem
    }
    return MAP.get(modelo_digit)


# ===========================
# Templates (CRUD mínimo)
# ===========================

@gp_checklist_api_bp.get("/templates")
def listar_templates():
    modelos = [row.modelo for row in db.session.scalars(select(ChecklistTemplate)).all()]
    return jsonify({"ok": True, "modelos": modelos})

@gp_checklist_api_bp.get("/template/<modelo>")
def obter_template(modelo: str):
    modelo = (modelo or "").strip()
    if not modelo:
        return jsonify({"ok": False, "error": "Modelo é obrigatório."}), 400

    tpl = db.session.scalar(select(ChecklistTemplate).where(ChecklistTemplate.modelo == modelo))
    if not tpl:
        return jsonify({"ok": False, "error": "Template não encontrado para este modelo."}), 404

    return jsonify({"ok": True, "data": tpl.to_dict()})

@gp_checklist_api_bp.post("/template")
def salvar_template():
    """
    Body JSON:
    {
      "modelo": "PM2100",
      "items": [
        {"ordem":1, "descricao":"...", "tempo_seg":30, "ncr_tags":["AJUSTE","REBARBA"]},
        ...
      ]
    }
    """
    data = request.get_json(silent=True) or {}
    modelo = (data.get("modelo") or "").strip()
    items = data.get("items")

    if not modelo:
        return jsonify({"ok": False, "error": "Modelo é obrigatório."}), 400
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"ok": False, "error": "Lista de itens é obrigatória."}), 400
    if len(items) > 10:
        return jsonify({"ok": False, "error": "Máximo de 10 itens."}), 400

    itens_limpos = []
    vistos_descricoes = set()
    for idx, it in enumerate(items, start=1):
        desc = (it.get("descricao") or "").strip()
        if not desc:
            return jsonify({"ok": False, "error": f"Item {idx}: 'descricao' é obrigatória."}), 400
        if desc in vistos_descricoes:
            return jsonify({"ok": False, "error": f"Item {idx}: descrições repetidas não são permitidas."}), 400
        vistos_descricoes.add(desc)

        try:
            tempo = int(it.get("tempo_seg"))
            if tempo <= 0:
                raise ValueError()
        except Exception:
            return jsonify({"ok": False, "error": f"Item {idx}: 'tempo_seg' deve ser inteiro > 0."}), 400

        ordem = it.get("ordem")
        if ordem is None:
            ordem = idx
        else:
            try:
                ordem = int(ordem)
                if ordem <= 0:
                    raise ValueError()
            except Exception:
                return jsonify({"ok": False, "error": f"Item {idx}: 'ordem' inválida."}), 400

        ncr_tags = it.get("ncr_tags") or []
        if not isinstance(ncr_tags, list):
            return jsonify({"ok": False, "error": f"Item {idx}: 'ncr_tags' deve ser lista."}), 400

        itens_limpos.append({
            "ordem": ordem,
            "descricao": desc,
            "tempo_seg": tempo,
            "ncr_tags": ncr_tags[:12],  # limite de bom senso
        })

    # upsert: apaga itens antigos e recria
    tpl = db.session.scalar(select(ChecklistTemplate).where(ChecklistTemplate.modelo == modelo))
    if not tpl:
        tpl = ChecklistTemplate(modelo=modelo)
        db.session.add(tpl)
        db.session.flush()  # para ter tpl.id

    # remove itens antigos
    db.session.execute(delete(ChecklistItem).where(ChecklistItem.template_id == tpl.id))

    # cria itens novos
    for it in sorted(itens_limpos, key=lambda x: x["ordem"]):
        db.session.add(ChecklistItem(
            template_id=tpl.id,
            ordem=it["ordem"],
            descricao=it["descricao"],
            tempo_seg=it["tempo_seg"],
            ncr_tags=it["ncr_tags"],
        ))

    db.session.commit()
    return jsonify({"ok": True, "modelo": modelo})

@gp_checklist_api_bp.get("/by-serial/<serial>")
def obter_template_por_serial(serial: str):
    modelo = inferir_modelo_por_serial(serial)
    if not modelo:
        return jsonify({"ok": False, "error": "Não foi possível inferir o modelo por este número de série."}), 404

    tpl = db.session.scalar(select(ChecklistTemplate).where(ChecklistTemplate.modelo == modelo))
    if not tpl:
        return jsonify({"ok": False, "error": f"Sem template salvo para o modelo {modelo}."}), 404

    return jsonify({"ok": True, "modelo": modelo, "data": tpl.to_dict()})


# ===========================
# Execuções (salvar resultado)
# ===========================

@gp_checklist_api_bp.post("/exec")
def salvar_execucao():
    """
    Body JSON esperado (gerado pela tela de execução):
    {
      "serial": "123...",
      "operador": "Fulano" (opcional),
      "modelo": "PM2100" (opcional),
      "finished_at": "iso-datetime",
      "items": [
        {
          "ordem":1, "descricao":"...", "tempo_estimado_seg":30,
          "status": "ok" | "nok",
          "started_at":"iso", "finished_at":"iso", "elapsed_seg": 28,
          "ncrs":[ {"categoria":"...","descricao":"...","fotoDataUrl":"..."} ]
        }, ...
      ],
      "result": "OK" | "NOK"
    }
    """
    data = request.get_json(silent=True) or {}
    serial = (data.get("serial") or "").strip()
    if not serial:
        return jsonify({"ok": False, "error": "Serial é obrigatório."}), 400

    operador = (data.get("operador") or None)
    modelo = (data.get("modelo") or None)
    finished_at = data.get("finished_at")
    try:
        finished_dt = datetime.fromisoformat(finished_at.replace("Z", "+00:00")) if finished_at else None
    except Exception:
        finished_dt = None

    result = data.get("result")
    if result not in (None, "OK", "NOK"):
        return jsonify({"ok": False, "error": "Campo 'result' inválido."}), 400

    items = data.get("items")
    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "error": "Lista de itens é obrigatória."}), 400

    exec_ = ChecklistExec(
        serial=serial,
        operador=operador,
        modelo=modelo,
        started_at=datetime.utcnow(),
        finished_at=finished_dt,
        result=result
    )
    db.session.add(exec_)
    db.session.flush()  # exec_.id

    for idx, it in enumerate(items, start=1):
        desc = (it.get("descricao") or "").strip()
        if not desc:
            db.session.rollback()
            return jsonify({"ok": False, "error": f"Item {idx}: 'descricao' é obrigatória."}), 400
        try:
            t_est = int(it.get("tempo_estimado_seg"))
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": f"Item {idx}: 'tempo_estimado_seg' inválido."}), 400

        status = it.get("status")
        if status not in (None, "ok", "nok"):
            db.session.rollback()
            return jsonify({"ok": False, "error": f"Item {idx}: 'status' inválido."}), 400

        # datas e elapsed são opcionais
        st_at = it.get("started_at")
        fn_at = it.get("finished_at")
        try:
            st_dt = datetime.fromisoformat(st_at.replace("Z", "+00:00")) if st_at else None
        except Exception:
            st_dt = None
        try:
            fn_dt = datetime.fromisoformat(fn_at.replace("Z", "+00:00")) if fn_at else None
        except Exception:
            fn_dt = None

        elapsed = it.get("elapsed_seg")
        try:
            elapsed = int(elapsed) if elapsed is not None else None
        except Exception:
            elapsed = None

        ncrs = it.get("ncrs") or []
        if not isinstance(ncrs, list):
            db.session.rollback()
            return jsonify({"ok": False, "error": f"Item {idx}: 'ncrs' deve ser lista."}), 400

        db.session.add(ChecklistExecItem(
            exec_id=exec_.id,
            ordem=int(it.get("ordem") or idx),
            descricao=desc,
            tempo_estimado_seg=t_est,
            status=status,
            started_at=st_dt,
            finished_at=fn_dt,
            elapsed_seg=elapsed,
            ncrs=ncrs[:50],  # sanidade
        ))

    db.session.commit()
    return jsonify({"ok": True, "exec_id": exec_.id})
