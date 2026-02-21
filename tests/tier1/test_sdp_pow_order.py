"""Tests for software_product_development POW node order (WS-SDP-001).

Verifies ADR-053 canonical order: Discovery -> IPP -> IPF -> TA -> WPs.

C1: IPP precedes TA in graph definition
C2: IPF precedes TA in graph definition
C3: Regression guard — TA does NOT precede IPF

Both the seed file and the combine-config runtime file are checked.
"""

import json
import os

import pytest


def _load_pow_seed() -> dict:
    """Load the seed copy of the POW definition."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "seed", "workflows",
        "software_product_development.v1.json",
    )
    with open(os.path.normpath(path)) as f:
        return json.load(f)


def _load_pow_runtime() -> dict:
    """Load the combine-config runtime copy of the POW definition."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "combine-config", "workflows",
        "software_product_development", "releases", "1.0.0", "definition.json",
    )
    with open(os.path.normpath(path)) as f:
        return json.load(f)


def _step_index(steps: list, produces: str) -> int:
    """Find the index of a step by its 'produces' field."""
    for i, step in enumerate(steps):
        if step.get("produces") == produces:
            return i
    raise ValueError(f"No step produces '{produces}'")


class TestADR053CanonicalOrder:
    """Verify POW step order matches ADR-053 in both seed and runtime files."""

    @pytest.mark.parametrize("loader", [_load_pow_seed, _load_pow_runtime],
                             ids=["seed", "combine-config"])
    def test_ipp_precedes_ta(self, loader):
        """C1: implementation_plan_primary precedes technical_architecture."""
        steps = loader()["steps"]
        ipp_idx = _step_index(steps, "implementation_plan_primary")
        ta_idx = _step_index(steps, "technical_architecture")
        assert ipp_idx < ta_idx, (
            f"IPP (index {ipp_idx}) must precede TA (index {ta_idx})"
        )

    @pytest.mark.parametrize("loader", [_load_pow_seed, _load_pow_runtime],
                             ids=["seed", "combine-config"])
    def test_ipf_precedes_ta(self, loader):
        """C2: implementation_plan precedes technical_architecture."""
        steps = loader()["steps"]
        ipf_idx = _step_index(steps, "implementation_plan")
        ta_idx = _step_index(steps, "technical_architecture")
        assert ipf_idx < ta_idx, (
            f"IPF (index {ipf_idx}) must precede TA (index {ta_idx})"
        )

    @pytest.mark.parametrize("loader", [_load_pow_seed, _load_pow_runtime],
                             ids=["seed", "combine-config"])
    def test_ta_does_not_precede_ipf(self, loader):
        """C3: Regression guard — TA must NOT precede IPF."""
        steps = loader()["steps"]
        ta_idx = _step_index(steps, "technical_architecture")
        ipf_idx = _step_index(steps, "implementation_plan")
        assert ta_idx > ipf_idx, (
            f"TA (index {ta_idx}) must NOT precede IPF (index {ipf_idx})"
        )
