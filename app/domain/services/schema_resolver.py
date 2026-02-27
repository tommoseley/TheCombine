"""
Schema Resolver for ADR-031.

Resolves $ref: "schema:<id>" references and produces self-contained bundles.
"""

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


from app.api.services.schema_registry_service import SchemaRegistryService


class CircularSchemaReferenceError(Exception):
    """Raised when a circular reference is detected in schema resolution."""
    pass


class SchemaResolutionError(Exception):
    """Raised when schema resolution fails."""
    pass


@dataclass
class SchemaDependency:
    """A resolved schema dependency."""
    schema_id: str
    version: str
    sha256: str


@dataclass
class ResolvedSchemaBundle:
    """
    A fully resolved, self-contained schema bundle.
    
    Per ADR-031:
    - No unresolved $ref in bundle_json
    - All $ref: "schema:<id>" replaced with "#/$defs/<id>"
    - bundle_sha256 computed for auditability
    """
    root_schema_id: str
    root_schema_version: str
    bundle_json: dict
    bundle_sha256: str
    dependencies: List[SchemaDependency] = field(default_factory=list)


class SchemaResolver:
    """
    Resolves schema references and produces self-contained bundles.
    
    Per ADR-031:
    - Resolves $ref: "schema:<id>" from DB registry
    - Detects and rejects circular references
    - Only accepted schemas may be used
    - Produces bundles with $defs containing all dependencies
    """
    
    # Pattern to match schema references: $ref: "schema:SomeSchemaId"
    SCHEMA_REF_PATTERN = re.compile(r'^schema:([A-Za-z0-9_]+)$')
    
    def __init__(self, registry: SchemaRegistryService):
        self.registry = registry
    
    async def resolve_bundle(
        self,
        root_schema_id: str,
        version: Optional[str] = None,
    ) -> ResolvedSchemaBundle:
        """
        Resolve a schema and all its dependencies into a self-contained bundle.
        
        Args:
            root_schema_id: The root schema to resolve
            version: Optional specific version (default: latest accepted)
            
        Returns:
            ResolvedSchemaBundle with all refs inlined
            
        Raises:
            SchemaResolutionError: If root schema not found
            CircularSchemaReferenceError: If circular ref detected
        """
        # Load root schema
        root_artifact = await self.registry.get_by_id(root_schema_id, version)
        
        if not root_artifact:
            raise SchemaResolutionError(
                f"Schema '{root_schema_id}' not found"
                + (f" (version {version})" if version else " (no accepted version)")
            )
        
        if root_artifact.status != "accepted":
            raise SchemaResolutionError(
                f"Schema '{root_schema_id}' version '{root_artifact.version}' "
                f"has status '{root_artifact.status}', expected 'accepted'"
            )
        
        # Track resolved schemas and dependencies
        resolved: Dict[str, dict] = {}
        dependencies: List[SchemaDependency] = []
        
        # Resolve all references recursively
        await self._resolve_refs(
            schema=root_artifact.schema_json,
            resolved=resolved,
            dependencies=dependencies,
            visited=set(),
            path=[root_schema_id],
        )
        
        # Build the bundle with $defs
        bundle_json = self._inline_to_defs(
            root=copy.deepcopy(root_artifact.schema_json),
            resolved=resolved,
        )
        
        # Compute bundle hash
        bundle_sha256 = self._compute_bundle_hash(bundle_json)
        
        return ResolvedSchemaBundle(
            root_schema_id=root_schema_id,
            root_schema_version=root_artifact.version,
            bundle_json=bundle_json,
            bundle_sha256=bundle_sha256,
            dependencies=dependencies,
        )
    
    async def _resolve_refs(
        self,
        schema: dict,
        resolved: Dict[str, dict],
        dependencies: List[SchemaDependency],
        visited: Set[str],
        path: List[str],
    ) -> None:
        """
        Recursively resolve all schema references.
        
        Args:
            schema: Current schema to scan
            resolved: Dict of schema_id -> schema_json (accumulator)
            dependencies: List of dependencies (accumulator)
            visited: Set of schema_ids currently in resolution path (cycle detection)
            path: Current resolution path for error messages
        """
        refs = self._find_schema_refs(schema)
        
        for ref_id in refs:
            # Check for cycle
            if ref_id in visited:
                cycle_path = " -> ".join(path + [ref_id])
                raise CircularSchemaReferenceError(
                    f"Circular schema reference detected: {cycle_path}"
                )
            
            # Skip if already resolved
            if ref_id in resolved:
                continue
            
            # Load referenced schema
            artifact = await self.registry.get_accepted(ref_id)
            
            if not artifact:
                raise SchemaResolutionError(
                    f"Referenced schema '{ref_id}' not found or not accepted. "
                    f"Resolution path: {' -> '.join(path)}"
                )
            
            # Track dependency
            dependencies.append(SchemaDependency(
                schema_id=ref_id,
                version=artifact.version,
                sha256=artifact.sha256,
            ))
            
            # Store resolved schema
            resolved[ref_id] = artifact.schema_json
            
            # Recursively resolve refs in this schema
            await self._resolve_refs(
                schema=artifact.schema_json,
                resolved=resolved,
                dependencies=dependencies,
                visited=visited | {ref_id},
                path=path + [ref_id],
            )
    
    def _find_schema_refs(self, schema: dict) -> List[str]:
        """
        Find all schema references in a schema.
        
        Looks for $ref values matching "schema:<id>".
        
        Args:
            schema: Schema dict to scan
            
        Returns:
            List of schema IDs referenced
        """
        refs = []
        self._walk_for_refs(schema, refs)
        return refs
    
    def _walk_for_refs(self, obj, refs: List[str]) -> None:
        """Recursively walk schema looking for $ref."""
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_value = obj["$ref"]
                match = self.SCHEMA_REF_PATTERN.match(ref_value)
                if match:
                    refs.append(match.group(1))
            
            for value in obj.values():
                self._walk_for_refs(value, refs)
        
        elif isinstance(obj, list):
            for item in obj:
                self._walk_for_refs(item, refs)
    
    def _inline_to_defs(
        self,
        root: dict,
        resolved: Dict[str, dict],
    ) -> dict:
        """
        Build $defs section and rewrite $ref targets.
        
        Args:
            root: Root schema (will be modified)
            resolved: Dict of schema_id -> schema_json
            
        Returns:
            Modified root with $defs and rewritten refs
        """
        if not resolved:
            return root
        
        # Create $defs section
        defs = {}
        for schema_id, schema_json in resolved.items():
            # Deep copy and rewrite any nested refs in the def
            def_schema = copy.deepcopy(schema_json)
            self._rewrite_refs(def_schema)
            defs[schema_id] = def_schema
        
        # Add $defs to root
        root["$defs"] = defs
        
        # Rewrite refs in root
        self._rewrite_refs(root)
        
        return root
    
    def _rewrite_refs(self, obj) -> None:
        """
        Rewrite $ref: "schema:<id>" to "#/$defs/<id>".
        
        Modifies obj in place.
        """
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_value = obj["$ref"]
                match = self.SCHEMA_REF_PATTERN.match(ref_value)
                if match:
                    schema_id = match.group(1)
                    obj["$ref"] = f"#/$defs/{schema_id}"
            
            for value in obj.values():
                self._rewrite_refs(value)
        
        elif isinstance(obj, list):
            for item in obj:
                self._rewrite_refs(item)
    
    @staticmethod
    def _compute_bundle_hash(bundle_json: dict) -> str:
        """Compute SHA256 hash of bundle JSON."""
        canonical = json.dumps(bundle_json, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()