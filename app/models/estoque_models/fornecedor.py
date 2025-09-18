"""Supplier model definitions.

The :class:`Fornecedor` class maps onto the ``fornecedores`` table
in the SQLite database.  It captures basic contact information for
companies that supply parts to the business.  This dataclass uses
simple SQLite queries via :class:`~app.models.base_model.BaseModel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..base_model import BaseModel


@dataclass
class Fornecedor(BaseModel):
    """Represents a supplier in the inventory system."""

    __tablename__ = "fornecedores"

    id: Optional[int] = field(default=None)
    nome_empresa: str = field(default="")
    nome_contato: str = field(default="")
    telefone1: Optional[str] = field(default=None)
    telefone2: Optional[str] = field(default=None)
    email1: Optional[str] = field(default=None)
    email2: Optional[str] = field(default=None)

    def __repr__(self) -> str:
        return f"<Fornecedor {self.nome_empresa}>"