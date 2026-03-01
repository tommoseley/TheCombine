"""
Mechanical Operations Service.

Per ADR-047, this service provides access to Mechanical Operation types
(from the registry) and operation instances (from combine-config/).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.config.package_loader import (
    PackageLoader,
    PackageLoaderError,
    PackageNotFoundError,
    get_package_loader,
)

logger = logging.getLogger(__name__)


@dataclass
class OperationType:
    """A mechanical operation type from the registry."""
    id: str
    name: str
    description: str
    icon: str
    category: str
    config_schema: Dict[str, Any]
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]


@dataclass
class OperationCategory:
    """A category for grouping operation types."""
    id: str
    name: str
    description: str


@dataclass
class MechanicalOperation:
    """A mechanical operation instance."""
    id: str
    version: str
    type: str
    name: str
    description: str
    config: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class MechanicalOpsService:
    """
    Service for Mechanical Operations.

    Provides access to operation types from the registry and
    operation instances from combine-config/mechanical_ops/.
    """

    def __init__(self, loader: Optional[PackageLoader] = None):
        """
        Initialize the service.

        Args:
            loader: Optional PackageLoader instance. Uses singleton if not provided.
        """
        self._loader = loader or get_package_loader()
        self._types_cache: Optional[Dict[str, OperationType]] = None
        self._categories_cache: Optional[Dict[str, OperationCategory]] = None

    def _get_registry_path(self) -> Path:
        """Get the path to the operation type registry."""
        return self._loader.config_path / "mechanical_ops" / "_registry" / "types.yaml"

    def _load_registry(self) -> Dict[str, Any]:
        """Load the operation type registry YAML."""
        registry_path = self._get_registry_path()

        if not registry_path.exists():
            logger.warning(f"Mechanical ops registry not found: {registry_path}")
            return {"types": {}, "categories": {}}

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"types": {}, "categories": {}}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse mechanical ops registry: {e}")
            return {"types": {}, "categories": {}}

    def _ensure_types_loaded(self) -> None:
        """Ensure operation types are loaded from registry."""
        if self._types_cache is not None:
            return

        registry = self._load_registry()

        self._types_cache = {}
        for type_id, type_data in registry.get("types", {}).items():
            self._types_cache[type_id] = OperationType(
                id=type_id,
                name=type_data.get("name", type_id),
                description=type_data.get("description", ""),
                icon=type_data.get("icon", "cog"),
                category=type_data.get("category", "uncategorized"),
                config_schema=type_data.get("config_schema", {}),
                inputs=type_data.get("inputs", []),
                outputs=type_data.get("outputs", []),
            )

        self._categories_cache = {}
        for cat_id, cat_data in registry.get("categories", {}).items():
            self._categories_cache[cat_id] = OperationCategory(
                id=cat_id,
                name=cat_data.get("name", cat_id),
                description=cat_data.get("description", ""),
            )

    # =========================================================================
    # Operation Types (from Registry)
    # =========================================================================

    def list_operation_types(self) -> List[Dict[str, Any]]:
        """
        List all operation types from the registry.

        Returns:
            List of operation type summaries
        """
        self._ensure_types_loaded()

        return [
            {
                "type_id": op_type.id,
                "name": op_type.name,
                "description": op_type.description,
                "icon": op_type.icon,
                "category": op_type.category,
            }
            for op_type in sorted(self._types_cache.values(), key=lambda t: t.name)
        ]

    def get_operation_type(self, type_id: str) -> Dict[str, Any]:
        """
        Get a specific operation type with its full config schema.

        Args:
            type_id: Operation type identifier

        Returns:
            Full operation type details

        Raises:
            PackageNotFoundError: Type not found
        """
        self._ensure_types_loaded()

        op_type = self._types_cache.get(type_id)
        if not op_type:
            raise PackageNotFoundError(f"Operation type not found: {type_id}")

        return {
            "type_id": op_type.id,
            "name": op_type.name,
            "description": op_type.description,
            "icon": op_type.icon,
            "category": op_type.category,
            "config_schema": op_type.config_schema,
            "inputs": op_type.inputs,
            "outputs": op_type.outputs,
        }

    def list_categories(self) -> List[Dict[str, Any]]:
        """
        List all operation categories.

        Returns:
            List of category summaries
        """
        self._ensure_types_loaded()

        return [
            {
                "category_id": cat.id,
                "name": cat.name,
                "description": cat.description,
            }
            for cat in sorted(self._categories_cache.values(), key=lambda c: c.name)
        ]

    # =========================================================================
    # Operation Instances (from combine-config)
    # =========================================================================

    def list_operations(self) -> List[Dict[str, Any]]:
        """
        List all operation instances.

        Returns:
            List of operation instance summaries
        """
        self._ensure_types_loaded()

        ops_dir = self._loader.config_path / "mechanical_ops"
        if not ops_dir.exists():
            return []

        active = self._loader.get_active_releases()
        active_mech_ops = getattr(active, "mechanical_ops", {}) or {}

        # Also check raw dict if attribute doesn't exist
        if not active_mech_ops:
            try:
                import json
                active_path = self._loader.config_path / "_active" / "active_releases.json"
                if active_path.exists():
                    with open(active_path, "r", encoding="utf-8") as f:
                        active_data = json.load(f)
                        active_mech_ops = active_data.get("mechanical_ops", {})
            except Exception:
                pass

        summaries = []
        for op_dir in sorted(ops_dir.iterdir()):
            if not op_dir.is_dir() or op_dir.name.startswith("_"):
                continue

            op_id = op_dir.name
            active_version = active_mech_ops.get(op_id)

            if not active_version:
                # Try to find any version
                releases_dir = op_dir / "releases"
                if releases_dir.exists():
                    versions = sorted([d.name for d in releases_dir.iterdir() if d.is_dir()])
                    if versions:
                        active_version = versions[-1]

            if not active_version:
                continue

            try:
                from app.api.services.service_pure import build_operation_summary

                op = self._load_operation(op_id, active_version)
                op_type = self._types_cache.get(op.type)

                summaries.append(build_operation_summary(
                    op_id=op.id,
                    op_name=op.name,
                    op_description=op.description,
                    op_type=op.type,
                    op_metadata=op.metadata,
                    type_name=op_type.name if op_type else None,
                    type_category=op_type.category if op_type else None,
                    active_version=active_version,
                ))
            except Exception as e:
                logger.warning(f"Could not load operation {op_id}: {e}")
                summaries.append({
                    "op_id": op_id,
                    "name": op_id,
                    "description": None,
                    "type": None,
                    "type_name": None,
                    "category": "uncategorized",
                    "active_version": active_version,
                    "tags": [],
                    "error": str(e),
                })

        return summaries

    def _load_operation(self, op_id: str, version: str) -> MechanicalOperation:
        """
        Load an operation instance from disk.

        Args:
            op_id: Operation identifier
            version: Version string

        Returns:
            MechanicalOperation instance

        Raises:
            PackageNotFoundError: Operation not found
        """
        op_path = (
            self._loader.config_path / "mechanical_ops" / op_id /
            "releases" / version / "operation.yaml"
        )

        if not op_path.exists():
            raise PackageNotFoundError(f"Operation not found: {op_id} v{version}")

        try:
            with open(op_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PackageLoaderError(f"Failed to parse operation {op_id}: {e}")

        return MechanicalOperation(
            id=data.get("id", op_id),
            version=data.get("version", version),
            type=data.get("type", "unknown"),
            name=data.get("name", op_id),
            description=data.get("description", ""),
            config=data.get("config", {}),
            metadata=data.get("metadata", {}),
        )

    def get_operation(
        self,
        op_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific operation instance.

        Args:
            op_id: Operation identifier
            version: Specific version or None for active version

        Returns:
            Full operation details

        Raises:
            PackageNotFoundError: Operation not found
        """
        self._ensure_types_loaded()

        if version is None:
            active = self._loader.get_active_releases()
            active_mech_ops = getattr(active, "mechanical_ops", {}) or {}

            # Fallback to raw JSON
            if not active_mech_ops:
                try:
                    import json
                    active_path = self._loader.config_path / "_active" / "active_releases.json"
                    if active_path.exists():
                        with open(active_path, "r", encoding="utf-8") as f:
                            active_data = json.load(f)
                            active_mech_ops = active_data.get("mechanical_ops", {})
                except Exception:
                    pass

            version = active_mech_ops.get(op_id)
            if not version:
                raise PackageNotFoundError(f"No active version for operation: {op_id}")

        op = self._load_operation(op_id, version)
        op_type = self._types_cache.get(op.type)

        return {
            "op_id": op.id,
            "version": op.version,
            "type": op.type,
            "type_name": op_type.name if op_type else op.type,
            "category": op_type.category if op_type else "uncategorized",
            "name": op.name,
            "description": op.description,
            "config": op.config,
            "config_schema": op_type.config_schema if op_type else {},
            "inputs": op_type.inputs if op_type else [],
            "outputs": op_type.outputs if op_type else [],
            "metadata": op.metadata,
        }

    # =========================================================================
    # Cache Management
    # =========================================================================

    def invalidate_cache(self) -> None:
        """Invalidate cached data."""
        self._types_cache = None
        self._categories_cache = None


# Module-level singleton
_service: Optional[MechanicalOpsService] = None


def get_mechanical_ops_service() -> MechanicalOpsService:
    """Get the singleton MechanicalOpsService instance."""
    global _service
    if _service is None:
        _service = MechanicalOpsService()
    return _service


def reset_mechanical_ops_service() -> None:
    """Reset the singleton (for testing)."""
    global _service
    _service = None
