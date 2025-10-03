"""Compatibility wrapper for GP checklist models.

The original codebase defined several dataclasses in this module:

  - ChecklistTemplate
  - ChecklistItem
  - ChecklistExecution
  - ChecklistExecutionItem

After migrating to SQLAlchemy, the corresponding classes live in
``app.models_sqla`` and are prefixed with ``GP``.  To maintain
backwards compatibility with import paths and names, this module
re-exports those SQLAlchemy models and provides aliases matching the
original names.  It also defines ``ChecklistExec`` and
``ChecklistExecItem`` aliases, which some routes expect.
"""

from app.models_sqla import (
    GPChecklistTemplate,
    GPChecklistItem,
    GPChecklistExecution,
    GPChecklistExecutionItem,
)

# Backwards-compatible aliases
ChecklistTemplate = GPChecklistTemplate
ChecklistItem = GPChecklistItem
ChecklistExecution = GPChecklistExecution
ChecklistExecutionItem = GPChecklistExecutionItem

# Additional aliases used by some routes
ChecklistExec = GPChecklistExecution
ChecklistExecItem = GPChecklistExecutionItem

__all__ = [
    "GPChecklistTemplate",
    "GPChecklistItem",
    "GPChecklistExecution",
    "GPChecklistExecutionItem",
    "ChecklistTemplate",
    "ChecklistItem",
    "ChecklistExecution",
    "ChecklistExecutionItem",
    "ChecklistExec",
    "ChecklistExecItem",
]
