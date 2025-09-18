
"""Compatibility wrapper for GPHipotRun.

The original codebase defined a dataclass ``HipotRun`` in this module.
After migrating to SQLAlchemy models, the corresponding class is
``GPHipotRun`` in ``app.models_sqla``.  To preserve existing import paths
and names, this module re-exports ``GPHipotRun`` and aliases ``HipotRun``
to it.
"""

from app.models_sqla import GPHipotRun

# Backwards-compatible alias: some code imported ``HipotRun`` from this
# module.  We alias it to the SQLAlchemy model class.
HipotRun = GPHipotRun

__all__ = ["GPHipotRun", "HipotRun"]
