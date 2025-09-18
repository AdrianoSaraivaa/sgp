"""Models related to serialised work orders and stages.

These dataclasses provide simple data containers for work orders,
their stages and reorder point alerts.  They map directly onto
``gp_work_order``, ``gp_work_stage`` and ``gp_rop_alerts`` tables
and provide helper methods via :class:`~app.models.base_model.BaseModel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..base_model import BaseModel


@dataclass
class WorkOrder(BaseModel):
    """Represents an order tied to a specific serial number."""

    __tablename__ = "gp_work_order"

    id: Optional[int] = field(default=None)
    serial: str = field(default="")
    modelo: str = field(default="")
    current_bench: str = field(default="")
    status: str = field(default="")
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    hipot_flag: bool = field(default=False)
    hipot_status: str = field(default="")
    hipot_last_at: Optional[datetime] = field(default=None)

    def __repr__(self) -> str:
        return f"<WorkOrder serial={self.serial} bench={self.current_bench} status={self.status}>"


@dataclass
class WorkStage(BaseModel):
    """Represents a step (etapa) in the progression of a work order."""

    __tablename__ = "gp_work_stage"

    id: Optional[int] = field(default=None)
    order_id: int = field(default=0)
    bench_id: str = field(default="")
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = field(default=None)
    operador: Optional[str] = field(default=None)
    observacoes: Optional[str] = field(default=None)

    def __repr__(self) -> str:
        return f"<WorkStage order_id={self.order_id} bench={self.bench_id}>"


@dataclass
class RopAlert(BaseModel):
    """Represents an alert generated when a part reaches its reorder point."""

    __tablename__ = "gp_rop_alerts"

    id: Optional[int] = field(default=None)
    peca_id: int = field(default=0)
    in_alert: bool = field(default=True)
    last_sent_at: Optional[datetime] = field(default=None)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RopAlert peca_id={self.peca_id} active={self.in_alert}>"