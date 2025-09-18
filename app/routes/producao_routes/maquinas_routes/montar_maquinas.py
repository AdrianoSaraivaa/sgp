
# app/routes/producao_routes/maquinas_routes/montar_maquinas.py
from __future__ import annotations
from datetime import datetime
import logging

from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import inspect

from app import db
from app.services.serials import generate_serials
from app.services.montagem import capacidade_service
# Use the SQLAlchemy models instead of the dataclasses. Import from the
# auto-generated models_sqla package to ensure that ``.query`` is available.
from app.models_sqla import Montagem, GPWorkOrder, EstruturaMaquina  # pré-checagem da BOM

# --- imports do service (duplo: módulo e funções) ---
import app.services.montagem.capacidade_service as cap_srv
from app.services.montagem.capacidade_service import (
    calcular_capacidade_modelo,
    calcular_todas_capacidades,
    calcular_otimizacao,
)

from app.routes.producao_routes.maquinas_routes.consumo_service import (
    reservar_componentes_para_montagem,
    EstoqInsuficiente,
)

# ============================================================
# Logger
# ============================================================
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ============================================================
# Blueprint
# ============================================================
maquinas_bp = Blueprint(
    "maquinas_bp",
    __name__,
    url_prefix="/producao/montagem"
)

# Modelos conhecidos
MODELOS = ["PM2100", "PM2200", "PM700", "PM25"]

# ------------------------------------------------------------
# Mapa: modelo (UI) -> código do conjunto/BOM (EstruturaMaquina.codigo_maquina)
# ------------------------------------------------------------
MODEL_TO_CONJUNTO = {
    "PM2100": "7-000",
    "PM2200": "2-000",
    "PM700":  "28-000",
    "PM25":   "PM0025",
}

def _resolver_codigo_conjunto(modelo: str) -> str | None:
    codigo = MODEL_TO_CONJUNTO.get(modelo)
    if not codigo:
        logger.error(f"[resolver] Sem mapeamento para modelo='{modelo}'. Atualize MODEL_TO_CONJUNTO.")
    else:
        logger.info(f"[resolver] Modelo '{modelo}' -> Conjunto '{codigo}'")
    return codigo

def _assert_bom_existe(codigo_conjunto: str) -> bool:
    qtd = (
        db.session.query(EstruturaMaquina)
        .filter(EstruturaMaquina.codigo_maquina == codigo_conjunto)
        .limit(1)
        .count()
    )
    logger.info(f"[pré-checagem] BOM para '{codigo_conjunto}': {'ENCONTRADA' if qtd > 0 else 'NÃO ENCONTRADA'}")
    return qtd > 0

# ============================================================
# Views / APIs
# ============================================================
@maquinas_bp.route("/", methods=["GET"])
def pagina_montagem():
    logger.info("Renderizando página de montagem")
    return render_template("producao_templates/montagem_templates/montar_maquina.html")

@maquinas_bp.route("/api/capacidade", methods=["GET"])
def api_capacidade():
    try:
        logger.info(">>> /api/capacidade chamado")
        logger.info(f"[cap] módulo: {cap_srv.__file__}")
        logger.info(f"[cap] funções disponíveis: {[n for n in dir(cap_srv) if n.startswith('calcular_')]}")
        capacidades = calcular_todas_capacidades(MODELOS)
        logger.info(f"[cap] resumo: {{ {', '.join(f'{k}: {v.get('capacidade')}' for k, v in capacidades['modelos'].items())} }}")
        return jsonify(capacidades)
    except Exception as e:
        logger.exception("Erro ao calcular capacidade")
        return jsonify({"ok": False, "erro": str(e)}), 500

@maquinas_bp.route("/api/otimizacao", methods=["GET"])
def api_otimizacao():
    try:
        logger.info(">>> /api/otimizacao chamado")
        logger.info(f"[otz] módulo: {cap_srv.__file__}")
        capacidades = calcular_todas_capacidades(MODELOS)["modelos"]
        plano = calcular_otimizacao(capacidades)
        logger.info(f"[otz] ideal: {plano.get('ideal')}")
        return jsonify(plano)
    except Exception as e:
        logger.exception("Erro ao calcular plano otimizado")
        return jsonify({"ok": False, "erro": str(e)}), 500

@maquinas_bp.route("/api/validar", methods=["POST"])
def api_validar():
    payload = request.get_json(silent=True) or {}
    erros = []

    logger.info(f"Validando payload: {payload}")

    for modelo, qtd in payload.items():
        try:
            qtd = int(qtd)
        except (ValueError, TypeError):
            erros.append({"modelo": modelo, "motivo": "Quantidade inválida"})
            continue
        if qtd < 0:
            erros.append({"modelo": modelo, "motivo": "Quantidade negativa"})
            continue
        if modelo not in MODELOS:
            erros.append({"modelo": modelo, "motivo": "Modelo desconhecido"})
            continue

        codigo_conjunto = _resolver_codigo_conjunto(modelo)
        if not codigo_conjunto:
            erros.append({"modelo": modelo, "motivo": "Modelo sem mapeamento para conjunto/BOM"})
            continue
        if not _assert_bom_existe(codigo_conjunto):
            erros.append({"modelo": modelo, "motivo": f"BOM não encontrada para '{codigo_conjunto}'"})

    ok = len(erros) == 0
    return jsonify({"ok": ok, "erros": erros})

@maquinas_bp.route("/api/montadas", methods=["GET"])
def api_montadas():
    itens = Montagem.query.order_by(Montagem.id.desc()).limit(300).all()
    logger.debug(f"Consultando {len(itens)} montagens")
    def _fmt_datetime(dt):
        try:
            # Formata data/hora no padrão brasileiro (dd/mm/YYYY HH:MM)
            return dt.strftime("%d/%m/%Y %H:%M") if dt else ""
        except Exception:
            return str(dt)
    return jsonify([
        {
            **m.as_dict(),
            # Frontend expects "serie" instead of "serial"; provide both
            "serie": m.serial,
            "data_hora": _fmt_datetime(m.data_hora),
        }
        for m in itens
    ])

@maquinas_bp.route("/api/montar", methods=["POST"])
def api_montar():
    """
    Espera JSON: { "modelo": "PM2100", "quantidade": 2, "usuario": "Operador" }
    """
    data = request.get_json() or {}
    modelo = (data.get("modelo") or "").strip()
    quantidade = int(data.get("quantidade") or 0)
    usuario = (data.get("usuario") or "Operador").strip()

    logger.info(f"Recebida montagem: modelo={modelo}, qtd={quantidade}, usuario={usuario}")

    if not modelo or quantidade <= 0:
        return jsonify({"ok": False, "erros": [{"modelo": modelo or "-", "motivo": "Informe modelo e quantidade > 0"}]}), 400
    if modelo not in MODELOS:
        return jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": "Modelo desconhecido"}]}), 400

    # Resolver modelo -> código do conjunto (BOM) + pré-checar BOM
    codigo_conjunto = _resolver_codigo_conjunto(modelo)
    if not codigo_conjunto:
        return jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": "Sem mapeamento para conjunto/BOM"}]}), 400
    if not _assert_bom_existe(codigo_conjunto):
        return jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": f"BOM não encontrada para '{codigo_conjunto}'"}]}), 400

    # 1) Seriais
    try:
        seriais = generate_serials(modelo, quantidade, usuario)
        logger.debug(f"Seriais gerados: {seriais}")
    except Exception as e:
        logger.exception("Erro ao gerar seriais")
        return jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": str(e)}]}), 500

    # 2) Registros de montagem (sem commit ainda)
    criadas = []
    for s in seriais:
        # Preenche campos obrigatórios de Montagem (status, label_printed, label_print_count, created_at, updated_at)
        m = Montagem(
            modelo=modelo,
            serial=s,
            usuario=usuario,
            data_hora=datetime.utcnow(),
            status="OK",
            label_printed=False,
            label_print_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(m)
        criadas.append(m)

    # 3) Reserva/baixa de componentes (antes do commit)
    try:
        referencia = (
            f"LOTE-{modelo}-{codigo_conjunto}-{seriais[0]}..{seriais[-1]}"
            if len(seriais) > 1 else f"{codigo_conjunto}-{seriais[0]}"
        )

        # Passa o CÓDIGO DO CONJUNTO (chave de BOM) para o consumo_service
        reservar_componentes_para_montagem(
            modelo=codigo_conjunto,
            quantidade_unidades=quantidade,
            usuario=usuario,
            referencia=referencia,
            session=db.session,
        )

        # 4) Commit atômico
        db.session.commit()
        logger.info(f"{len(criadas)} montagens registradas e componentes reservados com sucesso")

    except EstoqInsuficiente as e:
        db.session.rollback()
        faltas = [{"codigo_peca": f.codigo_peca, "necessario": f.necessario, "disponivel": f.disponivel} for f in e.faltas]
        logger.warning(f"Reserva negada por estoque insuficiente: {faltas}")
        return jsonify({"ok": False, "motivo": "ESTOQUE_INSUFICIENTE", "faltas": faltas}), 409

    except Exception as e:
        db.session.rollback()
        logger.exception("Erro ao salvar montagens/reserva")
        return jsonify({"ok": False, "erros": [{"modelo": modelo, "motivo": str(e)}]}), 400

    # 5) Enfileirar no Painel (operação separada)
    warn = None
    try:
        insp = inspect(db.engine)
        if not insp.has_table("gp_work_order"):
            logger.warning("Tabela gp_work_order não encontrada, criando...")
            db.create_all()

        for m in criadas:
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
        logger.info("Montagens enfileiradas no Painel com sucesso")

    except Exception as e:
        db.session.rollback()
        warn = f"Falha ao enfileirar no Painel (SEP): {e}"
        logger.exception("Erro ao enfileirar no Painel")

    # 6) Resposta
    resp = {"ok": True, "itens": [m.as_dict() for m in criadas]}
    if warn:
        resp["warning"] = warn
    return jsonify(resp)
