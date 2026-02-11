"""Alias module for work order/ordem models.

This module makes the ``WorkOrder`` model available under the
Portuguese name ``Ordem``.  Both names refer to the same table and
fields in the database; choosing one name over the other is a matter
of preference in the calling code.
"""

from ..seriais import WorkOrder as _WorkOrder


class WorkOrder(_WorkOrder):
    """Concrete subclass for IDE friendliness.

    Inherits all behaviour from ``_WorkOrder`` without modification.
    """

    pass


Ordem = WorkOrder  # Alias for Portuguese naming

__all__ = ["WorkOrder", "Ordem"]