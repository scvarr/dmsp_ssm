"""Внутренние контрактные границы слоя компоновки."""

from .artifact_accumulator import accumulate_artifact_bundle
from .contracts import (
    ArtifactBundle,
    ProfileArtifactRequirements,
    OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS,
    SupportsParseResultAssembler,
)
from .in_memory import (
    InMemoryParseResultAssembler,
)

__all__ = [
    "ArtifactBundle",
    "ProfileArtifactRequirements",
    "OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS",
    "SupportsParseResultAssembler",
    "InMemoryParseResultAssembler",
    "accumulate_artifact_bundle"
]
