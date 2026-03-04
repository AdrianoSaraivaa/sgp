"""Compatibility wrapper for GPHipotRun.

The original codebase defined a dataclass ``HipotRun`` in this module.
After migrating to SQLAlchemy models, the corresponding class is
``GPHipotRun`` in ``app.models_sqla``.  To preserve existing import paths
and names, this module re-exports ``GPHipotRun`` and aliases ``HipotRun``
to it.
"""

from app.models_sqla import GPHipotRun

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] AliasHipotRun
# [RESPONSABILIDADE] Reexportar modelo GPHipotRun e manter alias HipotRun para compatibilidade legada
# ====================================================================

# Backwards-compatible alias: some code imported ``HipotRun`` from this
# module.  We alias it to the SQLAlchemy model class.
HipotRun = GPHipotRun

# ====================================================================
# [FIM BLOCO] AliasHipotRun
# ====================================================================

# ====================================================================
# [BLOCO] BLOCO_UTIL
# [NOME] __all__
# [RESPONSABILIDADE] Definir símbolos públicos exportados pelo módulo para importações compatíveis
# ====================================================================
__all__ = ["GPHipotRun", "HipotRun"]
# ====================================================================
# [FIM BLOCO] __all__
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_UTIL: AliasHipotRun
# BLOCO_UTIL: __all__
# ====================================================================
