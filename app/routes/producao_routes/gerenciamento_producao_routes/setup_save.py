# app/routes/producao_routes/gerenciamento_producao_routes/setup_save.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
from sqlalchemy import inspect
from typing import Dict, Any

from app import db
from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig

gp_setup_save_bp = Blueprint("gp_setup_save_bp", __name__)

# ------------------------------
# Helpers
# ------------------------------
REQUIRED_BENCHES = {"b5": True, "b8": True, "sep": True}
ALL_BENCHES = ["sep", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]


def _ensure_tables() -> None:
    """Cria gp_model e gp_bench_config se ainda não existirem (ambiente de dev)."""
    insp = inspect(db.engine)
    if not insp.has_table("gp_model") or not insp.has_table("gp_bench_config"):
        db.create_all()


def _normalize_bench_id(bid: str) -> str:
    bid = (bid or "").strip().lower()
    if bid in ALL_BENCHES:
        return bid
    # aceita padrões como "B1", "1" → b1
    bid = bid.lower().replace(" ", "")
    if bid.startswith("b") and len(bid) == 2 and bid[1].isdigit():
        return bid
    if bid.isdigit():
        return f"b{bid}"
    return bid


def _defaults_for(bid: str) -> Dict[str, Any]:
    obrig = REQUIRED_BENCHES.get(bid, False)
    return {
        "ativo": obrig,
        "obrigatorio": obrig,
        "tempo_min": None,
        "tempo_esperado": None,
        "tempo_max": None,
        "operador": "",
        "responsavel": "",
        "observacoes": "",
        "anexos": [],
    }


# ------------------------------
# POST /producao/gp/setup/save
# body: {"modelo": "PM2100", "benches": { "b1": {...}, "b2": {...} } }
# ------------------------------
@gp_setup_save_bp.post("/producao/gp/setup/save")
def save_setup():
    _ensure_tables()

    payload = request.get_json(silent=True) or {}
    modelo = (payload.get("modelo") or "").strip()
    benches = payload.get("benches") or {}

    if not modelo:
        return jsonify({"ok": False, "error": "modelo_requerido"}), 400

    # garante modelo
    model = GPModel.query.filter_by(nome=modelo).first()
    if not model:
        model = GPModel(nome=modelo)
        db.session.add(model)
        db.session.flush()  # cria id

    # valida e aplica por bancada
    for raw_bid, data in benches.items():
        bid = _normalize_bench_id(raw_bid)
        if bid not in ALL_BENCHES:
            continue

        # defaults + merge
        cfg = _defaults_for(bid)
        if isinstance(data, dict):
            for key in cfg.keys():
                cfg[key] = data.get(key, cfg[key])

        # valida obrigatórias
        if bid in REQUIRED_BENCHES:
            cfg["ativo"] = True
            cfg["obrigatorio"] = True

        # valida tempos (quando informados)
        tmin = cfg.get("tempo_min")
        ttar = cfg.get("tempo_esperado")
        tmax = cfg.get("tempo_max")

        def _as_int(x):
            try:
                return int(x) if x is not None and str(x) != "" else None
            except Exception:
                return None

        tmin = _as_int(tmin)
        ttar = _as_int(ttar)
        tmax = _as_int(tmax)

        if tmin is not None and tmin < 0:
            return jsonify({"ok": False, "error": f"{bid}: tempo_min_invalido"}), 400
        if ttar is not None and ttar < 0:
            return (
                jsonify({"ok": False, "error": f"{bid}: tempo_esperado_invalido"}),
                400,
            )
        if tmax is not None and tmax < 0:
            return jsonify({"ok": False, "error": f"{bid}: tempo_max_invalido"}), 400
        if tmin is not None and ttar is not None and tmin > ttar:
            return (
                jsonify({"ok": False, "error": f"{bid}: tempo_min_maior_que_esperado"}),
                400,
            )
        if ttar is not None and tmax is not None and ttar > tmax:
            return (
                jsonify({"ok": False, "error": f"{bid}: tempo_esperado_maior_que_max"}),
                400,
            )

        # UPSERT
        row = GPBenchConfig.query.filter_by(model_id=model.id, bench_id=bid).first()
        if not row:
            row = GPBenchConfig(model_id=model.id, bench_id=bid)
            db.session.add(row)

        row.ativo = bool(cfg.get("ativo"))
        row.obrigatorio = bool(cfg.get("obrigatorio"))
        row.tempo_min = tmin
        row.tempo_esperado = ttar
        row.tempo_max = tmax
        row.operador = (cfg.get("operador") or "").strip() or None
        row.responsavel = (cfg.get("responsavel") or "").strip() or None
        row.observacoes = (cfg.get("observacoes") or "").strip() or None

    db.session.commit()
    return jsonify({"ok": True, "modelo": model.nome})


# ------------------------------
# GET /producao/gp/setup/load?modelo=PM2100
# Retorna dicionário consolidado por bancada para preencher a UI.
# ------------------------------
@gp_setup_save_bp.get("/producao/gp/setup/load")
def load_setup():
    _ensure_tables()

    modelo = (request.args.get("modelo") or "").strip()
    if not modelo:
        return jsonify({"ok": False, "error": "modelo_requerido"}), 400

    model = GPModel.query.filter_by(nome=modelo).first()
    benches: Dict[str, Dict[str, Any]] = {
        bid: _defaults_for(bid) for bid in ALL_BENCHES
    }

    if model:
        rows = GPBenchConfig.query.filter_by(model_id=model.id).all()
        for r in rows:
            bid = _normalize_bench_id(getattr(r, "bench_id", ""))
            if not bid:
                continue
            benches[bid].update(
                {
                    "ativo": bool(getattr(r, "ativo", benches[bid]["ativo"])),
                    "obrigatorio": bool(
                        getattr(r, "obrigatorio", benches[bid]["obrigatorio"])
                    ),
                    "tempo_min": getattr(r, "tempo_min", None),
                    "tempo_esperado": getattr(r, "tempo_esperado", None),
                    "tempo_max": getattr(r, "tempo_max", None),
                    "operador": getattr(r, "operador", "") or "",
                    "responsavel": getattr(r, "responsavel", "") or "",
                    "observacoes": getattr(r, "observacoes", "") or "",
                    "anexos": [],
                }
            )

    # reforça obrigatórias
    for bid in REQUIRED_BENCHES.keys():
        benches[bid]["ativo"] = True
        benches[bid]["obrigatorio"] = True

    return jsonify({"ok": True, "modelo": modelo, "benches": benches})
