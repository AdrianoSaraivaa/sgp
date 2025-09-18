
# app/routes/producao_routes/maquinas_routes/montagens.py
from __future__ import annotations
from datetime import datetime
from flask import Blueprint, request, jsonify, abort
from app import db
# Use the SQLAlchemy models instead of the dataclasses. Import from the
# auto-generated models_sqla package to ensure that ``.query`` is available.
from app.models_sqla import Montagem, LabelReprintLog, GPWorkOrder
from app.routes.producao_routes.maquinas_routes.consumo_service import (
    estornar_reserva_componentes,
)
# Use the real serial generator from app.services.serials instead of the stub.
from app.services.serials import generate_serials
from sqlalchemy import select  # precisa para as queries com with_for_update
from app.models_sqla import EstruturaMaquina  # BOM está nessa tabela

import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)





montagens_bp = Blueprint("montagens_bp", __name__, url_prefix="/producao/montagem")

@montagens_bp.route("/listar", methods=["GET"])
def listar_montagens():
    q = Montagem.query.order_by(Montagem.id.desc()).limit(300).all()
    return jsonify([m.as_dict() for m in q])
@montagens_bp.route("/criar", methods=["POST"])
def criar_montagens():
    """
    Espera JSON: { modelo: "PM2100", quantidade: 3, usuario: "Operador" }
    Gera 'quantidade' de linhas, cada uma com serial único (a sua lógica de serial entra aqui).
    """
    data = request.get_json() or {}
    modelo = (data.get("modelo") or "").strip()
    qtd = int(data.get("quantidade") or 0)
    usuario = (data.get("usuario") or "Operador").strip()
    if not modelo or qtd <= 0:
        return abort(400, "Informe modelo e quantidade > 0.")

    criadas = []
    for _ in range(qtd):
        # TODO: chame seu gerador real de serial (ex.: app.services.serials.next_serial(modelo))
        serial = gerar_serial_stub(modelo)  # SUBSTITUA PELO SEU GERADOR
        # Preenche campos obrigatórios de Montagem (status, label_printed, label_print_count, created_at, updated_at)
        m = Montagem(
            modelo=modelo,
            serial=serial,
            data_hora=datetime.utcnow(),
            usuario=usuario,
            status="OK",
            label_printed=False,
            label_print_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(m)
        criadas.append(m)

    # Commit das montagens
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return abort(400, f"Erro ao salvar (serial pode já existir): {e}")

    # --- Enfileira no Painel (bancada SEP) para cada serial criado (idempotente) ---
    warn = None
    try:
        for m in criadas:
            # Se já existir, não cria de novo (idempotente)
            wo = GPWorkOrder.query.filter_by(serial=m.serial).first()
            if not wo:
                wo = GPWorkOrder(
                    serial=m.serial,
                    modelo=m.modelo,
                    current_bench="sep",
                    status="queued"
                )
                db.session.add(wo)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Não derruba a montagem; apenas reporta aviso no JSON
        warn = f"Falha ao enfileirar no Painel (SEP): {e}"

    resp = {"ok": True, "itens": [m.as_dict() for m in criadas]}
    if warn:
        resp["warning"] = warn
    return jsonify(resp)


def gerar_serial_stub(modelo: str) -> str:
    """
    Gera um único número de série para o modelo informado usando o gerador
    real de números de série (``app.services.serials.generate_serials``).

    Este wrapper mantém a mesma assinatura do stub original. Ele delega ao
    gerador de números de série configurado no serviço ``serials`` e
    retorna somente o primeiro serial da lista.
    """
    try:
        serials = generate_serials(modelo, 1)
        return serials[0] if serials else ""
    except Exception as e:
        # fallback: timestamp modulo in case the generator fails
        base = int(datetime.utcnow().timestamp()) % 1000000
        return f"{base}"

    

@montagens_bp.route("/cancelar/<int:montagem_id>", methods=["POST"])
def cancelar_montagem(montagem_id: int):
    """
    Marca como CANCELADA. NÃO apaga nem permite repetir serial.
    Não estorna peças ao estoque (apenas marca status).
    
    Body: { motivo: "...", usuario: "..." }
    """
    data = request.get_json() or {}
    motivo = (data.get("motivo") or "").strip()
    usuario = (data.get("usuario") or "Operador").strip()
    if not motivo:
        return abort(400, "Motivo é obrigatório.")

    m = Montagem.query.get_or_404(montagem_id)

    if m.status == "CANCELADA":
        return jsonify({"ok": True, "message": "Já estava cancelada."})

    try:
        m.status = "CANCELADA"
        m.cancel_reason = motivo
        m.cancel_at = datetime.utcnow()
        m.cancel_by = usuario
        db.session.add(m)
        db.session.commit()

        return jsonify({"ok": True, "message": "Montagem cancelada."})

    except Exception as e:
        db.session.rollback()
        logger.exception("Erro ao cancelar montagem")
        return jsonify({"ok": False, "erro": str(e)}), 500




@montagens_bp.route("/reprints/<int:montagem_id>", methods=["GET"])
def listar_reprints_por_id(montagem_id: int):
    m = Montagem.query.get_or_404(montagem_id)
    logs = (LabelReprintLog.query
            .filter_by(montagem_id=m.id)
            .order_by(LabelReprintLog.id.desc())
            .all())
    return jsonify([{
        "id": l.id,
        "montagem_id": l.montagem_id,
        "motivo": l.motivo,
        "reprint_by": l.reprint_by,
        "reprint_at": l.reprint_at.strftime("%Y-%m-%d %H:%M")
    } for l in logs])




@montagens_bp.route("/reprints/by-serial/<serial>", methods=["GET"])
def listar_reprints_por_serial(serial: str):
    m = Montagem.query.filter_by(serial=serial).first()
    if not m:
        return jsonify([])  # vazio se não achar
    return listar_reprints_por_id(m.id)





@montagens_bp.route("/export/csv", methods=["GET"])
def exportar_montagens_csv():
    """
    Query params:
      - date_from=YYYY-MM-DD
      - date_to=YYYY-MM-DD
      - modelo=PM2100 (opcional)
      - status=OK|CANCELADA (opcional)
    """
    q = Montagem.query

    # Datas
    df = request.args.get("date_from")
    dt = request.args.get("date_to")
    if df:
        try:
            dt_from = datetime.strptime(df, "%Y-%m-%d")
            q = q.filter(Montagem.data_hora >= dt_from)
        except Exception:
            pass
    if dt:
        try:
            dt_to = datetime.strptime(dt, "%Y-%m-%d")
            # incluir o dia todo
            q = q.filter(Montagem.data_hora < dt_to.replace(hour=23, minute=59, second=59))
        except Exception:
            pass

    # Modelo / Status
    modelo = (request.args.get("modelo") or "").strip()
    status = (request.args.get("status") or "").strip().upper()
    if modelo:
        q = q.filter(Montagem.modelo == modelo)
    if status in ("OK", "CANCELADA"):
        q = q.filter(Montagem.status == status)

    itens = q.order_by(Montagem.id.desc()).all()

    # Monta CSV
    lines = ["id;modelo;serial;data_hora;usuario;status;label_printed;label_print_count"]
    for m in itens:
        lines.append(";".join([
            str(m.id),
            m.modelo,
            m.serial,
            m.data_hora.strftime("%Y-%m-%d %H:%M"),
            m.usuario or "",
            m.status,
            "1" if m.label_printed else "0",
            str(m.label_print_count or 0),
        ]))
    csv_data = "\n".join(lines)

    return Response(
        csv_data.encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="montagens.csv"'
        }
    )
