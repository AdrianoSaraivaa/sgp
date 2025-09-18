"""Models for GP checklists.

These dataclasses map to the checklist tables used to define and
execute production checklists.  They provide simple CRUD operations
via :class:`~app.models.base_model.BaseModel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from ...base_model import BaseModel


@dataclass
class ChecklistTemplate(BaseModel):
    """Represents a reusable template for a production checklist."""

    __tablename__ = "gp_checklist_templates"

    id: Optional[int] = field(default=None)
    modelo: str = field(default="")
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ChecklistTemplate modelo={self.modelo}>"


@dataclass
class ChecklistItem(BaseModel):
    """Represents a single step within a checklist template."""

    __tablename__ = "gp_checklist_items"

    id: Optional[int] = field(default=None)
    template_id: int = field(default=0)
    ordem: int = field(default=0)
    descricao: str = field(default="")
    tempo_seg: int = field(default=0)
    ncr_tags: Optional[Any] = field(default=None)

    def __repr__(self) -> str:
        return f"<ChecklistItem {self.ordem} for template={self.template_id}>"


@dataclass
class ChecklistExecution(BaseModel):
    """Represents an execution instance of a checklist against a serial number."""

    __tablename__ = "gp_checklist_execucoes"

    id: Optional[int] = field(default=None)
    serial: str = field(default="")
    modelo: Optional[str] = field(default=None)
    operador: Optional[str] = field(default=None)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = field(default=None)
    result: Optional[str] = field(default=None)

    def __repr__(self) -> str:
        return f"<ChecklistExecution serial={self.serial} result={self.result}>"


@dataclass
class ChecklistExecutionItem(BaseModel):
    """Represents the execution of a single checklist item within an execution."""

    __tablename__ = "gp_checklist_exec_items"

    id: Optional[int] = field(default=None)
    exec_id: int = field(default=0)
    ordem: int = field(default=0)
    descricao: str = field(default="")
    tempo_estimado_seg: int = field(default=0)
    status: Optional[str] = field(default=None)
    started_at: Optional[datetime] = field(default=None)
    finished_at: Optional[datetime] = field(default=None)
    elapsed_seg: Optional[int] = field(default=None)
    ncrs: Optional[Any] = field(default=None)

    def __repr__(self) -> str:
        return f"<ChecklistExecutionItem exec_id={self.exec_id} ordem={self.ordem}>"
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
