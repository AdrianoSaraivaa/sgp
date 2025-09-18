
"""Compatibility wrapper for ROP alerts.

In the original codebase the ROP alert model lived in
``app.models.producao_models.painel_models.alerts`` as ``GPRopAlert``.  In
this refactored version the SQLAlchemy model class lives in
``app.models_sqla`` and is named ``GPROPAlert`` to follow a consistent
prefixing scheme.

This module re-exports that class under both the new and legacy names
so that imports like ``from app.models.producao_models.painel_models.alerts
import GPRopAlert`` continue to work.
"""

from app.models_sqla import GPROPAlert as GPROPAlert

# Backwards-compatible alias
GPRopAlert = GPROPAlert

__all__ = ["GPROPAlert", "GPRopAlert"]
