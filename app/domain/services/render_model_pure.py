"""
Pure data transformation functions extracted from RenderModelBuilder.

These functions contain NO I/O, NO database access, NO logging.
They are deterministic, testable transformations of in-memory data.

Extracted as part of WS-CRAP-005: Testability Refactoring.
"""

import hashlib
import json
from typing import List, Dict, Optional, Any


# ---------------------------------------------------------------------------
# resolve_pointer  (was RenderModelBuilder._resolve_pointer, CC 9)
# ---------------------------------------------------------------------------

def resolve_pointer(data: Dict[str, Any], pointer: str) -> Any:
    """
    Resolve a JSON pointer against data.

    Args:
        data: Data object to resolve against
        pointer: JSON pointer (e.g., "/epics", "/open_questions")

    Returns:
        Resolved value or None if not found
    """
    if not pointer or pointer == "/":
        return data

    parts = pointer.lstrip("/").split("/")

    current = data
    for part in parts:
        if not part:
            continue

        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                idx = int(part)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None

        if current is None:
            return None

    return current


# ---------------------------------------------------------------------------
# compute_schema_bundle_hash  (was part of _compute_schema_bundle_sha256, CC 11)
# ---------------------------------------------------------------------------

def compute_schema_bundle_hash(bundle: Dict[str, Any]) -> str:
    """
    Compute SHA256 hash of a pre-assembled schema bundle.

    The bundle is serialized with sorted keys and compact separators
    for deterministic hashing.

    Args:
        bundle: Schema bundle dict (e.g. {"schemas": {...}})

    Returns:
        Hash string in format "sha256:<hex>"
    """
    bundle_json = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"


def collect_component_ids_from_sections(
    sections: List[Dict[str, Any]],
) -> List[str]:
    """
    Collect unique component IDs from docdef sections, preserving order.

    Args:
        sections: List of section config dicts with optional "component_id"

    Returns:
        Ordered list of unique component IDs
    """
    seen: set[str] = set()
    result: list[str] = []
    for section in sections:
        comp_id = section.get("component_id")
        if comp_id and comp_id not in seen:
            seen.add(comp_id)
            result.append(comp_id)
    return result


# ---------------------------------------------------------------------------
# process_nested_list_shape  (was _process_nested_list_shape, CC 10)
# ---------------------------------------------------------------------------

def flatten_nested_list(
    section_id: str,
    source_pointer: str,
    repeat_over_pointer: str,
    context_mapping: Dict[str, str],
    document_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Flatten a nested list shape into a list of block descriptors.

    Each block descriptor is a dict with:
      - key: str
      - data: dict
      - context: dict | None

    Args:
        section_id: Section identifier for key generation
        source_pointer: Pointer to items within each parent
        repeat_over_pointer: Pointer to parent list in document_data
        context_mapping: Dict of {context_key: pointer} (relative to parent)
        document_data: Full document data

    Returns:
        List of block descriptor dicts
    """
    parents = resolve_pointer(document_data, repeat_over_pointer)
    if not parents or not isinstance(parents, list):
        return []

    blocks = []
    for parent_idx, parent in enumerate(parents):
        if not isinstance(parent, dict):
            continue

        items = resolve_pointer(parent, source_pointer)
        if not items or not isinstance(items, list):
            continue

        context = build_context(parent, context_mapping)

        for item_idx, item in enumerate(items):
            item_data = item if isinstance(item, dict) else {"value": item}
            blocks.append({
                "key": f"{section_id}:{parent_idx}:{item_idx}",
                "data": item_data,
                "context": context,
            })

    return blocks


# ---------------------------------------------------------------------------
# process_container_with_repeat  (was _process_container_with_repeat, CC 10)
# ---------------------------------------------------------------------------

def process_container_repeat(
    section_id: str,
    source_pointer: str,
    repeat_over_pointer: str,
    context_mapping: Dict[str, str],
    derived_fields: List[Dict[str, Any]],
    exclude_fields: List[str],
    detail_ref_template: Optional[Dict[str, Any]],
    derivation_functions: Dict[str, Any],
    document_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Process a container shape with repeat_over into block descriptors.

    Each block descriptor is a dict with:
      - key: str
      - data: dict
      - context: dict | None

    Args:
        section_id: Section identifier for key generation
        source_pointer: Pointer to items within each parent ("/" means parent-as-data)
        repeat_over_pointer: Pointer to parent list in document_data
        context_mapping: Dict of {context_key: pointer} (relative to parent)
        derived_fields: List of derived field specs
        exclude_fields: Fields to exclude when using parent-as-data
        detail_ref_template: Optional detail ref template
        derivation_functions: Registry of derivation functions
        document_data: Full document data

    Returns:
        List of block descriptor dicts
    """
    parents = resolve_pointer(document_data, repeat_over_pointer)
    if not parents or not isinstance(parents, list):
        return []

    blocks = []
    for parent_idx, parent in enumerate(parents):
        if not isinstance(parent, dict):
            continue

        if source_pointer in ("/", ""):
            block_data = build_parent_as_data(
                parent=parent,
                derived_fields=derived_fields,
                exclude_fields=exclude_fields,
                detail_ref_template=detail_ref_template,
                derivation_functions=derivation_functions,
            )
        else:
            parent_items = resolve_pointer(parent, source_pointer)
            if not parent_items or not isinstance(parent_items, list):
                continue

            processed_items = []
            for item in parent_items:
                item_data = item if isinstance(item, dict) else {"value": item}
                processed_items.append(item_data)
            block_data = {"items": processed_items}

        context = build_context(parent, context_mapping)

        blocks.append({
            "key": f"{section_id}:container:{parent_idx}",
            "data": block_data,
            "context": context,
        })

    return blocks


# ---------------------------------------------------------------------------
# build_parent_as_data  (was _build_parent_as_data, CC 9)
# ---------------------------------------------------------------------------

def build_parent_as_data(
    parent: Dict[str, Any],
    derived_fields: List[Dict[str, Any]],
    exclude_fields: List[str],
    detail_ref_template: Optional[Dict[str, Any]],
    derivation_functions: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build block data from a parent object, applying exclusions,
    derived fields, and detail_ref_template.

    Args:
        parent: Parent data dict
        derived_fields: List of derived field specs
            Each: {"field": str, "function": str, "source": str}
        exclude_fields: Fields to exclude from parent copy
        detail_ref_template: Optional detail ref template
        derivation_functions: Registry of derivation functions {name: callable}

    Returns:
        Assembled block data dict
    """
    block_data = {k: v for k, v in parent.items() if k not in exclude_fields}

    for df in derived_fields:
        field_name = df.get("field")
        func_name = df.get("function")
        source = df.get("source", "")

        if func_name in derivation_functions:
            if source in ("/", ""):
                source_data = parent
            else:
                source_data = resolve_pointer(parent, source)
                if source_data is None:
                    source_data = []
            block_data[field_name] = derivation_functions[func_name](source_data)

    if detail_ref_template:
        block_data["detail_ref"] = {
            "document_type": detail_ref_template.get("document_type", ""),
            "params": {
                k: resolve_pointer(parent, v)
                for k, v in detail_ref_template.get("params", {}).items()
            },
        }

    return block_data


# ---------------------------------------------------------------------------
# process_derived_section_pure  (was part of _process_derived_section, CC 12)
# ---------------------------------------------------------------------------

def apply_derivation(
    source_pointer: str,
    func_name: str,
    omit_when_empty: bool,
    derivation_functions: Dict[str, Any],
    document_data: Dict[str, Any],
) -> Optional[Any]:
    """
    Apply a derivation function to source data resolved from document_data.

    Returns the derived value, or None if the derivation should be omitted
    (because the source is empty and omit_when_empty is True, or the
    function name is not found).

    Args:
        source_pointer: JSON pointer to source data in document_data
        func_name: Name of derivation function
        omit_when_empty: If True, return None when source is empty
        derivation_functions: Registry of derivation functions
        document_data: Full document data

    Returns:
        Derived value, or None if should be omitted
    """
    if func_name not in derivation_functions:
        return None

    # Resolve source data - "/" means pass entire document
    if source_pointer in ("/", ""):
        source_data = document_data
    else:
        source_data = resolve_pointer(document_data, source_pointer)
        if source_data is None:
            source_data = []

    # Omit if source is empty and omit_when_empty is set
    if omit_when_empty:
        if source_data is None:
            return None
        if isinstance(source_data, list) and len(source_data) == 0:
            return None
        if isinstance(source_data, dict) and not source_data:
            return None

    derive_fn = derivation_functions[func_name]
    return derive_fn(source_data)


# ---------------------------------------------------------------------------
# build_context  (helper used by multiple shapes)
# ---------------------------------------------------------------------------

def build_context(
    parent: Dict[str, Any],
    context_mapping: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """
    Build context dict by resolving pointers relative to parent.

    Args:
        parent: Parent object to resolve against
        context_mapping: Dict of {context_key: pointer}

    Returns:
        Context dict or None if no mapping or all values are None
    """
    if not context_mapping:
        return None

    context = {}
    for key, pointer in context_mapping.items():
        value = resolve_pointer(parent, pointer)
        if value is not None:
            context[key] = value

    return context if context else None


# ---------------------------------------------------------------------------
# build  dispatch helpers (was part of build(), CC 10)
# ---------------------------------------------------------------------------

def resolve_docdef_id(document_def_id: str) -> str:
    """
    Resolve a short document def name to a full docdef ID.

    Args:
        document_def_id: Short name (e.g., "EpicDetailView") or
            full ID (e.g., "docdef:EpicDetailView:1.0.0")

    Returns:
        Full docdef ID string
    """
    if not document_def_id.startswith("docdef:"):
        return f"docdef:{document_def_id}:1.0.0"
    return document_def_id


def extract_document_type(document_def_id: str) -> str:
    """
    Extract the document type name from a full docdef ID.

    Args:
        document_def_id: Full docdef ID (e.g., "docdef:EpicDetailView:1.0.0")

    Returns:
        Document type string (e.g., "EpicDetailView")
    """
    parts = document_def_id.split(":")
    return parts[1] if len(parts) >= 2 else document_def_id


def sort_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort section configs by their 'order' field.

    Args:
        sections: List of section config dicts

    Returns:
        New sorted list
    """
    return sorted(sections, key=lambda s: s.get("order", 0))
