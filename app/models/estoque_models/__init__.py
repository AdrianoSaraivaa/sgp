"""Inventory models package.

This subpackage collects simple dataclass models related to the
inventory domain, such as parts (``Peca``) and suppliers
(``Fornecedor``).  Importing this package ensures the dataclasses are
available for use.
"""

# Re-export individual models for convenient import elsewhere.
from .peca import Peca  # noqa: F401  pylint: disable=unused-import
from .fornecedor import Fornecedor  # noqa: F401  pylint: disable=unused-import

__all__ = ["Peca", "Fornecedor"]