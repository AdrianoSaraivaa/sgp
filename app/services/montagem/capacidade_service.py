
# app/services/montagem/capacidade_service.py
from __future__ import annotations
from typing import Dict, List
import logging
# Import the SQLAlchemy models instead of dataclasses.  The
# ``app.models_sqla`` package defines ``Peca`` and ``EstruturaMaquina``
# with a ``query`` attribute, which is required by this service.
from app.models_sqla import Peca, EstruturaMaquina

# Logger simples
logger = logging.getLogger(__name__)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# --------- MAPEAMENTO MODELO → CÓDIGO DO CONJUNTO (chaves normalizadas) ---------
_MODELO_TO_CONJUNTO_NORM: Dict[str, str] = {
    "PM2100": "7-000",
    "PM2200": "2-000",
    "PM700":  "28-000",
    "PM25":   "PM0025",
    "PM0025": "PM0025",
}

def _norm_model_key(s: str) -> str:
    """Normaliza nome do modelo removendo espaços/hífens e deixando MAIÚSCULO."""
    s = (s or "").strip().upper()
    return "".join(ch for ch in s if ch.isalnum())

def _to_codigo_maquina(modelo_ou_codigo: str) -> str:
    """
    Aceita 'PM2100', 'PM-2100', 'pm 2100' ou o código '7-000'.
    Retorna SEMPRE o código do conjunto (ex.: '7-000') ou '' se não mapear.
    """
    s = (modelo_ou_codigo or "").strip()
    if not s:
        return ""
    if "-" in s and any(ch.isdigit() for ch in s):
        return s  # já é um código
    key = _norm_model_key(s)
    cod = _MODELO_TO_CONJUNTO_NORM.get(key, "")
    if not cod:
        logger.warning(f"[capacidade] Modelo sem mapeamento: '{modelo_ou_codigo}' (key='{key}')")
    return cod

# ---------- FUNÇÕES PÚBLICAS ----------
__all__ = [
    "calcular_capacidade_modelo",
    "calcular_todas_capacidades",
    "calcular_otimizacao",
]

def calcular_capacidade_modelo(modelo_ou_codigo: str) -> Dict:
    """
    Calcula a capacidade máxima para um modelo (ex.: 'PM2100') OU para um
    código de conjunto (ex.: '7-000'), com base no estoque e na estrutura.

    Retorna:
      {
        "capacidade": int,
        "gargalos": [
          { "codigo": str, "descricao": str, "cap_local": int,
            "estoque": int, "consumo": int },
          ...
        ]
      }
    """
    codigo_maquina = _to_codigo_maquina(modelo_ou_codigo)
    if not codigo_maquina:
        return {"capacidade": 0, "gargalos": []}

    estrutura: List[EstruturaMaquina] = (
        EstruturaMaquina.query.filter_by(codigo_maquina=codigo_maquina).all()
    )
    if not estrutura:
        logger.info(f"[capacidade] Sem estrutura para codigo_maquina='{codigo_maquina}'")
        return {"capacidade": 0, "gargalos": []}

    gargalos: List[Dict] = []
    capacidade_total = None

    for item in estrutura:
        peca: Peca | None = Peca.query.filter_by(codigo_pneumark=item.codigo_peca).first()

        if not peca:
            gargalos.append({
                "codigo": item.codigo_peca,
                "descricao": "NÃO ENCONTRADA",
                "cap_local": 0,
                "estoque": 0,
                "consumo": int(item.quantidade or 0),
            })
            capacidade_total = 0
            logger.warning(f"[capacidade] Peça não encontrada: {item.codigo_peca} (consumo={item.quantidade})")
            continue

        consumo = int(item.quantidade or 0)
        estoque = int(peca.estoque_atual or 0)
        cap_local = (estoque // consumo) if consumo > 0 else 0

        gargalos.append({
            "codigo": peca.codigo_pneumark,
            "descricao": peca.descricao,
            "cap_local": cap_local,
            "estoque": estoque,
            "consumo": consumo,
        })

        capacidade_total = cap_local if capacidade_total is None else min(capacidade_total, cap_local)

    # ordenar gargalos do mais limitante para o menos
    gargalos.sort(key=lambda g: g["cap_local"])

    return {"capacidade": capacidade_total or 0, "gargalos": gargalos}

def calcular_todas_capacidades(modelos: List[str]) -> Dict:
    """
    Calcula capacidade/gargalos para cada item da lista.
    Cada item pode ser NOME do modelo (PM2100) ou CÓDIGO (7-000).
    """
    modelos_dict = {m: calcular_capacidade_modelo(m) for m in modelos}
    return {"modelos": modelos_dict}

def calcular_otimizacao(capacidades: Dict) -> Dict:
    """
    Sugere um plano simples: dividir de forma balanceada entre os modelos.
    (Podemos evoluir depois para levar em conta gargalos compartilhados.)
    """
    ideal: Dict[str, int] = {}
    n = max(1, len(capacidades))
    for modelo, cap in capacidades.items():
        ideal[modelo] = int((cap.get("capacidade") or 0) // n)
    return {"ideal": ideal, "criterio": "balanceamento_proporcional"}
