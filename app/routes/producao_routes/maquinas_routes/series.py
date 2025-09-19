# app/routes/producao_routes/maquinas_routes/series.py

from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from sqlalchemy import or_
from datetime import datetime
import csv
from io import StringIO
from app import db  # usado em ações/rotas dev
from app.routes.producao_routes.painel_routes.order_api import ensure_gp_workorder




# 1) UM ÚNICO BLUEPRINT (sem template_folder relativo frágil)
#    Usaremos render_template('nseries_template/...') nos handlers.
series_bp = Blueprint('series_bp', __name__, url_prefix='/producao/series')


# ---------------------------
# Guard (PIN) só nesta área
# ---------------------------
@series_bp.before_app_request
def _guard_series_only():
    path = (request.path or "")
    # Não intercepta outras páginas do app
    if not path.startswith('/producao/series'):
        return
    # Libera a tela de login da própria área
    if path.endswith('/login'):
        return
    pin = current_app.config.get('SERIES_ADMIN_PIN')
    if pin and not session.get('series_admin_ok'):
        return redirect(url_for('series_bp.series_login'))


# ---------------------------
# Views (HTML)
# ---------------------------
@series_bp.route('/login', methods=['GET', 'POST'])
def series_login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin and pin == current_app.config.get('SERIES_ADMIN_PIN'):
            session['series_admin_ok'] = True
            return redirect(url_for('series_bp.gerenciar_series'))
        return render_template('nseries_template/login.html', error='PIN inválido')
    return render_template('nseries_template/login.html')


@series_bp.route('/', methods=['GET'])
def gerenciar_series():
    return render_template('nseries_template/gerenciar.html')


# ------------------------------------
# Helpers internos (filtros + serialize)
# ------------------------------------
def _build_query_from_args():
    """Monta a query de Serial a partir de request.args (import tardio p/ evitar ciclo)."""
    from app.models.producao_models.seriais import Serial  # import tardio
    q = (request.args.get('q') or '').strip()
    modelo = (request.args.get('modelo') or '').strip()
    status = (request.args.get('status') or '').strip()

    qry = Serial.query
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(Serial.numero_serie.like(like), Serial.modelo.like(like)))
    if modelo:
        qry = qry.filter(Serial.modelo == modelo)
    if status:
        qry = qry.filter(Serial.status == status)

    return qry, Serial


def _serialize_serial(s):
    return {
        "id": s.id,
        "montagem_id": s.montagem_id,
        "modelo": s.modelo,
        "numero_serie": s.numero_serie,
        "status": s.status,
        "printed_count": s.printed_count or 0,
        "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
        "created_by": s.created_by or "",
    }


# ---------------------------
# API principal (ÚNICA /api)
# ---------------------------
@series_bp.route('/api', methods=['GET'])
def api_series_list():
    qry, Serial = _build_query_from_args()
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 200)

    pag = qry.order_by(Serial.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    items = [_serialize_serial(s) for s in pag.items]
    return jsonify({"items": items, "page": pag.page, "pages": pag.pages, "total": pag.total})


@series_bp.route('/api/<int:serial_id>', methods=['GET'])
def api_detail(serial_id):
    from app.models.producao_models.seriais import Serial, SerialEvent  # import tardio
    s = Serial.query.get_or_404(serial_id)
    events = s.events.order_by(SerialEvent.created_at.desc()).all()
    ev = [{
        "id": e.id,
        "kind": e.kind,
        "payload": e.payload,
        "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
        "created_by": e.created_by,
    } for e in events]
    return jsonify(_serialize_serial(s) | {"events": ev})


@series_bp.route('/api/<int:serial_id>/reprint', methods=['POST'])
def api_reprint(serial_id):
    from app.models.producao_models.seriais import Serial, SerialEvent  # import tardio
    s = Serial.query.get_or_404(serial_id)
    motivo = (request.json or {}).get('motivo') if request.is_json else request.form.get('motivo')
    user = ( (request.json or {}).get('user') if request.is_json else request.form.get('user') ) or 'Sistema'

    s.printed_count = (s.printed_count or 0) + 1
    ev = SerialEvent(
        serial_id=serial_id,
        kind='reprint',
        payload={
            "motivo": (motivo or '').strip(),
            "reprint_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "reprint_by": user
        },
        created_by=user
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify({"ok": True, "printed_count": s.printed_count})


@series_bp.route('/api/<int:serial_id>/invalidate', methods=['POST'])
def api_invalidate(serial_id):
    from app.models.producao_models.seriais import Serial, SerialEvent  # import tardio
    s = Serial.query.get_or_404(serial_id)

    motivo = (request.json or {}).get('motivo') if request.is_json else request.form.get('motivo')
    user = ( (request.json or {}).get('user') if request.is_json else request.form.get('user') ) or 'Sistema'

    s.status = 'invalid'
    ev = SerialEvent(
        serial_id=serial_id,
        kind='invalidate',
        payload={"motivo": (motivo or '').strip()},
        created_by=user
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify({"ok": True, "status": s.status})


@series_bp.route('/api/export', methods=['GET'])
def api_export():
    qry, Serial = _build_query_from_args()
    rows = qry.order_by(Serial.created_at.desc()).all()
    data = [_serialize_serial(s) for s in rows]

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()) if data else
                            ["id","montagem_id","modelo","numero_serie","status","printed_count","created_at","created_by"])
    writer.writeheader()
    for r in data:
        writer.writerow(r)
    buf.seek(0)
    return current_app.response_class(
        buf.read(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=series_export.csv'}
    )


# ---------------------------
# Rotas DEV (diagnóstico)
# ---------------------------
@series_bp.route('/dev/init', methods=['GET'])
def dev_init_serials():
    # cria qualquer tabela faltando (somente em dev)
    from app.models.producao_models.seriais import Serial, SerialEvent  # import tardio
    db.create_all()
    return jsonify({"ok": True, "msg": "Tabelas criadas (se não existiam): serials, serial_events"})


@series_bp.route('/dev/seed', methods=['GET'])
def dev_seed():
    from app.models.producao_models.seriais import Serial, SerialEvent  # import tardio

    existente = Serial.query.filter_by(numero_serie='TST0001').first()
    if existente:
        return jsonify({"ok": True, "created": False, "msg": "Serial TST0001 já existe"})

    s = Serial(
        montagem_id=None,
        modelo='PM2100',
        numero_serie='TST0001',
        status='valid',
        printed_count=1,
        created_by='Seeder'
    )
    db.session.add(s)
    db.session.flush()

    # garante a ordem de produção para este serial/modelo
    ensure_gp_workorder(db.session, serial=str(s.numero_serie), modelo=str(s.modelo))


    ev1 = SerialEvent(serial_id=s.id, kind='mounted', payload={"obs": "seed dev"}, created_by='Seeder')
    ev2 = SerialEvent(
        serial_id=s.id,
        kind='first_print',
        payload={"reprint_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), "reprint_by": "Seeder"},
        created_by='Seeder'
    )
    db.session.add_all([ev1, ev2])
    db.session.commit()

    return jsonify({"ok": True, "created": True, "id": s.id})


@series_bp.route('/dev/backfill', methods=['GET'])
def dev_backfill_serials():
    from app.models.producao_models.montagem import Montagem               # import tardio
    from app.models.producao_models.seriais import Serial, SerialEvent     # import tardio

    created, updated, skipped = 0, 0, 0
    monts = Montagem.query.order_by(Montagem.data_hora.asc()).all()

    for m in monts:
        s = Serial.query.filter_by(numero_serie=m.serial).first()
        if s:
            changed = False
            if s.montagem_id is None:
                s.montagem_id = m.id; changed = True
            if not s.modelo:
                s.modelo = m.modelo; changed = True
            new_status = 'valid' if m.status == 'OK' else 'invalid'
            if s.status != new_status:
                s.status = new_status; changed = True
            desired_count = m.label_print_count or (1 if m.label_printed else 0)
            if (s.printed_count or 0) < desired_count:
                s.printed_count = desired_count; changed = True
            if changed:
                updated += 1
            else:
                skipped += 1
            continue

        s = Serial(
            montagem_id=m.id,
            modelo=m.modelo,
            numero_serie=m.serial,
            status='valid' if m.status == 'OK' else 'invalid',
            printed_count=m.label_print_count or (1 if m.label_printed else 0),
            created_at=m.created_at or m.data_hora or datetime.utcnow(),
            created_by=m.usuario or 'Operador'
        )
        db.session.add(s)
        db.session.flush()
        db.session.add(SerialEvent(
            serial_id=s.id,
            kind='mounted',
            payload={"from": "backfill", "montagem_id": m.id,
                     "data_hora": (m.data_hora.strftime("%Y-%m-%d %H:%M:%S") if m.data_hora else None)},
            created_by=s.created_by
        ))
        created += 1

    db.session.commit()
    return jsonify({"ok": True, "created": created, "updated": updated, "skipped": skipped})


@series_bp.route('/dev/debug', methods=['GET'])
def dev_debug_serials():
    from app.models.producao_models.seriais import Serial  # import tardio
    total = Serial.query.count()
    items = (Serial.query.order_by(Serial.created_at.desc()).limit(10).all())
    sample = [{
        "id": s.id,
        "modelo": s.modelo,
        "numero_serie": s.numero_serie,
        "status": s.status,
        "printed_count": s.printed_count,
        "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else None,
        "created_by": s.created_by,
    } for s in items]
    return jsonify({"total": total, "sample": sample})
