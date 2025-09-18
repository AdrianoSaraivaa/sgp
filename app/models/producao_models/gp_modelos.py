
"""Legacy module for GP model management.

Historically, the ``gp_modelos`` module provided access to model
configuration classes for the GP system.  In this refactored version
the canonical SQLAlchemy models live in ``app.models_sqla``.  To
support existing imports like ``from app.models.producao_models.gp_modelos
import GPModel``, we re-export those classes here.

Developers should prefer importing directly from ``app.models_sqla``.
"""

from app.models_sqla import GPModel, GPBenchConfig

__all__ = ["GPModel", "GPBenchConfig"]
