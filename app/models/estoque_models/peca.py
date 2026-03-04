"""Part model definitions.

The :class:`Peca` dataclass represents individual parts or
components used in the production process.  It maps onto the
``pecas`` table in the database and stores details such as codes,
stock levels and pricing information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..base_model import BaseModel


# ====================================================================
# [BLOCO] CLASSE
# [NOME] Peca
# [RESPONSABILIDADE] Representar peça/conjunto no estoque mapeado para a tabela "pecas"
# ====================================================================
@dataclass
class Peca(BaseModel):
    """Represents a part in inventory."""

    __tablename__ = "pecas"

    id: Optional[int] = field(default=None)
    tipo: Optional[str] = field(default=None)
    descricao: Optional[str] = field(default=None)
    codigo_pneumark: Optional[str] = field(default=None)
    codigo_omie: Optional[str] = field(default=None)
    estoque_minimo: Optional[int] = field(default=None)
    ponto_pedido: Optional[int] = field(default=None)
    estoque_maximo: Optional[int] = field(default=None)
    estoque_atual: Optional[int] = field(default=None)
    margem: Optional[float] = field(default=None)
    custo: Optional[float] = field(default=None)

    # ====================================================================
    # [BLOCO] MÉTODO
    # [NOME] __repr__
    # [RESPONSABILIDADE] Retornar representação textual resumida da peça para debug/log
    # ====================================================================
    def __repr__(self) -> str:
        return f"<Peca {self.codigo_pneumark or self.id}>"

    # ====================================================================
    # [FIM BLOCO] __repr__
    # ====================================================================


# ====================================================================
# [FIM BLOCO] Peca
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# CLASSE: Peca
# MÉTODO: __repr__
# ====================================================================
