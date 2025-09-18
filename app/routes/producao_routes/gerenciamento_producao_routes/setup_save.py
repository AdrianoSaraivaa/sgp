# app/routes/producao_routes/gerenciamento_producao_routes/setup_save.py
from flask import Blueprint, request, jsonify
from app import db
from sqlalchemy import inspect
from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig  # seu arquivo renomeado

gp_setup_save_bp = Blueprint("gp_setup_save_bp", __name__)

def _ensure_tables():
    """DEV: cria gp_model e gp_bench_config se ainda não existirem."""
    insp = inspect(db.engine)
    if not insp.has_table("gp_model") or not insp.has_table("gp_bench_config"):
        db.create_all()

# aceitar com e sem barra final
@gp_setup_save_bp.route("/producao/gp/setup/save", methods=["POST"])
@gp_setup_save_bp.route("/producao/gp/setup/save/", methods=["POST"])
def save_setup():
    _ensure_tables()  # <<< CRUCIAL

    payload = request.get_json(force=True) or {}
    modelo = payload.get("modelo")
    benches = payload.get("benches", {})

    if not modelo or not isinstance(benches, dict):
        return jsonify({"ok": False, "error": "payload_invalido"}), 400

    # upsert do modelo
    model = GPModel.query.filter_by(nome=modelo).first()
    if not model:
        model = GPModel(nome=modelo)
        db.session.add(model)
        db.session.flush()

    # apaga configs antigas e recria
    GPBenchConfig.query.filter_by(model_id=model.id).delete()

    for bench_id, cfg in benches.items():
        db.session.add(GPBenchConfig(
            model_id=model.id,
            bench_id=bench_id,
            ativo=bool(cfg.get("ativo")),
            obrigatorio=bool(cfg.get("obrigatorio")),
            tempo_min=cfg.get("tempo_min"),
            tempo_esperado=cfg.get("tempo_esperado"),
            tempo_max=cfg.get("tempo_max"),
            operador=(cfg.get("operador") or "")[:120],
            responsavel=(cfg.get("responsavel") or "")[:120],
            observacoes=cfg.get("observacoes") or ""
        ))

    db.session.commit()
    return jsonify({"ok": True})



# GET /producao/gp/setup/load?modelo=PM2100
@gp_setup_save_bp.get("/producao/gp/setup/load")
def load_setup():
    from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig  # garante import local
    modelo = request.args.get("modelo")
    if not modelo:
        return jsonify({"ok": False, "error": "modelo_requerido"}), 400

    # busca modelo
    model = GPModel.query.filter_by(nome=modelo).first()
    if not model:
        # default “zerado”, mantendo obrigatórias ativas
        def bench(ativo, obrig):
            return {
                "ativo": bool(ativo),
                "obrigatorio": bool(obrig),
                "tempo_min": None, "tempo_esperado": None, "tempo_max": None,
                "operador": "", "responsavel": "", "observacoes": "", "anexos": []
            }
        benches = {
            "sep": bench(True,  True),
            "b1":  bench(False, False),
            "b2":  bench(False, False),
            "b3":  bench(False, False),
            "b4":  bench(False, False),
            "b5":  bench(True,  True),
            "b6":  bench(False, False),
            "b7":  bench(False, False),
            "b8":  bench(True,  True),
        }
        return jsonify({"ok": True, "modelo": modelo, "benches": benches})

    # tem no banco: monta dict por bench_id
    rows = GPBenchConfig.query.filter_by(model_id=model.id).all()
    benches = {}
    for r in rows:
        benches[r.bench_id] = {
            "ativo": r.ativo,
            "obrigatorio": r.obrigatorio,
            "tempo_min": r.tempo_min,
            "tempo_esperado": r.tempo_esperado,
            "tempo_max": r.tempo_max,
            "operador": r.operador or "",
            "responsavel": r.responsavel or "",
            "observacoes": r.observacoes or "",
            "anexos": []
        }

    # garante que todas existam (preenche faltantes com padrões)
    for bid, obrig in {"sep": True, "b1": False, "b2": False, "b3": False, "b4": False,
                       "b5": True, "b6": False, "b7": False, "b8": True}.items():
        if bid not in benches:
            benches[bid] = {
                "ativo": obrig, "obrigatorio": obrig,
                "tempo_min": None, "tempo_esperado": None, "tempo_max": None,
                "operador": "", "responsavel": "", "observacoes": "", "anexos": []
            }

    return jsonify({"ok": True, "modelo": model.nome, "benches": benches})




