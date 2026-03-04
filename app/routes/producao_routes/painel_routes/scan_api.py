# app/routes/producao_routes/painel_routes/scan_api.py
from flask import Blueprint, request, jsonify, current_app as logapp
from app import db
from sqlalchemy import inspect
from datetime import datetime
import re

# models de execução (ordens/etapas)
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage

# “receita” por modelo
from app.models.producao_models.gp_modelos import GPModel, GPBenchConfig

# Consumo/estoque: entrada e estorno do produto acabado
from app.routes.producao_routes.maquinas_routes.consumo_service import (
    registrar_conclusao_produto_acabado,
    estornar_conclusao_produto_acabado,
)

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] gp_painel_scan_api_bp
# [RESPONSABILIDADE] Definir blueprint e prefixo das rotas de scan do painel de produção
# ====================================================================
gp_painel_scan_api_bp = Blueprint(
    "gp_painel_scan_api_bp", __name__, url_prefix="/producao/gp/painel/api"
)
# ====================================================================
# [FIM BLOCO] gp_painel_scan_api_bp
# ====================================================================

# -------------------------------------------------------------------
# Helpers de resposta/log (padronizam erros e sucessos) + verbose
# -------------------------------------------------------------------


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _ok
# [RESPONSABILIDADE] Padronizar resposta de sucesso (JSON) e registrar log leve
# ====================================================================
def _ok(**data):
    data.setdefault("ok", True)
    # log leve
    try:
        logapp.logger.info(
            "[SCAN][OK] %s", {k: v for k, v in data.items() if k not in {"session"}}
        )
    except Exception:
        pass
    return jsonify(data), 200


# ====================================================================
# [FIM BLOCO] _ok
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _err
# [RESPONSABILIDADE] Padronizar resposta de erro (JSON) com logging estruturado e contexto opcional
# ====================================================================
def _err(http_code, code, msg, hint=None, **ctx):
    # log estruturado
    try:
        logapp.logger.warning(
            "[SCAN][%s] %s | hint=%s | ctx=%s",
            code,
            msg,
            hint or "-",
            {k: v for k, v in ctx.items() if k not in {"session"}},
        )
    except Exception:
        pass
    payload = {"ok": False, "error": code, "message": msg}
    if hint:
        payload["hint"] = hint
    if ctx:
        payload["context"] = ctx
    return jsonify(payload), http_code


# ====================================================================
# [FIM BLOCO] _err
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _is_verbose
# [RESPONSABILIDADE] Indicar se a resposta deve incluir diagnósticos detalhados via querystring
# ====================================================================
def _is_verbose():
    return request.args.get("verbose") == "1"


# ====================================================================
# [FIM BLOCO] _is_verbose
# ====================================================================

# -------------------------------------------------------------------
# Utilitários
# -------------------------------------------------------------------


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _ensure_tables
# [RESPONSABILIDADE] Garantir existência das tabelas necessárias para execução do painel (criar se faltar)
# ====================================================================
def _ensure_tables():
    insp = inspect(db.engine)
    for t in ("gp_work_order", "gp_work_stage", "gp_model", "gp_bench_config"):
        if not insp.has_table(t):
            db.create_all()
            break


# ====================================================================
# [FIM BLOCO] _ensure_tables
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _sequence_for_model
# [RESPONSABILIDADE] Construir sequência de bancadas ativas por modelo com regras obrigatórias do projeto
# ====================================================================
def _sequence_for_model(modelo):
    """
    Retorna a sequência de bancadas ativas:
      ['sep', ...bancadas ativas em ordem..., 'final']
    b5 (HiPot) e b8 (Checklist) são sempre obrigatórias.
    """
    seq = ["sep"]
    active = {"b%d" % i: False for i in range(1, 9)}
    m = GPModel.query.filter_by(nome=modelo).first()
    if m:
        for r in GPBenchConfig.query.filter_by(model_id=m.id).all():
            active[r.bench_id] = bool(r.ativo) or bool(r.obrigatorio)

    # obrigatórias do projeto
    active["b5"] = True
    active["b8"] = True

    for i in range(1, 9):
        if active.get("b%d" % i, False):
            seq.append("b%d" % i)
    seq.append("final")
    return seq


# ====================================================================
# [FIM BLOCO] _sequence_for_model
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _first_active_bench
# [RESPONSABILIDADE] Obter primeira bancada ativa após 'sep' para um modelo
# ====================================================================
def _first_active_bench(modelo):
    """Primeira bancada ativa após 'sep'."""
    seq = _sequence_for_model(modelo)
    return seq[1] if len(seq) > 2 else "sep"


# ====================================================================
# [FIM BLOCO] _first_active_bench
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _next_in_sequence
# [RESPONSABILIDADE] Obter próxima bancada na sequência para uma bancada atual
# ====================================================================
def _next_in_sequence(seq, current):
    try:
        i = seq.index(current)
        return seq[i + 1] if i + 1 < len(seq) else seq[-1]
    except ValueError:
        return "sep"


# ====================================================================
# [FIM BLOCO] _next_in_sequence
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _prev_in_sequence
# [RESPONSABILIDADE] Obter bancada anterior na sequência para uma bancada atual
# ====================================================================
def _prev_in_sequence(seq, current):
    try:
        i = seq.index(current)
        return seq[i - 1] if i - 1 >= 0 else seq[0]
    except ValueError:
        return "sep"


# ====================================================================
# [FIM BLOCO] _prev_in_sequence
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _nome_operador_amigavel
# [RESPONSABILIDADE] Normalizar nome de operador para exibição amigável em mensagens finais
# ====================================================================
def _nome_operador_amigavel(raw_op):
    raw = (raw_op or "").strip()
    norm = raw.lower()
    if "saed" in norm:
        return "Saedy"
    if "wev" in norm or "wever" in norm:
        return "Weverton"
    if norm in {"weverton", "saedy"}:
        return raw.title()
    if not raw or len(raw) < 2:
        return "Weverton"
    return raw


# ====================================================================
# [FIM BLOCO] _nome_operador_amigavel
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _sanitize_scan
# [RESPONSABILIDADE] Normalizar string lida no scanner (separadores, sufixos e deduplicação)
# ====================================================================
def _sanitize_scan(raw):
    """
    - Remove espaços/CR/LF
    - Normaliza separador (: ; /) -> '-'
    - Remove sufixos ocasionais (+S, +F, $)
    - Deduplica leitura repetida: 'B3-591160B3-591160' -> 'B3-591160'
    """
    if not raw:
        return ""
    s = raw.strip().replace("\r", "").replace("\n", "")
    s = re.sub(r"[:;/]", "-", s)
    s = re.sub(r"(\+S|\+F|\$)+$", "", s, flags=re.IGNORECASE)
    # deduplicação: <token><token>
    m = re.match(r"^([A-Za-z0-9]+-[A-Za-z0-9\-]+)\1$", s)
    if m:
        s = m.group(1)
    return s


# ====================================================================
# [FIM BLOCO] _sanitize_scan
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _parse_raw_scan
# [RESPONSABILIDADE] Parsear leitura bruta do scanner em bench_id e serial no formato esperado
# ====================================================================
def _parse_raw_scan(raw):
    """
    Ex.: 'B1-581150' -> bench_id='b1', serial='581150'
    aceita também 'SEP-581150'
    """
    if not raw:
        return None, None, None
    s = _sanitize_scan(raw)
    parts = s.split("-", 1)
    if len(parts) != 2:
        return None, None, None
    prefix, serial = parts[0].strip().upper(), parts[1].strip().upper()
    if prefix == "SEP":
        return "sep", serial, None
    if prefix.startswith("B") and prefix[1:].isdigit():
        return "b%d" % int(prefix[1:]), serial, None
    return None, None, None


# ====================================================================
# [FIM BLOCO] _parse_raw_scan
# ====================================================================

# -------------------------------------------------------------------
# Rotas
# -------------------------------------------------------------------


@gp_painel_scan_api_bp.post("/scan")
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] scan
# [RESPONSABILIDADE] Processar leitura de scanner/manual e realizar start/finish de etapas com validações
# ====================================================================
def scan():
    """
    Entrada:
      - Automática: { "raw_scan": "B1-581150", "operador": "João" }
      - Manual (legado): { "serial": "...", "bench_id":"b1", "action":"start|finish", "operador": "..." }

    Regras:
      - START só é permitido para a bancada atual (order.current_bench),
        exceto quando current_bench == 'sep', onde START esperado é a primeira bancada ativa.
      - FINISH só na bancada atual, movendo para a próxima.
      - Se vier raw_scan, o backend decide automaticamente start/finish:
          * existe stage aberto NESTA bancada? -> FINISH
          * senão -> START (respeitando regra da bancada atual)
    """
    _ensure_tables()

    data = request.get_json(force=True) or {}
    raw_scan = (data.get("raw_scan") or "").strip()
    operador = (data.get("operador") or "").strip() or "sistema"

    diagnostics = []  # devolvido só se ?verbose=1

    if raw_scan:
        bench_id, serial, action = _parse_raw_scan(raw_scan)
        diagnostics.append(
            {
                "input": "raw_scan",
                "bench_id": bench_id,
                "serial": serial,
                "action": action,
            }
        )
    else:
        serial = (data.get("serial") or "").strip().upper()
        bench_id = (data.get("bench_id") or "").strip().lower()
        action = (data.get("action") or "").strip().lower() or None
        diagnostics.append(
            {
                "input": "structured",
                "bench_id": bench_id,
                "serial": serial,
                "action": action,
            }
        )

    # validação básica
    if not serial or bench_id not in {
        "sep",
        "b1",
        "b2",
        "b3",
        "b4",
        "b5",
        "b6",
        "b7",
        "b8",
    }:
        return _err(
            400,
            "payload_invalido",
            "Leitura inválida.",
            hint="Verifique o formato do código (ex.: B3-581150).",
            bench_id=bench_id,
            serial=serial,
        )

    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return _err(
            404,
            "serial_nao_encontrado",
            "Serial não encontrado.",
            hint="Imprima a etiqueta ou verifique o número.",
            serial=serial,
        )

    seq = _sequence_for_model(order.modelo)
    now = datetime.utcnow()

    # decisão automática para raw_scan sem ação explícita
    if raw_scan and action is None:
        open_this = GPWorkStage.query.filter_by(
            order_id=order.id, bench_id=bench_id, finished_at=None
        ).first()
        action = "finish" if open_this else "start"
        diagnostics.append({"auto_action": action})

    # ---------------- START ----------------
    if action == "start":
        # há etapa aberta em outra bancada?
        open_any = GPWorkStage.query.filter_by(
            order_id=order.id, finished_at=None
        ).first()
        if open_any and open_any.bench_id != bench_id:
            return _err(
                400,
                "etapa_em_aberto",
                "Há uma etapa em aberto.",
                hint="Finalize a etapa atual antes de iniciar outra.",
                aberta_em=open_any.bench_id,
                bench_id=bench_id,
                serial=serial,
            )

        expected_start = order.current_bench
        if order.current_bench == "sep":
            expected_start = _first_active_bench(order.modelo)

        if bench_id != expected_start:
            return _err(
                400,
                "transicao_invalida",
                "Transição inválida.",
                hint="Siga a sequência de bancadas.",
                esperado=expected_start,
                atual=order.current_bench,
                escolhido=bench_id,
                serial=serial,
            )

        stage = GPWorkStage.query.filter_by(
            order_id=order.id, bench_id=bench_id, finished_at=None
        ).first()
        if not stage:
            stage = GPWorkStage(
                order_id=order.id, bench_id=bench_id, started_at=now, operador=operador
            )
            db.session.add(stage)

        order.current_bench = bench_id
        order.status = "in_progress"
        order.updated_at = now
        db.session.commit()

        resp = {
            "serial": order.serial,
            "modelo": order.modelo,
            "operador": operador,
            "bench_started": bench_id,
            "moved_to": bench_id,
            "status": order.status,
            "final_message": None,
        }
        if _is_verbose():
            resp["diagnostics"] = diagnostics
        return _ok(**resp)

    # ---------------- FINISH ----------------
    # só finaliza a bancada atual
    if bench_id != order.current_bench:
        return _err(
            400,
            "transicao_invalida",
            "Transição inválida.",
            hint="Finalize na bancada atual.",
            esperado=order.current_bench,
            escolhido=bench_id,
            serial=serial,
        )

    stage = GPWorkStage.query.filter_by(
        order_id=order.id, bench_id=bench_id, finished_at=None
    ).first()
    if not stage:
        # cria e fecha (resiliência/rastreabilidade)
        stage = GPWorkStage(
            order_id=order.id, bench_id=bench_id, started_at=now, operador=operador
        )
        db.session.add(stage)
    stage.finished_at = now

    bench_done = bench_id
    nxt = _next_in_sequence(seq, bench_id)

    order.current_bench = nxt
    order.status = "done" if nxt == "final" else "in_progress"
    order.updated_at = now

    final_message = None
    if nxt == "final":
        try:
            registrar_conclusao_produto_acabado(
                modelo=order.modelo,
                quantidade=1,
                usuario=operador,
                referencia=order.serial,
                session=db.session,
            )
        except Exception as e:
            db.session.rollback()
            return _err(
                500,
                "entrada_produto_acabado_falhou",
                "Falha ao lançar produto acabado no estoque.",
                hint="Avise o supervisor.",
                detalhe=str(e),
                serial=serial,
            )

        nome_operador = _nome_operador_amigavel(operador)
        final_message = {
            "titulo": "🎉 Tudo certo por aqui!",
            "mensagem": (
                "O %s (S/N %s) está pronto. "
                "Rastreabilidade gravada e estoque atualizado. Bom trabalho, %s!"
            )
            % (order.modelo, order.serial, nome_operador),
            "serial": order.serial,
            "modelo": order.modelo,
            "operador": nome_operador,
            "hora": now.strftime("%H:%M"),
        }

    db.session.commit()

    resp = {
        "serial": order.serial,
        "modelo": order.modelo,
        "operador": operador,
        "bench_done": bench_done,
        "moved_to": order.current_bench,
        "status": order.status,
        "final_message": final_message,
    }
    if _is_verbose():
        resp["diagnostics"] = diagnostics
    return _ok(**resp)


# ====================================================================
# [FIM BLOCO] scan
# ====================================================================

# -------------------------------------------------------------------


@gp_painel_scan_api_bp.post("/scan/undo")
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] scan_undo
# [RESPONSABILIDADE] Desfazer a última movimentação de etapa, com estorno de produto acabado quando aplicável
# ====================================================================
def scan_undo():
    """
    Desfaz a última movimentação.
    Se estava finalizado antes, estorna o produto acabado.
    """
    _ensure_tables()
    data = request.get_json(force=True) or {}
    serial = (data.get("serial") or "").strip().upper()
    operador = (data.get("operador") or "sistema").strip()

    if not serial:
        return _err(400, "serial_requerido", "Informe o serial para desfazer.")

    order = GPWorkOrder.query.filter_by(serial=serial).first()
    if not order:
        return _err(
            404, "serial_nao_encontrado", "Serial não encontrado.", serial=serial
        )

    estava_final = (order.current_bench == "final") or (order.status == "done")
    seq = _sequence_for_model(order.modelo)
    now = datetime.utcnow()

    # 1) Se tem etapa ABERTA -> remover e voltar para a anterior
    open_stage = (
        GPWorkStage.query.filter_by(order_id=order.id, finished_at=None)
        .order_by(GPWorkStage.started_at.desc())
        .first()
    )
    if open_stage:
        prevb = _prev_in_sequence(seq, open_stage.bench_id)
        db.session.delete(open_stage)
        order.current_bench = prevb
        order.status = "queued" if prevb == "sep" else "in_progress"
        order.updated_at = now

        if estava_final:
            try:
                estornar_conclusao_produto_acabado(
                    modelo=order.modelo,
                    quantidade=1,
                    usuario=operador,
                    referencia=order.serial,
                    session=db.session,
                )
            except Exception as e:
                db.session.rollback()
                return _err(
                    500,
                    "estorno_produto_acabado_falhou",
                    "Falha ao estornar produto acabado.",
                    hint="Avise o supervisor.",
                    detalhe=str(e),
                    serial=serial,
                )

        db.session.commit()
        return _ok(moved_to=order.current_bench, status=order.status)

    # 2) Senão, reabre a última etapa FECHADA
    last_closed = (
        GPWorkStage.query.filter(
            GPWorkStage.order_id == order.id, GPWorkStage.finished_at.isnot(None)
        )
        .order_by(GPWorkStage.finished_at.desc())
        .first()
    )
    if last_closed:
        last_closed.finished_at = None
        order.current_bench = last_closed.bench_id
        order.status = "in_progress"
        order.updated_at = now

        if estava_final:
            try:
                estornar_conclusao_produto_acabado(
                    modelo=order.modelo,
                    quantidade=1,
                    usuario=operador,
                    referencia=order.serial,
                    session=db.session,
                )
            except Exception as e:
                db.session.rollback()
                return _err(
                    500,
                    "estorno_produto_acabado_falhou",
                    "Falha ao estornar produto acabado.",
                    hint="Avise o supervisor.",
                    detalhe=str(e),
                    serial=serial,
                )

        db.session.commit()
        return _ok(moved_to=order.current_bench, status=order.status)

    # 3) Nada para desfazer (volta para 'sep')
    order.current_bench = "sep"
    order.status = "queued"
    order.updated_at = now

    if estava_final:
        try:
            estornar_conclusao_produto_acabado(
                modelo=order.modelo,
                quantidade=1,
                usuario=operador,
                referencia=order.serial,
                session=db.session,
            )
        except Exception as e:
            db.session.rollback()
            return _err(
                500,
                "estorno_produto_acabado_falhou",
                "Falha ao estornar produto acabado.",
                hint="Avise o supervisor.",
                detalhe=str(e),
                serial=serial,
            )

    db.session.commit()
    return _ok(moved_to=order.current_bench, status=order.status)


# ====================================================================
# [FIM BLOCO] scan_undo
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: gp_painel_scan_api_bp
# FUNÇÃO: _ok
# FUNÇÃO: _err
# FUNÇÃO: _is_verbose
# FUNÇÃO: _ensure_tables
# FUNÇÃO: _sequence_for_model
# FUNÇÃO: _first_active_bench
# FUNÇÃO: _next_in_sequence
# FUNÇÃO: _prev_in_sequence
# FUNÇÃO: _nome_operador_amigavel
# FUNÇÃO: _sanitize_scan
# FUNÇÃO: _parse_raw_scan
# FUNÇÃO: scan
# FUNÇÃO: scan_undo
# ====================================================================
