"""Models backing the production dashboard/panel user interface.

This subpackage exposes the ``WorkStage`` and ``WorkOrder`` models
under Portuguese‑friendly names (``Etapa`` and ``Ordem``).  These
aliases make it easier to reason about the domain when working in a
Portuguese codebase.
"""

from .etapa import Etapa, WorkStage  # noqa: F401  pylint: disable=unused-import
from .ordem import Ordem, WorkOrder  # noqa: F401  pylint: disable=unused-import

__all__ = ["Etapa", "Ordem", "WorkStage", "WorkOrder"]