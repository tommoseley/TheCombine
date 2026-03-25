"""Tests for TA component schema `owns` field (WS-EVAL-002).

Verifies the TA output schema accepts the optional `owns` field
on component objects.
"""

import json
from pathlib import Path

import pytest

try:
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SCHEMA_PATH = Path(__file__).parent.parent.parent / (
    "combine-config/document_types/technical_architecture/"
    "releases/1.0.0/schemas/output.schema.json"
)


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _minimal_ta(**component_overrides):
    """Build a minimal valid TA document."""
    comp = {"name": "Order Engine", "purpose": "Execute orders"}
    comp.update(component_overrides)
    return {
        "architecture_summary": {
            "title": "Test",
            "style": "Layered",
            "key_decisions": ["Python"],
        },
        "components": [comp],
    }


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestTASchemaOwns:

    def test_schema_accepts_owns_field(self):
        """Criterion 1: component with owns passes validation."""
        schema = _load_schema()
        doc = _minimal_ta(owns=["src/trading/", "src/orders/"])
        validate(instance=doc, schema=schema)

    def test_schema_accepts_component_without_owns(self):
        """Criterion 2: component without owns still passes validation."""
        schema = _load_schema()
        doc = _minimal_ta()
        validate(instance=doc, schema=schema)

    def test_owns_must_be_array_of_strings(self):
        """owns field rejects non-string items."""
        schema = _load_schema()
        doc = _minimal_ta(owns=[123, True])
        with pytest.raises(ValidationError):
            validate(instance=doc, schema=schema)


class TestTAPromptOwnership:
    """Criterion 3: TA prompt v1.2.0 contains ownership instruction."""

    def test_prompt_contains_ownership_paths_instruction(self):
        prompt_path = Path(__file__).parent.parent.parent / (
            "combine-config/prompts/tasks/technical_architecture/"
            "releases/1.2.0/task.prompt.txt"
        )
        content = prompt_path.read_text()
        assert "OWNERSHIP PATHS" in content
        assert "owns" in content

    def test_prompt_self_check_includes_ownership(self):
        prompt_path = Path(__file__).parent.parent.parent / (
            "combine-config/prompts/tasks/technical_architecture/"
            "releases/1.2.0/task.prompt.txt"
        )
        content = prompt_path.read_text()
        assert "exactly one component" in content.lower()
