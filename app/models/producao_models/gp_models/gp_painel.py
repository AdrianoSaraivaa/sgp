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
from ..seriais import WorkOrder, WorkStage, RopAlert  # noqa: F401  pylint: disable=unused-import


@dataclass
class GPModel(BaseModel):
    """Represents a machine model configured for the GP process."""

    __tablename__ = "gp_model"

    id: Optional[int] = field(default=None)
    nome: str = field(default="")

    def __repr__(self) -> str:
        return f"<GPModel nome={self.nome}>"


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

    def __repr__(self) -> str:
        return f"<BenchConfig model_id={self.model_id} bench_id={self.bench_id}>"


__all__ = [
    "GPModel",
    "BenchConfig",
    "WorkOrder",
    "WorkStage",
    "RopAlert",
]