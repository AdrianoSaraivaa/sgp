
"""Legacy module for GP execution logic.

This module historically provided access to GP-related model classes such
as work orders, work stages and checklist executions.  The original
project defined these in various submodules under
``app.models.producao_models``.  To maintain backwards compatibility
with imports like ``from app.models.producao_models.gp_execucao import
GPWorkOrder``, we re-export the SQLAlchemy models defined in
``app.models_sqla`` here.

Developers are encouraged to import these classes directly from
``app.models_sqla`` for clarity.
"""

from app.models_sqla import (
    GPWorkOrder,
    GPWorkStage,
    GPChecklistExecution,
    GPChecklistExecutionItem,
    GPChecklistTemplate,
    GPChecklistItem,
)

# Re-export for backwards compatibility.  When wildcard importing from
# this module, only the names defined here will be exposed.
__all__ = [
    "GPWorkOrder",
    "GPWorkStage",
    "GPChecklistExecution",
    "GPChecklistExecutionItem",
    "GPChecklistTemplate",
    "GPChecklistItem",
]
