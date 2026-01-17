"""
Seed data for registry tables (fragments, components, schemas, document types).

Per ADR-032: Canonical artifacts are seeded as governed items.

Usage:
    from seed.registry import (
        INITIAL_COMPONENT_ARTIFACTS,
        INITIAL_FRAGMENT_ARTIFACTS,
        INITIAL_SCHEMA_ARTIFACTS,
        INITIAL_DOCUMENT_TYPES,
    )
"""

from seed.registry.component_artifacts import INITIAL_COMPONENT_ARTIFACTS
from seed.registry.document_types import INITIAL_DOCUMENT_TYPES
from seed.registry.fragment_artifacts import INITIAL_FRAGMENT_ARTIFACTS
from seed.registry.schema_artifacts import INITIAL_SCHEMA_ARTIFACTS

__all__ = [
    "INITIAL_COMPONENT_ARTIFACTS",
    "INITIAL_DOCUMENT_TYPES",
    "INITIAL_FRAGMENT_ARTIFACTS",
    "INITIAL_SCHEMA_ARTIFACTS",
]
