from flask import Blueprint, jsonify
from app import db
from sqlalchemy import inspect
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage
from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig

gp_painel_api_bp = Blueprint(
    "gp_painel_api_bp",
    __name__,
    url_prefix="/producao/gp/painel/api"
)

def _ensure_tables():
    insp = inspect(db.engine)
    for t in ("gp_work_order", "gp_work_stage", "gp_model", "gp_bench_config"):
        if not insp.has_table(t):
            db.create_all()
            break

@gp_painel_api_bp.get("/board")
def board_data():
    _ensure_tables()

    titles = {
        "sep":   "ESTOQUE",
        "b1":    "BANCADA 1",
        "b2":    "BANCADA 2",
        "b3":    "BANCADA 3",
        "b4":    "BANCADA 4",
        "b5":    "HI-POT",
        "b6":    "BANCADA 6",
        "b7":    "BANCADA 7",
        "b8":    "CHECK-LIST",
        "final": "FINALIZADO",
    }
    columns = {cid: {"id": cid, "title": title, "items": []} for cid, title in titles.items()}

    # cache simples de receita por modelo -> bench_id -> tempo_esperado (s)
    expected_cache = {}

    def expected_for(modelo, bench_id):
        if bench_id not in {"b1","b2","b3","b4","b5","b6","b7","b8"}:
            return None
        if modelo not in expected_cache:
            expected_cache[modelo] = {}
            m = GPModel.query.filter_by(nome=modelo).first()
            if m:
                for r in GPBenchConfig.query.filter_by(model_id=m.id).all():
                    expected_cache[modelo][r.bench_id] = r.tempo_esperado
        return expected_cache.get(modelo, {}).get(bench_id)

    orders = GPWorkOrder.query.order_by(GPWorkOrder.updated_at.desc()).all()

    for o in orders:
        col_id = o.current_bench if o.current_bench in columns else "sep"

        # when started (since)
        if col_id == "sep":
            since_dt = o.created_at
        elif col_id == "final":
            # mostra quando finalizou a última etapa
            last = (GPWorkStage.query
                    .filter_by(order_id=o.id)
                    .order_by(GPWorkStage.finished_at.desc())
                    .first())
            since_dt = last.finished_at if last and last.finished_at else o.updated_at or o.created_at
        else:
            st = (GPWorkStage.query
                  .filter_by(order_id=o.id, bench_id=col_id)
                  .order_by(GPWorkStage.started_at.desc())
                  .first())
            since_dt = st.started_at if st and st.started_at else (o.updated_at or o.created_at)

        item = {
            "serial": o.serial,
            "modelo": o.modelo,
            "since":  (since_dt.isoformat() if since_dt else None),
            "expected_s": expected_for(o.modelo, col_id),
            "hipot_flag": bool(o.hipot_flag)  # 🔴 NOVO: manda flag de reprovação
}

        columns[col_id]["items"].append(item)

    ordered = [columns[cid] for cid in ["sep","b1","b2","b3","b4","b5","b6","b7","b8","final"]]
    return jsonify({"ok": True, "columns": ordered})
