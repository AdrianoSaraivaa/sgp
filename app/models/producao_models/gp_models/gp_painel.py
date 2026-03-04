"""Models for the GP production panel.

This module defines dataclasses for machine models and bench
configurations used in the production panel.  These dataclasses map
to the ``gp_model`` and ``gp_bench_config`` tables in the database.
Work orders and stages are defined separately in
``app.models.producao_models.seriais`` but are imported here for
convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ...base_model import BaseModel
from ..seriais import (
    WorkOrder,
    WorkStage,
    RopAlert,
)  # noqa: F401  pylint: disable=unused-import


# ====================================================================
# [BLOCO] CLASSE
# [NOME] GPModel
# [RESPONSABILIDADE] Representar modelo de máquina configurado para o processo GP (tabela gp_model)
# ====================================================================
@dataclass
class GPModel(BaseModel):
    """Represents a machine model configured for the GP process."""

    __tablename__ = "gp_model"

    id: Optional[int] = field(default=None)
    nome: str = field(default="")

    # ====================================================================
    # [BLOCO] MÉTODO
    # [NOME] __repr__
    # [RESPONSABILIDADE] Retornar representação textual resumida do modelo para debug/log
    # ====================================================================
    def __repr__(self) -> str:
        return f"<GPModel nome={self.nome}>"

    # ====================================================================
    # [FIM BLOCO] __repr__
    # ====================================================================


# ====================================================================
# [FIM BLOCO] GPModel
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] BenchConfig
# [RESPONSABILIDADE] Representar configuração de bancada por modelo com parâmetros de tempo e responsabilidades
# ====================================================================
@dataclass
class BenchConfig(BaseModel):
    """Configuration linking a model to a bench with timing information."""

    __tablename__ = "gp_bench_config"

    id: Optional[int] = field(default=None)
    model_id: int = field(default=0)
    bench_id: str = field(default="")
    ativo: Optional[bool] = field(default=None)
    obrigatorio: Optional[bool] = field(default=None)
    tempo_min: Optional[int] = field(default=None)
    tempo_esperado: Optional[int] = field(default=None)
    tempo_max: Optional[int] = field(default=None)
    operador: Optional[str] = field(default=None)
    responsavel: Optional[str] = field(default=None)
    observacoes: Optional[str] = field(default=None)

    # ====================================================================
    # [BLOCO] MÉTODO
    # [NOME] __repr__
    # [RESPONSABILIDADE] Retornar representação textual resumida da configuração de bancada para debug/log
    # ====================================================================
    def __repr__(self) -> str:
        return f"<BenchConfig model_id={self.model_id} bench_id={self.bench_id}>"

    # ====================================================================
    # [FIM BLOCO] __repr__
    # ====================================================================


# ====================================================================
# [FIM BLOCO] BenchConfig
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] __all__
# [RESPONSABILIDADE] Definir símbolos públicos exportados pelo módulo para uso externo
# ====================================================================
__all__ = [
    "GPModel",
    "BenchConfig",
    "WorkOrder",
    "WorkStage",
    "RopAlert",
]
# ====================================================================
# [FIM BLOCO] __all__
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# CLASSE: GPModel
# MÉTODO: __repr__
# CLASSE: BenchConfig
# MÉTODO: __repr__
# BLOCO_UTIL: __all__
# ====================================================================
