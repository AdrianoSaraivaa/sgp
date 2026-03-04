# app/routes/home_routes/utilidades_routes.py

from flask import Blueprint, jsonify, make_response, request, current_app
from datetime import datetime
from pathlib import Path
import json, random
from typing import List, Dict  # Adicione este import no topo do arquivo

# ====================================================================
# [BLOCO] BLUEPRINT
# [NOME] utilidades_bp
# [RESPONSABILIDADE] Registrar rotas utilitárias do sistema com prefixo /utilidades
# ====================================================================
utilidades_bp = Blueprint("utilidades_bp", __name__, url_prefix="/utilidades")


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] __ping
# [RESPONSABILIDADE] Retornar status simples para teste do blueprint utilidades
# ====================================================================
# --- opcional: rota de ping para testar o blueprint rapidamente
@utilidades_bp.get("/__ping")
def __ping():
    return (
        jsonify(
            {"ok": True, "where": "utilidades_bp", "ts": datetime.utcnow().isoformat()}
        ),
        200,
    )


# ====================================================================
# [FIM BLOCO] __ping
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _caminho_frases_json
# [RESPONSABILIDADE] Resolver caminho absoluto do arquivo frases.json
# ====================================================================
def _caminho_frases_json() -> Path:
    root = Path(current_app.root_path).parent
    return (root / "app" / "data" / "frases.json").resolve()


# ====================================================================
# [FIM BLOCO] _caminho_frases_json
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _carregar_frases
# [RESPONSABILIDADE] Carregar e normalizar lista de frases a partir do arquivo JSON
# ====================================================================
def _carregar_frases() -> List[Dict]:
    caminho = _caminho_frases_json()
    # ====================================================================
    # [BLOCO] BLOCO_ARQUIVO
    # [NOME] leitura_frases_json
    # [RESPONSABILIDADE] Ler arquivo frases.json e extrair registros válidos
    # ====================================================================
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


# ====================================================================
# [FIM BLOCO] _carregar_frases
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] frase_motivacional
# [RESPONSABILIDADE] Retornar frase motivacional em modo diário ou aleatório via JSON
# ====================================================================
# 👇👇 AQUI estão os DOIS caminhos equivalentes (underscore e hífen) e sem exigir barra final
@utilidades_bp.route("/frase_motivacional", methods=["GET"], strict_slashes=False)
@utilidades_bp.route("/frase-motivacional", methods=["GET"], strict_slashes=False)
def frase_motivacional():
    frases = _carregar_frases()
    if not frases:
        resp = make_response(
            jsonify({"texto": "Nenhuma frase disponível", "autor": ""})
        )
        resp.headers["Cache-Control"] = "no-store"
        return resp

    mode = (request.args.get("mode") or "daily").lower()
    if mode == "random":
        # ====================================================================
        # [BLOCO] BLOCO_UTIL
        # [NOME] selecao_frase_random
        # [RESPONSABILIDADE] Selecionar frase aleatória da lista carregada
        # ====================================================================
        frase = random.choice(frases)
    else:
        # ====================================================================
        # [BLOCO] BLOCO_UTIL
        # [NOME] selecao_frase_diaria
        # [RESPONSABILIDADE] Selecionar frase determinística com base na data atual
        # ====================================================================
        hoje = datetime.now()
        idx = (int(hoje.strftime("%Y")) * 1000 + int(hoje.strftime("%j"))) % len(frases)
        frase = frases[idx]

    resp = make_response(jsonify(frase))
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ====================================================================
# [FIM BLOCO] frase_motivacional
# ====================================================================

# ====================================================================
# [FIM BLOCO] utilidades_bp
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLUEPRINT: utilidades_bp
# FUNÇÃO: __ping
# FUNÇÃO: _caminho_frases_json
# FUNÇÃO: _carregar_frases
# BLOCO_ARQUIVO: leitura_frases_json
# FUNÇÃO: frase_motivacional
# BLOCO_UTIL: selecao_frase_random
# BLOCO_UTIL: selecao_frase_diaria
# ====================================================================
