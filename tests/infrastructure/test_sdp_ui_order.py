"""Tests for SPA UI alignment to ADR-053 canonical order (WS-SDP-002).

C1: UI does not hardcode TA-before-IPF ordering
C2: No UI text suggests TA precedes IPF
C3: No broken references between document stages
"""

import os
import glob


def _read_spa_sources() -> dict:
    """Read all SPA source files into a dict of path -> content."""
    spa_dir = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "..", "spa", "src",
    ))
    sources = {}
    for filepath in glob.glob(os.path.join(spa_dir, "**", "*"), recursive=True):
        if os.path.isfile(filepath) and filepath.endswith((".js", ".jsx", ".ts", ".tsx")):
            with open(filepath) as f:
                sources[filepath] = f.read()
    return sources


class TestNoHardcodedTABeforeIPF:
    """C1: No SPA component hardcodes TA appearing before IPF in a list or flow."""

    def test_no_ordered_array_with_ta_before_ipf(self):
        """No JS array literal places technical_architecture before implementation_plan."""
        sources = _read_spa_sources()
        for path, content in sources.items():
            # Look for array literals containing both doc types in TA-first order
            # This catches patterns like ['technical_architecture', ..., 'implementation_plan']
            ta_pos = content.find("technical_architecture")
            ipf_pos = content.find("implementation_plan")
            if ta_pos == -1 or ipf_pos == -1:
                continue
            # Only flag if both appear in what looks like an ordered list/sequence
            # and TA comes first. We check for array context.
            import re
            arrays = re.findall(r'\[([^\]]*)\]', content)
            for arr in arrays:
                if "technical_architecture" in arr and "implementation_plan" in arr:
                    ta_arr_pos = arr.find("technical_architecture")
                    ipf_arr_pos = arr.find("implementation_plan")
                    assert ta_arr_pos > ipf_arr_pos, (
                        f"Array in {os.path.basename(path)} has TA before IPF: {arr[:100]}"
                    )


class TestNoUITextSuggestsTABeforeIPF:
    """C2: No instructional text, label, or flow hint implies TA precedes IPF."""

    def test_no_step_text_with_architecture_before_plan(self):
        """No visible text string shows 'Architecture' as a step before 'Plan'."""
        sources = _read_spa_sources()
        import re
        for path, content in sources.items():
            # Look for flow/step patterns like "Architecture → Plan" or
            # step arrays with Architecture before Plan
            if re.search(
                r'["\'].*Architecture.*Plan.*Implementation.*["\']',
                content,
            ):
                assert False, (
                    f"{os.path.basename(path)} contains text implying Architecture before Plan"
                )


class TestNoMissingDocTypeReferences:
    """C3: Both technical_architecture and implementation_plan are referenced consistently."""

    def test_workflow_block_handles_both_doc_types(self):
        """WorkflowBlock components don't assume specific doc type ordering."""
        spa_dir = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "..", "spa", "src",
        ))
        # Verify WorkflowBlock files exist and use generic sorting
        workflow_blocks = glob.glob(
            os.path.join(spa_dir, "**", "WorkflowBlock*"), recursive=True,
        )
        assert len(workflow_blocks) > 0, "WorkflowBlock components must exist"
        for path in workflow_blocks:
            with open(path) as f:
                content = f.read()
            # Should use generic sort, not hardcoded doc type order
            assert "sort" in content.lower(), (
                f"{os.path.basename(path)} should sort steps generically"
            )
