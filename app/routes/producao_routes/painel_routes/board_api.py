# app/routes/producao_routes/painel_routes/board_api.py
from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import inspect, or_
from datetime import timezone, timedelta, datetime, date
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage
from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig
from app.routes.producao_routes.painel_routes.rop_service import list_rop_needs

gp_painel_api_bp = Blueprint(
    "gp_painel_api_bp", __name__, url_prefix="/producao/gp/painel/api"
)


def _ensure_tables():
    insp = inspect(db.engine)
    for t in ("gp_work_order", "gp_work_stage", "gp_model", "gp_bench_config"):
        if not insp.has_table(t):
            db.create_all()
            break


def _enabled_seq_for_model(modelo: str):
    seq = []
    try:
        m = (
            GPModel.query.filter(
                or_(
                    getattr(GPModel, "nome") == modelo,
                    getattr(GPModel, "code", modelo) == modelo,
                )
            ).first()
            or GPModel.query.filter_by(nome=modelo).first()
        )
        if m:
            cfgs = GPBenchConfig.query.filter_by(model_id=m.id).all()
            cfgs.sort(key=lambda r: getattr(r, "bench_num", 0))
            for r in cfgs:
                bid = getattr(r, "bench_id", None) or (
                    f"b{getattr(r, 'bench_num', '')}".lower()
                )
                if bid and getattr(r, "enabled", getattr(r, "habilitar", True)):
                    seq.append(bid)
    except Exception:
        pass
    if not seq:
        seq = [f"b{i}" for i in range(1, 9)]
    return seq


@gp_painel_api_bp.get("/board")
def board_data():
    _ensure_tables()

    titles = {
        "sep": "ESTOQUE",
        "b1": "BANCADA 1",
        "b2": "BANCADA 2",
        "b3": "BANCADA 3",
        "b4": "BANCADA 4",
        "b5": "HI-POT",
        "b6": "BANCADA 6",
        "b7": "BANCADA 7",
        "b8": "CHECK-LIST",
        "final": "FINALIZADO",
    }
    columns = {
        cid: {"id": cid, "title": title, "items": []} for cid, title in titles.items()
    }

    EXPECTED_FALLBACK = {
        "b1": 45 * 60,
        "b2": 40 * 60,
        "b3": 35 * 60,
        "b4": 30 * 60,
        "b5": 20 * 60,
        "b6": 30 * 60,
        "b7": 20 * 60,
        "b8": 15 * 60,
    }

    expected_cache = {}

    def expected_for(modelo, bench_id):
        if bench_id not in EXPECTED_FALLBACK:
            return None
        if modelo not in expected_cache:
            expected_cache[modelo] = {}
            try:
                m = (
                    GPModel.query.filter(
                        or_(
                            getattr(GPModel, "nome") == modelo,
                            getattr(GPModel, "code", modelo) == modelo,
                        )
                    ).first()
                    or GPModel.query.filter_by(nome=modelo).first()
                )
            except Exception:
                m = GPModel.query.filter_by(nome=modelo).first()
            if m:
                for r in GPBenchConfig.query.filter_by(model_id=m.id).all():
                    bid = getattr(r, "bench_id", None) or (
                        f"b{getattr(r,'bench_num','')}".lower()
                    )
                    if bid:
                        expected_cache[modelo][bid] = getattr(r, "tempo_esperado", None)
        return expected_cache.get(modelo, {}).get(bench_id) or EXPECTED_FALLBACK.get(
            bench_id
        )

    orders = GPWorkOrder.query.order_by(GPWorkOrder.updated_at.desc()).all()

    for o in orders:
        col_id = o.current_bench if o.current_bench in columns else "sep"
        seq = _enabled_seq_for_model(o.modelo)
        idx = {b: i for i, b in enumerate(seq)}

        if col_id == "sep":
            since_iso = None
        elif col_id == "final":
            last = (
                GPWorkStage.query.filter_by(order_id=o.id)
                .order_by(GPWorkStage.finished_at.desc())
                .first()
            )
            if last and last.finished_at:
                dt = last.finished_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                since_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                since_iso = None
        else:
            st_open = (
                GPWorkStage.query.filter_by(
                    order_id=o.id, bench_id=col_id, finished_at=None
                )
                .order_by(GPWorkStage.started_at.desc())
                .first()
            )
            if st_open and st_open.started_at:
                dt = st_open.started_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_local = dt.astimezone(timezone(timedelta(hours=-3)))
                since_iso = dt_local.strftime("%d/%m/%Y %H:%M:%S")
            else:
                since_iso = None

        returned = False
        try:
            max_idx = -1
            finished = GPWorkStage.query.filter(
                GPWorkStage.order_id == o.id, GPWorkStage.finished_at.isnot(None)
            ).all()
            for s in finished:
                bi = idx.get(s.bench_id, -1)
                if bi > max_idx:
                    max_idx = bi
            cur_i = idx.get(col_id, -1)
            returned = max_idx > cur_i >= 0
        except Exception:
            returned = False

        item = {
            "serial": o.serial,
            "modelo": o.modelo,
            "since": since_iso,
            "expected_s": expected_for(o.modelo, col_id),
            "hipot_flag": bool(getattr(o, "hipot_flag", False)),
            "returned": returned,
            "result": None,
            "rework_flag": False,
            "workstation": None,
            "finished_at": None,
        }

        try:
            if col_id not in ("sep", "final"):
                st_open = (
                    GPWorkStage.query.filter_by(
                        order_id=o.id, bench_id=col_id, finished_at=None
                    )
                    .order_by(GPWorkStage.started_at.desc())
                    .first()
                )
                if st_open:
                    item["result"] = getattr(st_open, "result", None)
                    item["rework_flag"] = bool(getattr(st_open, "rework_flag", False))
                    item["workstation"] = getattr(st_open, "workstation", None)
            elif col_id == "final":
                last_stage = (
                    GPWorkStage.query.filter_by(order_id=o.id)
                    .order_by(GPWorkStage.finished_at.desc())
                    .first()
                )
                if last_stage and last_stage.finished_at:
                    item["finished_at"] = last_stage.finished_at.isoformat()
        except Exception:
            pass

        columns[col_id]["items"].append(item)

    for cid, col in columns.items():
        col["count"] = len(col["items"])

    ordered = [
        columns[cid]
        for cid in ["sep", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "final"]
    ]

    needs = []
    needs_banner = ""
    try:
        needs = list_rop_needs(db.session) or []
        parts = []
        for row in needs:
            sug = int(row.get("sugerido") or 0)  # corrigido aqui
            mc = (
                row.get("model_code")
                or row.get("modelo")
                or row.get("codigo")
                or row.get("code")
            )
            if sug > 0 and mc:
                parts.append(f"{mc} +{sug}")
        if parts:
            needs_banner = "Montar: " + " • ".join(parts)
    except Exception:
        needs = []
        needs_banner = ""

    payload = {
        "ok": True,
        "columns": ordered,
        "needs": needs,
        "needs_banner": needs_banner,
    }
    return jsonify(payload)


@gp_painel_api_bp.get("/kpis/dia")
def kpis_dia():
    data_str = request.args.get("data")
    modelo = request.args.get("modelo")

    try:
        if data_str:
            dia = datetime.strptime(data_str, "%Y-%m-%d").date()
        else:
            dia = date.today()
    except Exception:
        return jsonify({"ok": False, "error": "data_invalida"}), 400

    start_dt = datetime.combine(dia, datetime.min.time())
    end_dt = datetime.combine(dia, datetime.max.time())

    q = GPWorkOrder.query.filter(
        GPWorkOrder.created_at >= start_dt, GPWorkOrder.created_at <= end_dt
    )
    if modelo:
        q = q.filter_by(modelo=modelo)
    orders = q.all()

    throughput = len([o for o in orders if getattr(o, "finished_at", None)])
    fpy_count = 0
    rework_count = 0
    hipot_total = 0
    hipot_ok = 0
    avg_cycle_times = {}

    for o in orders:
        stages = GPWorkStage.query.filter_by(order_id=o.id).all()
        if not stages:
            continue
        has_rework = any(getattr(s, "rework_flag", False) for s in stages)
        if has_rework:
            rework_count += 1
        else:
            fpy_count += 1

        for s in stages:
            if s.started_at and s.finished_at:
                delta = (s.finished_at - s.started_at).total_seconds()
                avg_cycle_times.setdefault(s.bench_id, []).append(delta)

            if s.bench_id == "b5":
                hipot_total += 1
                if getattr(s, "result", "").upper() in ("OK", "APR"):
                    hipot_ok += 1

    avg_cycle = {
        b: (sum(v) / len(v) if v else None) for b, v in avg_cycle_times.items()
    }

    result = {
        "ok": True,
        "data": dia.isoformat(),
        "modelo": modelo,
        "throughput": throughput,
        "fpy_rate": fpy_count / len(orders) if orders else 0,
        "rework_rate": rework_count / len(orders) if orders else 0,
        "avg_cycle_time": avg_cycle,
        "hipot_ok_rate": (hipot_ok / hipot_total) if hipot_total else None,
    }
    return jsonify(result)


@gp_painel_api_bp.get("/needs")
def needs_data():
    try:
        needs = list_rop_needs(db.session) or []
        return jsonify(needs), 200
    except Exception:
        return jsonify([]), 200
