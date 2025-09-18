"""Assembly and label reprint models.

The :class:`Montagem` dataclass records the assembly of machines and
associated metadata.  The :class:`LabelReprintLog` dataclass logs
each time a label is reprinted for a given assembly.  These
dataclasses operate directly against the ``montagens`` and
``label_reprint_logs`` tables using the helper methods provided by
:class:`~app.models.base_model.BaseModel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..base_model import BaseModel


@dataclass
class Montagem(BaseModel):
    """Represents an assembly (montagem) of a machine or product."""

    __tablename__ = "montagens"

    id: Optional[int] = field(default=None)
    modelo: str = field(default="")
    serial: str = field(default="")
    data_hora: datetime = field(default_factory=datetime.utcnow)
    usuario: str = field(default="")
    status: str = field(default="")
    cancel_reason: Optional[str] = field(default=None)
    cancel_at: Optional[datetime] = field(default=None)
    cancel_by: Optional[str] = field(default=None)
    label_printed: Optional[bool] = field(default=False)
    label_printed_at: Optional[datetime] = field(default=None)
    label_printed_by: Optional[str] = field(default=None)
    label_print_count: Optional[int] = field(default=0)
    qrcode_path: Optional[str] = field(default=None)
    label_path: Optional[str] = field(default=None)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Montagem {self.modelo} serial={self.serial}>"


@dataclass
class LabelReprintLog(BaseModel):
    """Logs each label reprint for a given assembly."""

    __tablename__ = "label_reprint_logs"

    id: Optional[int] = field(default=None)
    montagem_id: int = field(default=0)
    motivo: str = field(default="")
    reprint_by: str = field(default="")
    reprint_at: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<LabelReprintLog montagem_id={self.montagem_id} at={self.reprint_at}>"