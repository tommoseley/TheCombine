"""Tier-1 tests for portable governance conversion (ADR-060).

Pure unit tests — no DB, no LLM.
Tests that Combine-internal references are stripped or rewritten
when governance is rendered in portable mode.
"""

from app.domain.services.governance_portable import (
    convert_policies_to_portable,
    _convert_policy_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _native_policy(title="POL-TEST-001", content="Some policy content."):
    return {"title": title, "content": content}


# ---------------------------------------------------------------------------
# Operational reference stripping
# ---------------------------------------------------------------------------

class TestOperationalReferenceStripping:
    def test_strips_ops_scripts_path(self):
        content = "Run `ops/scripts/tier0.sh --ws --scope app/` to verify."
        result = _convert_policy_content(content)
        assert "ops/scripts/" not in result

    def test_strips_seed_prompts_path(self):
        content = "Prompts live in `seed/prompts/` and are versioned."
        result = _convert_policy_content(content)
        assert "seed/prompts/" not in result

    def test_strips_seed_schemas_path(self):
        content = "Schemas in `seed/schemas/` are authoritative."
        result = _convert_policy_content(content)
        assert "seed/schemas/" not in result

    def test_strips_combine_config_path(self):
        content = "See `combine-config/governance/tier0/pgc_secrets_clause.v1.txt` for details."
        result = _convert_policy_content(content)
        assert "combine-config/" not in result

    def test_replaces_tier0_invocation(self):
        content = "Run ops/scripts/tier0.sh --ws --scope app/ tests/"
        result = _convert_policy_content(content)
        assert "ops/scripts" not in result
        assert "verification" in result.lower() or "complete" in result.lower()

    def test_preserves_non_operational_content(self):
        content = "All work statements MUST reference governing policies."
        result = _convert_policy_content(content)
        assert "All work statements MUST reference governing policies." in result


# ---------------------------------------------------------------------------
# Source attribution generalization
# ---------------------------------------------------------------------------

class TestSourceAttribution:
    def test_generalizes_claude_md_source(self):
        content = '*Source: CLAUDE.md "Execution Model (Concrete)"*'
        result = _convert_policy_content(content)
        assert "CLAUDE.md" not in result
        assert "Project governance policy" in result

    def test_generalizes_established_source(self):
        content = '*Source: Established API conventions, CLAUDE.md*'
        result = _convert_policy_content(content)
        assert "CLAUDE.md" not in result


# ---------------------------------------------------------------------------
# convert_policies_to_portable
# ---------------------------------------------------------------------------

class TestConvertPoliciesToPortable:
    def test_preserves_titles(self):
        policies = [
            _native_policy("POL-WS-001: Standard Work Statements", "content here"),
            _native_policy("POL-QA-001: Testing", "test content"),
        ]
        result = convert_policies_to_portable(policies)
        assert len(result) == 2
        assert result[0]["title"] == "POL-WS-001: Standard Work Statements"
        assert result[1]["title"] == "POL-QA-001: Testing"

    def test_content_is_converted(self):
        policies = [
            _native_policy(content="Run `ops/scripts/tier0.sh` to verify."),
        ]
        result = convert_policies_to_portable(policies)
        assert "ops/scripts/" not in result[0]["content"]

    def test_returns_new_list(self):
        """Original policies are not mutated."""
        policies = [_native_policy(content="Run `ops/scripts/tier0.sh` for testing.")]
        original_content = policies[0]["content"]
        convert_policies_to_portable(policies)
        assert policies[0]["content"] == original_content

    def test_empty_list(self):
        assert convert_policies_to_portable([]) == []


# ---------------------------------------------------------------------------
# Full policy conversion (realistic content)
# ---------------------------------------------------------------------------

class TestRealisticPolicyConversion:
    def test_pol_ws_001_tier0_section(self):
        """The Tier 0 section in POL-WS-001 should be replaced with declarative version."""
        content = (
            "### Tier 0 Verification in WS Mode\n\n"
            "When executing a Work Statement, Tier 0 **MUST** be invoked in WS mode:\n\n"
            "```bash\n"
            "ops/scripts/tier0.sh --ws --scope <paths>\n"
            "```\n\n"
            "If Tier 0 is run without `--scope`, it will **FAIL by design**.\n\n"
            "### AI-Specific Rules"
        )
        result = _convert_policy_content(content)
        assert "tier0.sh" not in result
        assert "Verification" in result
        assert "AI-Specific Rules" in result

    def test_mixed_content_preserves_rules(self):
        """Non-operational governance rules survive conversion."""
        content = (
            "## 5. Prohibited Actions\n\n"
            "A Work Statement **MUST** explicitly list known prohibited actions.\n\n"
            "All prohibitions defined in governing ADRs are implicitly in force.\n\n"
            "## 6. Execution Rules\n\n"
            "Run ops/scripts/tier0.sh --ws --scope app/ to verify."
        )
        result = _convert_policy_content(content)
        assert "explicitly list known prohibited actions" in result
        assert "implicitly in force" in result
        assert "ops/scripts/" not in result
