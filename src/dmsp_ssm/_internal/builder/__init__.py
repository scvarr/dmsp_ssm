"""Внутренние контракты слоя сборки."""

from .contracts import (
    BuilderArtifact,
    SupportsDecodedRecordBuilder,
)
from .xarray_builder import (
    XArrayBuilder,
    XArrayDimensionModel,
)
from .numpy_builder import (
    NumpyBuilder,
)
from .table_builder import (
    TableBuilder,
)

__all__ = [
    "BuilderArtifact",
    "SupportsDecodedRecordBuilder",
    "XArrayDimensionModel",
    "XArrayBuilder",
    "NumpyBuilder",
    "TableBuilder",
]
