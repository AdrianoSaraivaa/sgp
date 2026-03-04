# app/services/serials.py
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] MODEL_CODE
# [RESPONSABILIDADE] Definir códigos por modelo usados na composição do número de série
# ====================================================================
# --- Config ---------------------------------------------------------------

# Código por modelo (terceiro dígito do número de série)
MODEL_CODE: Dict[str, str] = {
    "PM2100": "1",
    "PM2200": "2",
    "PM700": "7",
}
# ====================================================================
# [FIM BLOCO] MODEL_CODE
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] LOG_DIR
# [RESPONSABILIDADE] Definir e garantir diretório para logs do gerador de seriais
# ====================================================================
# Pasta dos logs + arquivo do contador global
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
# ====================================================================
# [FIM BLOCO] LOG_DIR
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] COUNTER_FILE
# [RESPONSABILIDADE] Definir arquivo persistente do contador global de números de série
# ====================================================================
COUNTER_FILE = LOG_DIR / "serial_counter.txt"  # contador GLOBAL e persistente
# ====================================================================
# [FIM BLOCO] COUNTER_FILE
# ====================================================================

# --- Helpers --------------------------------------------------------------


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _year_last_digit
# [RESPONSABILIDADE] Obter último dígito do ano para composição do serial
# ====================================================================
def _year_last_digit(dt: datetime) -> str:
    # A: último dígito do ano (2025 -> '5')
    return str(dt.year % 10)


# ====================================================================
# [FIM BLOCO] _year_last_digit
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _month_no_leading_zero
# [RESPONSABILIDADE] Obter mês (1..12) sem zero à esquerda para composição do serial
# ====================================================================
def _month_no_leading_zero(dt: datetime) -> str:
    # M: mês 1..12 (sem zero à esquerda). Se preferir 2 dígitos: return f"{dt.month:02d}"
    return str(dt.month)


# ====================================================================
# [FIM BLOCO] _month_no_leading_zero
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _model_code
# [RESPONSABILIDADE] Resolver código do modelo a partir do dicionário de configuração
# ====================================================================
def _model_code(modelo: str) -> str:
    code = MODEL_CODE.get(modelo)
    if not code:
        raise ValueError(f"Modelo sem código configurado: {modelo}")
    return code


# ====================================================================
# [FIM BLOCO] _model_code
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _load_global_counter
# [RESPONSABILIDADE] Carregar contador global persistente a partir do arquivo de contador
# ====================================================================
def _load_global_counter() -> int:
    if not COUNTER_FILE.exists():
        return 0
    try:
        return int(COUNTER_FILE.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        # Se o arquivo estiver corrompido, NÃO quebrar o sistema; continuar a partir de 0
        return 0


# ====================================================================
# [FIM BLOCO] _load_global_counter
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _save_global_counter
# [RESPONSABILIDADE] Persistir o valor atualizado do contador global no arquivo de contador
# ====================================================================
def _save_global_counter(value: int) -> None:
    COUNTER_FILE.write_text(str(value), encoding="utf-8")


# ====================================================================
# [FIM BLOCO] _save_global_counter
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _audit_log_path
# [RESPONSABILIDADE] Determinar caminho do arquivo de auditoria anual para geração de seriais
# ====================================================================
def _audit_log_path(dt: datetime) -> Path:
    # um arquivo por ano para auditoria
    return LOG_DIR / f"serials_{dt.year}.txt"


# ====================================================================
# [FIM BLOCO] _audit_log_path
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _append_audit
# [RESPONSABILIDADE] Registrar linhas de auditoria no arquivo anual de seriais (append-only)
# ====================================================================
def _append_audit(lines: List[str], dt: datetime) -> None:
    p = _audit_log_path(dt)
    with p.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


# ====================================================================
# [FIM BLOCO] _append_audit
# ====================================================================

# --- API pública ----------------------------------------------------------


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] generate_serials
# [RESPONSABILIDADE] Gerar lista de números de série com contador global persistente e registrar auditoria
# ====================================================================
def generate_serials(
    modelo: str, qty: int, usuario: str = "Operador", now: datetime | None = None
) -> List[str]:
    """
    Gera números de série no formato: A + M + C(modelo) + SSS

      - A: último dígito do ano (2025 -> '5')
      - M: mês (1..12, sem zero à esquerda)
      - C(modelo): conforme MODEL_CODE
      - SSS: sequencial GLOBAL (mínimo 3 dígitos com zero-pad). NÃO reseta.

    Também registra auditoria em logs/serials_YYYY.txt (append-only).

    Retorna: lista de strings de tamanho 'qty'
    """
    if qty <= 0:
        return []

    dt = now or datetime.now()
    A = _year_last_digit(dt)
    M = _month_no_leading_zero(dt)
    C = _model_code(modelo)

    # contador GLOBAL persistente
    counter = _load_global_counter()

    serials: List[str] = []
    for _ in range(qty):
        counter += 1
        serials.append(
            f"{A}{M}{C}{counter:03d}"
        )  # >=1000 vira 1000, 1001... normalmente

    # Salva novo valor do contador
    _save_global_counter(counter)

    # Auditoria paralela (uma linha por série)
    stamp = dt.strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"{stamp};{modelo};{s};usr={usuario}" for s in serials]
    _append_audit(lines, dt)

    return serials


# ====================================================================
# [FIM BLOCO] generate_serials
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: MODEL_CODE
# BLOCO_UTIL: LOG_DIR
# BLOCO_UTIL: COUNTER_FILE
# FUNÇÃO: _year_last_digit
# FUNÇÃO: _month_no_leading_zero
# FUNÇÃO: _model_code
# FUNÇÃO: _load_global_counter
# FUNÇÃO: _save_global_counter
# FUNÇÃO: _audit_log_path
# FUNÇÃO: _append_audit
# FUNÇÃO: generate_serials
# ====================================================================
