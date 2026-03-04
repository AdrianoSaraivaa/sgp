"""Legacy module for GP model management.

Historically, the ``gp_modelos`` module provided access to model
configuration classes for the GP system.  In this refactored version
the canonical SQLAlchemy models live in ``app.models_sqla``.  To
support existing imports like ``from app.models.producao_models.gp_modelos
import GPModel``, we re-export those classes here.

Developers should prefer importing directly from ``app.models_sqla``.
"""

from app.models_sqla import GPModel, GPBenchConfig

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] ReexportGPModelos
# [RESPONSABILIDADE] Reexportar modelos GPModel e GPBenchConfig para compatibilidade com imports legados
# ====================================================================

# ====================================================================
# [FIM BLOCO] ReexportGPModelos
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] __all__
# [RESPONSABILIDADE] Definir símbolos públicos exportados pelo módulo para importações compatíveis
# ====================================================================
__all__ = ["GPModel", "GPBenchConfig"]
# ====================================================================
# [FIM BLOCO] __all__
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: ReexportGPModelos
# BLOCO_UTIL: __all__
# ====================================================================
