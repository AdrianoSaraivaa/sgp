"""Alias module for work stage/etapa models.

To keep the model names intuitive for Portuguese speakers, this module
re-exports the ``WorkStage`` model from the serials module under the
alternative name ``Etapa``.  The underlying table and behaviour are
unchanged; this is purely a naming convenience.
"""

from ..seriais import WorkStage as _WorkStage


class WorkStage(_WorkStage):
    """Concrete subclass for IDE friendliness.

    This class does not change behaviour from its base class but
    provides an anchor point for documentation and type checking.
    """

    pass


Etapa = WorkStage  # Alias for Portuguese naming

__all__ = ["WorkStage", "Etapa"]