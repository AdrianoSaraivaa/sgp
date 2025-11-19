from flask import Blueprint, render_template, request, jsonify
from app import db

# ⬇️ ajuste o import para o caminho REAL do seu modelo
from app.models.producao_models.gp_models.gp_hipot import GPHipotRun

# ``inspect`` é importado sob demanda nas rotas de depuração para reduzir
# dependências globais.  Importamos aqui apenas o serviço e os modelos
from app.services.producao.hipot_service import aplicar_resultado_hipot
from app.models.producao_models.gp_execucao import GPWorkOrder, GPWorkStage
from datetime import datetime


gp_hipot_bp = Blueprint("gp_hipot_bp", __name__, url_prefix="/producao/gp/hipot")


# --- já existia ---
@gp_hipot_bp.route("/perfil", methods=["GET"])
def perfil_editor():
    return render_template("gp_templates/hipot/profile_editor.html")


# --- já existia ---
@gp_hipot_bp.route("/exec-manual", methods=["GET"])
def exec_manual():
    # Opcionalmente aceita 'serial' na query string para pré-preencher o campo
    serial_param = (request.args.get("serial") or "").strip()
    return render_template("gp_templates/hipot/exec_manual.html", serial=serial_param)


# --- NOVO: salvar execução manual ---
@gp_hipot_bp.route("/api/save", methods=["POST"])
def save_execucao():
    data = request.get_json(force=True, silent=True) or {}

    serial = (data.get("serial") or "").strip()
    modelo = (data.get("modelo") or "").strip()  # opcional neste passo
    operador = (data.get("operador") or "").strip()
    responsavel = (data.get("responsavel") or "").strip()
    obs = (data.get("obs") or "").strip()
    ordem = (data.get("ordem") or "GB>HP").strip()  # futuro

    gb_ok = data.get("gb_ok")
    gb_r_mohm = data.get("gb_r_mohm")
    gb_i_a = data.get("gb_i_a")
    gb_t_s = data.get("gb_t_s")

    hp_ok = data.get("hp_ok")
    hp_ileak_ma = data.get("hp_ileak_ma")
    hp_v_obs_v = data.get("hp_v_obs_v")
    hp_t_s = data.get("hp_t_s")

    if not serial:
        return jsonify({"ok": False, "error": "serial obrigatório"}), 400
    if gb_ok is None or hp_ok is None:
        return jsonify({"ok": False, "error": "gb_ok e hp_ok são obrigatórios"}), 400
    if (not bool(gb_ok) or not bool(hp_ok)) and not obs:
        return (
            jsonify({"ok": False, "error": "observação obrigatória na reprovação"}),
            400,
        )

    run = GPHipotRun(
        serial=serial,
        modelo=modelo or None,
        operador=operador or None,
        responsavel=responsavel or None,
        ordem=ordem or None,
        obs=obs or None,
        gb_ok=bool(gb_ok),
        gb_r_mohm=(
            float(gb_r_mohm)
            if gb_r_mohm
            not in (
                None,
                "",
            )
            else None
        ),
        gb_i_a=(
            float(gb_i_a)
            if gb_i_a
            not in (
                None,
                "",
            )
            else None
        ),
        gb_t_s=(
            float(gb_t_s)
            if gb_t_s
            not in (
                None,
                "",
            )
            else None
        ),
        hp_ok=bool(hp_ok),
        hp_ileak_ma=(
            float(hp_ileak_ma)
            if hp_ileak_ma
            not in (
                None,
                "",
            )
            else None
        ),
        hp_v_obs_v=(
            float(hp_v_obs_v)
            if hp_v_obs_v
            not in (
                None,
                "",
            )
            else None
        ),
        hp_t_s=(
            float(hp_t_s)
            if hp_t_s
            not in (
                None,
                "",
            )
            else None
        ),
    )
    # Calcula e atribui ``final_ok`` com base nos testes GB/HP
    run.finalize()
    db.session.add(run)
    db.session.commit()

    # Após salvar o registro da execução manual, aplicar o resultado na etapa B5 e na ordem
    try:
        status = "APR" if run.final_ok else "REP"
        # Atualiza etapa B5 (result e rework_flag) se existir etapa em aberto
        order = GPWorkOrder.query.filter_by(serial=serial).first()
        if order:
            stage_b5 = GPWorkStage.query.filter_by(
                order_id=order.id, bench_id="b5", finished_at=None
            ).first()
            if stage_b5:
                stage_b5.result = status
                stage_b5.rework_flag = status == "REP"
                db.session.add(stage_b5)
        # Aplica o resultado global no sistema (atualiza hiPot_status e avança o fluxo)
        aplicar_resultado_hipot({"serial": serial, "status": status})
        db.session.commit()
    except Exception:
        # Em caso de erro, reverte alterações parciais
        db.session.rollback()

    return jsonify({"ok": True, "id": run.id, "final_ok": run.final_ok})


@gp_hipot_bp.route("/api/debug/status", methods=["GET"])
def hipot_debug_status():
    # Importa ``inspect`` localmente para evitar importações desnecessárias
    from sqlalchemy import inspect  # noqa: F401

    insp = inspect(db.engine)
    return jsonify(
        {"ok": True, "has_table_gp_hipot_run": insp.has_table("gp_hipot_run")}
    )


@gp_hipot_bp.route("/api/debug/create-table", methods=["POST"])
def hipot_create_table():
    # garantir que o modelo está importado
    from app.models.producao_models.gp_models.gp_hipot import GPHipotRun  # noqa: F401

    db.create_all()  # cria qualquer tabela faltante nos models carregados
    return jsonify({"ok": True})


@gp_hipot_bp.route("/api/result", methods=["POST"])
def hipot_result_apply():
    """
    Endpoint para o coletor/ingestor enviar o resultado do HiPoT.
    Espera JSON como:
    {
      "serial": "581150",
      "status": "APR" | "OK" | "REP",
      "received_at": "2025-09-11 18:55:13"  # opcional (ISO). Se faltar, usa agora()
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    try:
        order = aplicar_resultado_hipot(data)
        return jsonify(
            {
                "ok": True,
                "serial": order.serial,
                "hipot_status": order.hipot_status,
                "hipot_flag": order.hipot_flag,
                "hipot_last_at": (
                    order.hipot_last_at.isoformat() if order.hipot_last_at else None
                ),
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ============================================================
# Rotas para execução manual integrada (B5 no painel)
# ============================================================
@gp_hipot_bp.route("/<serial>", methods=["GET"])
def hipot_manual(serial: str):
    """Exibe um formulário simples para registrar o resultado HiPot.

    Esta rota é usada pelo Painel ou por operadores ao clicarem no
    cartão de uma máquina na B5.  O template renderizado mostra um
    campo para o valor medido do ensaio elétrico e um seletor para
    indicar se o teste foi aprovado ou reprovado.

    Args:
        serial (str): número de série da máquina.

    Returns:
        str: HTML do formulário.
    """
    return render_template(
        "gp_templates/hipot/manual_form.html",
        serial=serial,
    )


@gp_hipot_bp.route("/<serial>/submit", methods=["POST"])
def hipot_manual_submit(serial: str):
    """Processa o envio manual do resultado HiPot para uma máquina.

    O formulário deve enviar os campos ``valor`` (float) e
    ``resultado`` ("aprovado" ou "reprovado").  A função cria um
    registro em ``GPHipotRun``, calcula o resultado final, atualiza a
    etapa B5 em aberto com o resultado e chama o serviço
    ``aplicar_resultado_hipot`` para atualizar a ordem de produção e
    avançar o fluxo.

    Args:
        serial (str): número de série da máquina.

    Returns:
        Response: JSON indicando se a operação foi bem-sucedida.
    """
    # Lê os dados enviados pelo formulário (campos simples de texto)
    valor_str = (request.form.get("valor") or "").strip()
    resultado = (request.form.get("resultado") or "").strip().lower()

    # Converte o valor medido para float ou None
    try:
        valor = float(valor_str) if valor_str else None
    except Exception:
        valor = None

    if resultado not in {"aprovado", "reprovado"}:
        return jsonify({"ok": False, "error": "resultado invalido"}), 400

    # Determina flags de aprovação
    final_ok = resultado == "aprovado"
    gb_ok = final_ok
    hp_ok = final_ok

    # Cria novo registro GPHipotRun com as medições mínimas necessárias
    run = GPHipotRun(
        serial=serial,
        modelo=None,
        operador=None,
        responsavel=None,
        ordem=None,
        obs=None,
        gb_ok=gb_ok,
        gb_r_mohm=valor,
        gb_i_a=None,
        gb_t_s=None,
        hp_ok=hp_ok,
        hp_ileak_ma=valor,
        hp_v_obs_v=None,
        hp_t_s=None,
    )
    run.finalize()
    db.session.add(run)
    db.session.commit()

    try:
        # Atualiza etapa B5 em aberto com resultado e flag de retrabalho
        status = "APR" if run.final_ok else "REP"
        order = GPWorkOrder.query.filter_by(serial=serial).first()
        if order:
            stage_b5 = GPWorkStage.query.filter_by(
                order_id=order.id, bench_id="b5", finished_at=None
            ).first()
            if stage_b5:
                stage_b5.result = status
                stage_b5.rework_flag = status == "REP"
                db.session.add(stage_b5)
        # Aplica o resultado global usando o serviço, que fecha a etapa e avança
        aplicar_resultado_hipot({"serial": serial, "status": status})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"ok": False, "error": "falha ao aplicar resultado"}), 500

    return jsonify({"ok": True, "final_ok": run.final_ok})


# app/routes/producao_routes/gerenciamento_producao_routes/hipot_routes.py

# ... (após as rotas existentes, mas antes do fim do arquivo) ...


# ============================================================
# NOVO: API para submissão via modal do Painel Kanban
# ============================================================
@gp_hipot_bp.route("/api/painel-submit-result", methods=["POST"])
def hipot_painel_submit():
    """
    Recebe os dados do modal do Painel Kanban (coluna HI POT).
    Coleta os dois parâmetros (Tensão Suportável e Cont. Aterramento)
    e o resultado final, registrando o GPHipotRun e avançando o fluxo.
    """
    # Recebe o JSON do frontend
    data = request.get_json(force=True, silent=True) or {}

    serial = (data.get("serial") or "").strip()
    # Novos campos específicos do teste
    hp_tensao_str = (data.get("tensao_suportavel") or "").strip()
    gb_resistencia_str = (data.get("continuidade_aterramento") or "").strip()
    resultado = (
        (data.get("resultado") or "").strip().lower()
    )  # 'aprovado' ou 'reprovado'
    operador_id = (data.get("operador_id") or "").strip()  # ID do operador logado

    if not serial:
        return jsonify({"ok": False, "error": "Número de Série é obrigatório"}), 400
    if resultado not in {"aprovado", "reprovado"}:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Resultado inválido. Deve ser 'aprovado' ou 'reprovado'",
                }
            ),
            400,
        )

    # Conversão e validação dos valores para float
    try:
        hp_tensao = float(hp_tensao_str) if hp_tensao_str else None
        gb_resistencia = float(gb_resistencia_str) if gb_resistencia_str else None
    except ValueError:
        return (
            jsonify(
                {"ok": False, "error": "Valores de medição inválidos (não são números)"}
            ),
            400,
        )

    # Ambos os valores são obrigatórios para um teste completo
    if hp_tensao is None or gb_resistencia is None:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Ambos os valores de medição (Tensão Suportável e Cont. Aterramento) são obrigatórios",
                }
            ),
            400,
        )

    # Define status e flags para a execução
    final_ok = resultado == "aprovado"
    gb_ok = final_ok  # Assumimos que o resultado final implica no sub-teste
    hp_ok = final_ok
    status = "APR" if final_ok else "REP"

    # Cria o registro GPHipotRun (Log de rastreabilidade)
    run = GPHipotRun(
        serial=serial,
        operador=operador_id or None,
        # Mapeamento: Continuidade de Aterramento -> Ground Bond Resistance (gb_r_mohm)
        gb_ok=gb_ok,
        gb_r_mohm=gb_resistencia,
        # Mapeamento: Tensão Suportável -> Hi-Pot Voltage Observed (hp_v_obs_v)
        hp_ok=hp_ok,
        hp_v_obs_v=hp_tensao,
        # Outros campos do modelo não utilizados nesta interface
        modelo=None,
        responsavel=None,
        ordem=None,
        obs=None,
        gb_i_a=None,
        gb_t_s=None,
        hp_ileak_ma=None,
        hp_t_s=None,
    )
    run.finalize()  # Garante que run.final_ok esteja correto
    db.session.add(run)

    try:
        # 1. Atualiza a etapa B5 (Hi-Pot) em aberto, se existir
        order = GPWorkOrder.query.filter_by(serial=serial).first()
        if order:
            stage_b5 = GPWorkStage.query.filter_by(
                order_id=order.id, bench_id="b5", finished_at=None
            ).first()
            if stage_b5:
                stage_b5.result = status
                stage_b5.rework_flag = status == "REP"
                stage_b5.finished_at = datetime.utcnow()  # Fecha a etapa
                db.session.add(stage_b5)

        # 2. Aplica o resultado global, que deve avançar o fluxo.
        # O serviço 'aplicar_resultado_hipot' já contém o db.session.commit()
        aplicar_resultado_hipot({"serial": serial, "status": status})

    except Exception as e:
        db.session.rollback()
        # Reverte se o avanço do fluxo falhar
        return (
            jsonify(
                {"ok": False, "error": f"Falha ao aplicar resultado no fluxo: {str(e)}"}
            ),
            500,
        )

    return jsonify({"ok": True, "final_ok": run.final_ok, "status": status})
