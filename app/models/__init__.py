
"""Top‑level package for application models.

This module aggregates all dataclass‑based models defined within the
``app.models`` package.  Models inherit from :class:`BaseModel` and
map directly onto tables in the underlying SQLite database.

Importing this package ensures that all model classes are loaded and
available for use.  You can refer to individual models via attributes
on this module, e.g. ``app.models.Peca`` or ``app.models.Montagem``.
"""

from .base_model import BaseModel  # noqa: F401  pylint: disable=unused-import

# Inventory models
from .estoque_models.peca import Peca  # noqa: F401  pylint: disable=unused-import
from .estoque_models.fornecedor import Fornecedor  # noqa: F401  pylint: disable=unused-import

# Production models
from .producao_models.montagem import Montagem, LabelReprintLog  # noqa: F401  pylint: disable=unused-import
from .producao_models.seriais import WorkOrder, WorkStage, RopAlert  # noqa: F401  pylint: disable=unused-import

# GP models
from .producao_models.gp_models.gp_checklist import (
    ChecklistTemplate,
    ChecklistItem,
    ChecklistExecution,
    ChecklistExecutionItem,
)  # noqa: F401  pylint: disable=unused-import
from .producao_models.gp_models.gp_hipot import HipotRun  # noqa: F401  pylint: disable=unused-import
from .producao_models.gp_models.gp_painel import BenchConfig, GPModel  # noqa: F401  pylint: disable=unused-import

__all__ = [
    # Base
    "BaseModel",
    # Inventory
    "Peca",
    "Fornecedor",
    # Production
    "Montagem",
    "LabelReprintLog",
    "WorkOrder",
    "WorkStage",
    "RopAlert",
    # GP checklist
    "ChecklistTemplate",
    "ChecklistItem",
    "ChecklistExecution",
    "ChecklistExecutionItem",
    # GP hipot
    "HipotRun",
    # GP painel
    "BenchConfig",
    "GPModel",
]

# ------------------------------------------------------------
# Compatibilidade com SQLAlchemy
# ------------------------------------------------------------
# Alguns módulos legados importam ``EstruturaMaquina`` diretamente de
# ``app.models``.  Para não quebrar esses imports, reexportamos o
# modelo SQLAlchemy a partir de ``app.models_sqla``.  Caso adicione
# outros modelos SQLAlchemy aqui, lembre-se de adicioná-los ao
# ``__all__``.
try:
    from app.models_sqla import EstruturaMaquina as _SQLA_EstruturaMaquina  # type: ignore
    EstruturaMaquina = _SQLA_EstruturaMaquina  # alias público
    __all__.append("EstruturaMaquina")
except Exception:
    # se models_sqla não estiver disponível, apenas ignore
    pass