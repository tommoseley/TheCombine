"""Tests for IPF input alignment with ADR-053 order (WS-SDP-003).

Verifies that the implementation_plan DCW, task prompt, schema, and package
are aligned with ADR-053: IPF runs BEFORE TA, so TA cannot be a required input.

C1: DCW requires_inputs does NOT include technical_architecture
C2: DCW requires_inputs includes primary_implementation_plan
C3: Package required_inputs matches DCW requires_inputs
C4: Task prompt does NOT reference Technical Architecture as a required input
C5: Schema governance_pins.ta_version_id is NOT required
"""

import json
from pathlib import Path

import yaml

COMBINE_CONFIG = Path("combine-config")
IPF_RELEASE = COMBINE_CONFIG / "document_types" / "implementation_plan" / "releases" / "1.0.0"
IPF_DCW = COMBINE_CONFIG / "workflows" / "implementation_plan" / "releases" / "1.0.0" / "definition.json"


def _load_dcw() -> dict:
    with open(IPF_DCW) as f:
        return json.load(f)


def _load_package() -> dict:
    with open(IPF_RELEASE / "package.yaml") as f:
        return yaml.safe_load(f)


def _load_schema() -> dict:
    with open(IPF_RELEASE / "schemas" / "output.schema.json") as f:
        return json.load(f)


def _load_task_prompt() -> str:
    with open(IPF_RELEASE / "prompts" / "task.prompt.txt") as f:
        return f.read()


class TestIPFInputAlignment:
    """Verify IPF inputs align with ADR-053 (Planning Before Architecture)."""

    def test_c1_dcw_no_ta_in_requires_inputs(self):
        """C1: DCW requires_inputs does NOT include technical_architecture."""
        dcw = _load_dcw()
        requires = dcw.get("requires_inputs", [])
        assert "technical_architecture" not in requires, (
            f"IPF DCW still lists 'technical_architecture' in requires_inputs. "
            f"ADR-053 says IPF runs before TA. Current: {requires}"
        )

    def test_c2_dcw_requires_ipp(self):
        """C2: DCW requires_inputs includes primary_implementation_plan."""
        dcw = _load_dcw()
        requires = dcw.get("requires_inputs", [])
        assert "primary_implementation_plan" in requires, (
            f"IPF DCW missing 'primary_implementation_plan' in requires_inputs. "
            f"Current: {requires}"
        )

    def test_c3_package_matches_dcw(self):
        """C3: Package required_inputs matches DCW requires_inputs."""
        dcw = _load_dcw()
        pkg = _load_package()
        dcw_requires = set(dcw.get("requires_inputs", []))
        pkg_requires = set(pkg.get("required_inputs", []))
        assert dcw_requires == pkg_requires, (
            f"IPF package.yaml required_inputs does not match DCW requires_inputs. "
            f"DCW: {sorted(dcw_requires)}, Package: {sorted(pkg_requires)}"
        )

    def test_c4_prompt_no_ta_required_input(self):
        """C4: Task prompt does NOT reference Technical Architecture as a required input."""
        prompt = _load_task_prompt()
        # Look for the "Inputs Provided" section and check it doesn't list TA
        # The prompt should not say the LLM "will receive" TA as an input
        lines = prompt.split("\n")
        in_inputs_section = False
        ta_as_input = False
        for line in lines:
            if "## Inputs Provided" in line or "## Inputs" in line:
                in_inputs_section = True
                continue
            if in_inputs_section and line.startswith("## "):
                break  # Exited the inputs section
            if in_inputs_section and "Technical Architecture" in line and ("receive" in prompt[:prompt.index(line) + len(line)] or "input document" in line.lower() or line.strip().startswith("*")):
                ta_as_input = True
        assert not ta_as_input, (
            "IPF task prompt still lists Technical Architecture as a required input document. "
            "ADR-053 says IPF runs before TA."
        )

    def test_c5_schema_ta_version_not_required(self):
        """C5: Schema governance_pins.ta_version_id is NOT in required array."""
        schema = _load_schema()
        wp_def = schema.get("definitions", {}).get("work_package", {})
        gov_pins = wp_def.get("properties", {}).get("governance_pins", {})
        required = gov_pins.get("required", [])
        assert "ta_version_id" not in required, (
            f"IPF schema still requires governance_pins.ta_version_id. "
            f"TA is not available when IPF runs. Required: {required}"
        )
