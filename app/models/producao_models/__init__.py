"""Production models package.

This package houses dataclass models describing the production
process, assembly records, work orders, stages and specialised GP
subsystems.  All models inherit from
``app.models.base_model.BaseModel`` and can perform basic CRUD
operations against the SQLite database without requiring external
ORM dependencies.
"""

# Re-export commonly used production models at the package level.
from .montagem import Montagem, LabelReprintLog  # noqa: F401  pylint: disable=unused-import
from .seriais import WorkOrder, WorkStage, RopAlert  # noqa: F401  pylint: disable=unused-import

# GP models reside in the ``gp_models`` subpackage.
from .gp_models.gp_checklist import (
    ChecklistTemplate,
    ChecklistItem,
    ChecklistExecution,
    ChecklistExecutionItem,
)  # noqa: F401  pylint: disable=unused-import
from .gp_models.gp_hipot import HipotRun  # noqa: F401  pylint: disable=unused-import
from .gp_models.gp_painel import BenchConfig, GPModel  # noqa: F401  pylint: disable=unused-import

# Panel aliases
from .painel_models.etapa import Etapa  # noqa: F401  pylint: disable=unused-import
from .painel_models.ordem import Ordem  # noqa: F401  pylint: disable=unused-import

__all__ = [
    "Montagem",
    "LabelReprintLog",
    "WorkOrder",
    "WorkStage",
    "RopAlert",
    "ChecklistTemplate",
    "ChecklistItem",
    "ChecklistExecution",
    "ChecklistExecutionItem",
    "HipotRun",
    "BenchConfig",
    "GPModel",
    "Etapa",
    "Ordem",
]