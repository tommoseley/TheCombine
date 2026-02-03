"""
Configuration package for Git-canonical document type management.

Per ADR-044, all document configuration is stored in combine-config/ and
loaded via this module. Runtime systems read from this module, not from
seed/ or database registries directly.
"""

from app.config.package_model import (
    DocumentTypePackage,
    RolePrompt,
    Template,
    ActiveReleases,
)
from app.config.package_loader import (
    PackageLoader,
    get_package_loader,
)

__all__ = [
    "DocumentTypePackage",
    "RolePrompt",
    "Template",
    "ActiveReleases",
    "PackageLoader",
    "get_package_loader",
]
