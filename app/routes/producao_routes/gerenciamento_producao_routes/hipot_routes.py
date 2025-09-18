from flask import Blueprint, render_template, request, jsonify
from app import db
# ⬇️ ajuste o import para o caminho REAL do seu modelo
from app.models.producao_models.gp_models.gp_hipot import GPHipotRun
from sqlalchemy import inspect
from app.services.producao.hipot_service import aplicar_resultado_hipot



gp_hipot_bp = Blueprint(
    "gp_hipot_bp", __name__, url_prefix="/producao/gp/hipot"
)

# --- já existia ---
@gp_hipot_bp.route("/perfil", methods=["GET"])
def perfil_editor():
    return render_template("gp_templates/hipot/profile_editor.html")

# --- já existia ---
@gp_hipot_bp.route("/exec-manual", methods=["GET"])
def exec_manual():
    return render_template("gp_templates/hipot/exec_manual.html")

# --- NOVO: salvar execução manual ---
@gp_hipot_bp.route("/api/save", methods=["POST"])
def save_execucao():
    data = request.get_json(force=True, silent=True) or {}

    serial       = (data.get("serial") or "").strip()
    modelo       = (data.get("modelo") or "").strip()           # opcional neste passo
    operador     = (data.get("operador") or "").strip()
    responsavel  = (data.get("responsavel") or "").strip()
    obs          = (data.get("obs") or "").strip()
    ordem        = (data.get("ordem") or "GB>HP").strip()       # futuro

    gb_ok        = data.get("gb_ok")
    gb_r_mohm    = data.get("gb_r_mohm")
    gb_i_a       = data.get("gb_i_a")
    gb_t_s       = data.get("gb_t_s")

    hp_ok        = data.get("hp_ok")
    hp_ileak_ma  = data.get("hp_ileak_ma")
    hp_v_obs_v   = data.get("hp_v_obs_v")
    hp_t_s       = data.get("hp_t_s")

    if not serial:
        return jsonify({"ok": False, "error": "serial obrigatório"}), 400
    if gb_ok is None or hp_ok is None:
        return jsonify({"ok": False, "error": "gb_ok e hp_ok são obrigatórios"}), 400
    if (not bool(gb_ok) or not bool(hp_ok)) and not obs:
        return jsonify({"ok": False, "error": "observação obrigatória na reprovação"}), 400

    run = GPHipotRun(
        serial=serial,
        modelo=modelo or None,
        operador=operador or None,
        responsavel=responsavel or None,
        ordem=ordem or None,
        obs=obs or None,

        gb_ok=bool(gb_ok),
        gb_r_mohm=float(gb_r_mohm) if gb_r_mohm not in (None, "",) else None,
        gb_i_a=float(gb_i_a) if gb_i_a not in (None, "",) else None,
        gb_t_s=float(gb_t_s) if gb_t_s not in (None, "",) else None,

        hp_ok=bool(hp_ok),
        hp_ileak_ma=float(hp_ileak_ma) if hp_ileak_ma not in (None, "",) else None,
        hp_v_obs_v=float(hp_v_obs_v) if hp_v_obs_v not in (None, "",) else None,
        hp_t_s=float(hp_t_s) if hp_t_s not in (None, "",) else None,
    )
    run.finalize()
    db.session.add(run)
    db.session.commit()

    from sqlalchemy import inspect



    return jsonify({"ok": True, "id": run.id, "final_ok": run.final_ok})


@gp_hipot_bp.route("/api/debug/status", methods=["GET"])
def hipot_debug_status():
    insp = inspect(db.engine)
    return jsonify({
        "ok": True,
        "has_table_gp_hipot_run": insp.has_table("gp_hipot_run")
    })



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
        return jsonify({
            "ok": True,
            "serial": order.serial,
            "hipot_status": order.hipot_status,
            "hipot_flag": order.hipot_flag,
            "hipot_last_at": (order.hipot_last_at.isoformat() if order.hipot_last_at else None),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

