# app/routes/home_routes/utilidades_routes.py

from flask import Blueprint, jsonify, make_response, request, current_app
from datetime import datetime
from pathlib import Path
import json, random

utilidades_bp = Blueprint("utilidades_bp", __name__, url_prefix="/utilidades")

# --- opcional: rota de ping para testar o blueprint rapidamente
@utilidades_bp.get("/__ping")
def __ping():
    return jsonify({"ok": True, "where": "utilidades_bp", "ts": datetime.utcnow().isoformat()}), 200

def _caminho_frases_json() -> Path:
    root = Path(current_app.root_path).parent
    return (root / "app" / "data" / "frases.json").resolve()

def _carregar_frases() -> list[dict]:
    caminho = _caminho_frases_json()
    if not caminho.exists():
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        data = json.load(f)
        out = []
        for it in data:
            texto = (it.get("texto") or "").strip()
            autor = (it.get("autor") or "").strip()
            if texto:
                out.append({"texto": texto, "autor": autor})
        return out

# 👇👇 AQUI estão os DOIS caminhos equivalentes (underscore e hífen) e sem exigir barra final
@utilidades_bp.route("/frase_motivacional", methods=["GET"], strict_slashes=False)
@utilidades_bp.route("/frase-motivacional", methods=["GET"], strict_slashes=False)
def frase_motivacional():
    frases = _carregar_frases()
    if not frases:
        resp = make_response(jsonify({"texto": "Nenhuma frase disponível", "autor": ""}))
        resp.headers["Cache-Control"] = "no-store"
        return resp

    mode = (request.args.get("mode") or "daily").lower()
    if mode == "random":
        frase = random.choice(frases)
    else:
        hoje = datetime.now()
        idx = (int(hoje.strftime("%Y")) * 1000 + int(hoje.strftime("%j"))) % len(frases)
        frase = frases[idx]

    resp = make_response(jsonify(frase))
    resp.headers["Cache-Control"] = "no-store"
    return resp
