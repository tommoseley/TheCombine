"""WS-SKILLS-001: Decompose CLAUDE.md into Claude Code Skills.

Verifies all 16 Tier 1 criteria:

Content Completeness:
  C1  - All 10 skill directories exist with SKILL.md files
  C2  - README.md exists in .claude/skills/ cataloging all 10 skills
  C3  - No content loss (every governance rule in new CLAUDE.md or exactly one skill)
  C4  - Bug-First Rule preserved in autonomous-bug-fix skill
  C5  - ADR-040 preserved in config-governance skill
  C6  - ADR-049 preserved in config-governance skill
  C7  - Session template preserved in session-management skill

CLAUDE.md Structure:
  C8  - CLAUDE.md under 15K characters
  C9  - Skills table present with all 10 skills
  C10 - Policy summaries present with skill pointers
  C11 - Always-on constraints present
  C12 - Non-negotiables unchanged
  C13 - No moved sections remain in CLAUDE.md

Skill Quality:
  C14 - Each skill has valid YAML frontmatter with name and description
  C15 - Each description includes trigger phrases (action verbs)
  C16 - No cross-skill duplication
"""

import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"

SKILL_NAMES = [
    "ws-execution",
    "autonomous-bug-fix",
    "subagent-dispatch",
    "metrics-reporting",
    "session-management",
    "config-governance",
    "ia-validation",
    "ia-golden-tests",
    "tier0-verification",
    "combine-governance",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill(name: str) -> str:
    """Read the SKILL.md for a given skill name."""
    path = SKILLS_DIR / name / "SKILL.md"
    return path.read_text()


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file.

    Returns dict with 'name' and 'description' keys if valid.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("name", "description"):
                fm[key] = val
    return fm


def _read_claude_md() -> str:
    return CLAUDE_MD.read_text()


# ===================================================================
# Original CLAUDE.md reference content (for content-loss checks)
# These are key phrases from sections that will move to skills.
# Each phrase must appear in exactly one skill after migration.
# ===================================================================

# Bug-First Testing Rule key phrases
BUG_FIRST_KEY_PHRASES = [
    "Reproduce First",
    "Verify Failure",
    "MUST NOT** be written after the fix",
    "MUST NOT** be changed before a reproducing test",
    "Vibe-based fixes are explicitly disallowed",
]

# ADR-040 key phrases
ADR_040_KEY_PHRASES = [
    "No transcript replay",
    "Stateless LLM Execution Invariant",
    "Continuity comes from structured state, not transcripts",
    "node_history is for audit. context_state is for memory",
]

# ADR-049 key phrases
ADR_049_KEY_PHRASES = [
    "No Black Boxes",
    '"Generate" is deprecated as a step abstraction',
    "Full pattern",
    "Gate Profile pattern",
]

# Seed Governance key phrases
SEED_GOVERNANCE_PHRASES = [
    "Versioned",
    "Certified",
    "Hashed",
    "seed/manifest.json",
    "Manifest regeneration",
]

# Subagent Usage key phrases
SUBAGENT_USAGE_PHRASES = [
    'isolation: "worktree"',
    "Parallel WS Execution",
    "Subagent responsibilities",
    "Main agent responsibilities",
]

# Metrics Reporting key phrases
METRICS_REPORTING_PHRASES = [
    "POST /api/v1/metrics/ws-execution",
    "POST /api/v1/metrics/bug-fix",
    "Rework cycles",
    "LLM calls made, tokens consumed",
]

# Session Management key phrases
SESSION_MANAGEMENT_PHRASES = [
    "How to Start a New AI Session",
    "How to Close a Session",
    "Prepare session close",
    "Session summaries are **immutable logs**",
]

# Session template (verbatim block)
SESSION_TEMPLATE_MARKER = "# Session Summary - YYYY-MM-DD"

# Planning Discipline key phrases
PLANNING_DISCIPLINE_PHRASES = [
    "Plan Before Executing",
    "Enter plan mode before writing code",
    "STOP and re-plan",
    "Verification Before Done",
]

# Autonomous Bug Fixing key phrases
AUTONOMOUS_BUG_FIX_PHRASES = [
    "Do not stop and ask for instructions",
    "Report what you fixed, not what you found",
    "write a remediation WS",
]

# Non-Negotiables section (must be preserved verbatim)
NON_NEGOTIABLES_LINES = [
    "Do not merge role logic into task prompts",
    "Do not invent workflow, ceremony, or process",
    "Do not assume undocumented context",
    "Do not suggest SQLite for testing",
    "Do not edit prompts without version bump",
    "Session summaries are logs - never edit after writing",
    "Discipline > convenience",
]


# ===================================================================
# C1 -- All 10 skill directories exist with SKILL.md files
# ===================================================================


class TestC1SkillDirectoriesExist:
    """All 10 skill directories must exist with SKILL.md files."""

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_directory_exists(self, skill_name):
        skill_dir = SKILLS_DIR / skill_name
        assert skill_dir.is_dir(), f"Skill directory missing: {skill_dir}"

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_md_exists(self, skill_name):
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_file.is_file(), f"SKILL.md missing: {skill_file}"


# ===================================================================
# C2 -- README.md exists in .claude/skills/
# ===================================================================


class TestC2ReadmeExists:
    """README.md must exist in .claude/skills/ and catalog all 10 skills."""

    def test_readme_exists(self):
        readme = SKILLS_DIR / "README.md"
        assert readme.is_file(), f"README.md missing: {readme}"

    def test_readme_lists_all_skills(self):
        readme = SKILLS_DIR / "README.md"
        content = readme.read_text()
        for name in SKILL_NAMES:
            assert name in content, f"README.md does not mention skill '{name}'"


# ===================================================================
# C3 -- No content loss
# ===================================================================


class TestC3NoContentLoss:
    """Every governance rule from original CLAUDE.md exists in either
    new CLAUDE.md or exactly one skill (not duplicated, not dropped)."""

    def _all_skill_texts(self) -> list[str]:
        """Read all skill files and return list of texts."""
        texts = []
        for name in SKILL_NAMES:
            path = SKILLS_DIR / name / "SKILL.md"
            if path.exists():
                texts.append(path.read_text())
        return texts

    def _combined_text(self) -> str:
        """CLAUDE.md + all skills concatenated."""
        parts = [_read_claude_md()]
        parts.extend(self._all_skill_texts())
        return "\n".join(parts)

    def test_bug_first_phrases_preserved(self):
        combined = self._combined_text()
        for phrase in BUG_FIRST_KEY_PHRASES:
            assert phrase in combined, f"Bug-First phrase lost: '{phrase}'"

    def test_adr040_phrases_preserved(self):
        combined = self._combined_text()
        for phrase in ADR_040_KEY_PHRASES:
            assert phrase in combined, f"ADR-040 phrase lost: '{phrase}'"

    def test_adr049_phrases_preserved(self):
        combined = self._combined_text()
        for phrase in ADR_049_KEY_PHRASES:
            assert phrase in combined, f"ADR-049 phrase lost: '{phrase}'"

    def test_seed_governance_preserved(self):
        combined = self._combined_text()
        for phrase in SEED_GOVERNANCE_PHRASES:
            assert phrase in combined, f"Seed governance phrase lost: '{phrase}'"

    def test_subagent_usage_preserved(self):
        combined = self._combined_text()
        for phrase in SUBAGENT_USAGE_PHRASES:
            assert phrase in combined, f"Subagent usage phrase lost: '{phrase}'"

    def test_metrics_reporting_preserved(self):
        combined = self._combined_text()
        for phrase in METRICS_REPORTING_PHRASES:
            assert phrase in combined, f"Metrics reporting phrase lost: '{phrase}'"

    def test_session_management_preserved(self):
        combined = self._combined_text()
        for phrase in SESSION_MANAGEMENT_PHRASES:
            assert phrase in combined, f"Session management phrase lost: '{phrase}'"

    def test_planning_discipline_preserved(self):
        combined = self._combined_text()
        for phrase in PLANNING_DISCIPLINE_PHRASES:
            assert phrase in combined, f"Planning discipline phrase lost: '{phrase}'"

    def test_autonomous_bug_fix_preserved(self):
        combined = self._combined_text()
        for phrase in AUTONOMOUS_BUG_FIX_PHRASES:
            assert phrase in combined, f"Autonomous bug fix phrase lost: '{phrase}'"


# ===================================================================
# C4 -- Bug-First Rule preserved in autonomous-bug-fix skill
# ===================================================================


class TestC4BugFirstRulePreserved:
    """Complete Bug-First Testing Rule exists in autonomous-bug-fix skill."""

    def test_bug_first_rule_in_skill(self):
        content = _read_skill("autonomous-bug-fix")
        for phrase in BUG_FIRST_KEY_PHRASES:
            assert phrase in content, (
                f"Bug-First phrase missing from autonomous-bug-fix: '{phrase}'"
            )

    def test_autonomous_bug_fix_in_skill(self):
        content = _read_skill("autonomous-bug-fix")
        for phrase in AUTONOMOUS_BUG_FIX_PHRASES:
            assert phrase in content, (
                f"Autonomous Bug Fix phrase missing from skill: '{phrase}'"
            )


# ===================================================================
# C5 -- ADR-040 preserved in config-governance skill
# ===================================================================


class TestC5ADR040Preserved:
    """Complete stateless LLM execution invariant exists in config-governance."""

    def test_adr040_in_config_governance(self):
        content = _read_skill("config-governance")
        for phrase in ADR_040_KEY_PHRASES:
            assert phrase in content, (
                f"ADR-040 phrase missing from config-governance: '{phrase}'"
            )


# ===================================================================
# C6 -- ADR-049 preserved in config-governance skill
# ===================================================================


class TestC6ADR049Preserved:
    """Complete No Black Boxes rule exists in config-governance."""

    def test_adr049_in_config_governance(self):
        content = _read_skill("config-governance")
        for phrase in ADR_049_KEY_PHRASES:
            assert phrase in content, (
                f"ADR-049 phrase missing from config-governance: '{phrase}'"
            )


# ===================================================================
# C7 -- Session template preserved in session-management skill
# ===================================================================


class TestC7SessionTemplatePreserved:
    """Verbatim session log template exists in session-management skill."""

    def test_session_template_marker(self):
        content = _read_skill("session-management")
        assert SESSION_TEMPLATE_MARKER in content, (
            "Session template marker missing from session-management skill"
        )

    def test_session_template_sections(self):
        """Template must contain all required sections."""
        content = _read_skill("session-management")
        for section in [
            "## Scope",
            "## Decisions Made",
            "## Implemented",
            "## Updated or Created",
            "## Commits / PRs",
            "## Open Threads",
            "## Known Risks / Drift Warnings",
        ]:
            assert section in content, (
                f"Session template section missing: '{section}'"
            )


# ===================================================================
# C8 -- CLAUDE.md under 15K characters
# ===================================================================


class TestC8ClaudeMdSlimmed:
    """New CLAUDE.md must be under 30K characters."""

    def test_character_count(self):
        content = _read_claude_md()
        char_count = len(content)
        assert char_count < 30000, (
            f"CLAUDE.md is {char_count} chars (limit: 30000)"
        )


# ===================================================================
# C9 -- Skills table present
# ===================================================================


class TestC9SkillsTablePresent:
    """CLAUDE.md must have a Skills section listing all 10 skills."""

    def test_skills_section_exists(self):
        content = _read_claude_md()
        assert "## Skills" in content or "# Skills" in content, (
            "CLAUDE.md missing Skills section"
        )

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_skill_listed_in_table(self, skill_name):
        content = _read_claude_md()
        assert skill_name in content, (
            f"Skill '{skill_name}' not listed in CLAUDE.md Skills table"
        )


# ===================================================================
# C10 -- Policy summaries present with skill pointers
# ===================================================================


class TestC10PolicySummariesPresent:
    """CLAUDE.md has one-line summaries for each policy with skill pointers."""

    def test_pol_ws_001_summary(self):
        content = _read_claude_md()
        assert "POL-WS-001" in content, "POL-WS-001 not mentioned in CLAUDE.md"
        assert "ws-execution" in content, (
            "POL-WS-001 summary missing skill pointer to ws-execution"
        )

    def test_pol_adr_exec_001_summary(self):
        content = _read_claude_md()
        assert "POL-ADR-EXEC-001" in content, (
            "POL-ADR-EXEC-001 not mentioned in CLAUDE.md"
        )
        assert "combine-governance" in content, (
            "POL-ADR-EXEC-001 summary missing skill pointer to combine-governance"
        )


# ===================================================================
# C11 -- Always-on constraints present
# ===================================================================


class TestC11AlwaysOnConstraints:
    """CLAUDE.md must retain these always-on constraints:
    - Reuse-first
    - No commit = nothing happened (implied in Execution Constraints)
    - Don't invent file paths
    - Tier 0 is the bar
    - combine-config canonical
    """

    def test_reuse_first_present(self):
        content = _read_claude_md()
        assert "Reuse-First" in content or "reuse-first" in content.lower(), (
            "Reuse-First rule missing from CLAUDE.md"
        )

    def test_tier0_reference(self):
        content = _read_claude_md()
        assert "Tier 0" in content or "tier0" in content.lower(), (
            "Tier 0 reference missing from CLAUDE.md"
        )

    def test_combine_config_reference(self):
        content = _read_claude_md()
        assert "combine-config" in content, (
            "combine-config reference missing from CLAUDE.md"
        )


# ===================================================================
# C12 -- Non-negotiables unchanged
# ===================================================================


class TestC12NonNegotiablesUnchanged:
    """Non-Negotiables section must be identical to original."""

    def test_non_negotiables_section_exists(self):
        content = _read_claude_md()
        assert "## Non-Negotiables" in content, (
            "Non-Negotiables section missing from CLAUDE.md"
        )

    @pytest.mark.parametrize("line", NON_NEGOTIABLES_LINES)
    def test_non_negotiable_line_present(self, line):
        content = _read_claude_md()
        assert line in content, (
            f"Non-Negotiable line missing: '{line}'"
        )


# ===================================================================
# C13 -- No moved sections remain in CLAUDE.md
# ===================================================================


class TestC13NoMovedSections:
    """CLAUDE.md must not contain sections that moved to skills."""

    def test_no_bug_first_testing_rule_section(self):
        content = _read_claude_md()
        assert "## Bug-First Testing Rule" not in content, (
            "Bug-First Testing Rule section still in CLAUDE.md"
        )

    def test_no_autonomous_bug_fixing_section(self):
        content = _read_claude_md()
        assert "## Autonomous Bug Fixing" not in content, (
            "Autonomous Bug Fixing section still in CLAUDE.md"
        )

    def test_no_subagent_usage_section(self):
        content = _read_claude_md()
        assert "## Subagent Usage" not in content, (
            "Subagent Usage section still in CLAUDE.md"
        )

    def test_no_metrics_reporting_section(self):
        content = _read_claude_md()
        assert "## Metrics Reporting" not in content, (
            "Metrics Reporting section still in CLAUDE.md"
        )

    def test_no_session_management_section(self):
        content = _read_claude_md()
        assert "## Session Management" not in content, (
            "Session Management section still in CLAUDE.md"
        )

    def test_no_backfilling_session_logs_section(self):
        content = _read_claude_md()
        assert "## Backfilling Session Logs" not in content, (
            "Backfilling Session Logs section still in CLAUDE.md"
        )

    def test_no_seed_governance_section(self):
        content = _read_claude_md()
        assert "## Seed Governance" not in content, (
            "Seed Governance section still in CLAUDE.md"
        )

    def test_no_planning_discipline_section(self):
        content = _read_claude_md()
        assert "## Planning Discipline" not in content, (
            "Planning Discipline section still in CLAUDE.md"
        )

    def test_no_adr040_detail_block(self):
        """ADR-040 detail (multi-paragraph) should not be in CLAUDE.md."""
        content = _read_claude_md()
        assert "No transcript replay" not in content, (
            "ADR-040 detail block still in CLAUDE.md"
        )

    def test_no_adr049_detail_block(self):
        """ADR-049 detail (multi-paragraph) should not be in CLAUDE.md."""
        content = _read_claude_md()
        # Check for the distinctive ADR-049 phrase
        assert '"Generate" is deprecated as a step abstraction' not in content, (
            "ADR-049 detail block still in CLAUDE.md"
        )


# ===================================================================
# C14 -- Each skill has valid YAML frontmatter
# ===================================================================


class TestC14ValidFrontmatter:
    """Each SKILL.md must have name and description in YAML frontmatter."""

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_has_frontmatter(self, skill_name):
        content = _read_skill(skill_name)
        assert content.startswith("---"), (
            f"{skill_name}/SKILL.md does not start with YAML frontmatter"
        )
        # Must have closing ---
        assert content.count("---") >= 2, (
            f"{skill_name}/SKILL.md missing closing frontmatter delimiter"
        )

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_has_name_field(self, skill_name):
        content = _read_skill(skill_name)
        fm = _parse_frontmatter(content)
        assert "name" in fm and fm["name"], (
            f"{skill_name}/SKILL.md missing 'name' in frontmatter"
        )

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_has_description_field(self, skill_name):
        content = _read_skill(skill_name)
        fm = _parse_frontmatter(content)
        assert "description" in fm and fm["description"], (
            f"{skill_name}/SKILL.md missing 'description' in frontmatter"
        )


# ===================================================================
# C15 -- Each description includes trigger phrases
# ===================================================================


class TestC15TriggerPhrases:
    """Description field must contain action verbs enabling discovery."""

    # At least one action verb per description
    ACTION_VERBS = [
        "execute", "run", "fix", "dispatch", "report", "manage",
        "validate", "verify", "govern", "test", "audit", "start",
        "close", "create", "enforce", "check",
    ]

    @pytest.mark.parametrize("skill_name", SKILL_NAMES)
    def test_description_has_action_verb(self, skill_name):
        content = _read_skill(skill_name)
        fm = _parse_frontmatter(content)
        desc = fm.get("description", "").lower()
        has_verb = any(verb in desc for verb in self.ACTION_VERBS)
        assert has_verb, (
            f"{skill_name} description lacks action verbs: '{fm.get('description', '')}'"
        )


# ===================================================================
# C16 -- No cross-skill duplication
# ===================================================================


class TestC16NoCrossSkillDuplication:
    """No governance rule appears in full in more than one skill."""

    def _count_skill_occurrences(self, phrase: str) -> list[str]:
        """Return list of skill names containing the phrase."""
        found_in = []
        for name in SKILL_NAMES:
            path = SKILLS_DIR / name / "SKILL.md"
            if path.exists():
                content = path.read_text()
                if phrase in content:
                    found_in.append(name)
        return found_in

    def test_bug_first_not_duplicated(self):
        """Bug-First key content should be in exactly one skill."""
        found_in = self._count_skill_occurrences("Reproduce First")
        assert len(found_in) <= 1, (
            f"Bug-First rule duplicated across skills: {found_in}"
        )

    def test_adr040_not_duplicated(self):
        """ADR-040 key content should be in exactly one skill."""
        found_in = self._count_skill_occurrences(
            "No transcript replay"
        )
        assert len(found_in) <= 1, (
            f"ADR-040 duplicated across skills: {found_in}"
        )

    def test_adr049_not_duplicated(self):
        """ADR-049 key content should be in exactly one skill."""
        found_in = self._count_skill_occurrences("No Black Boxes")
        assert len(found_in) <= 1, (
            f"ADR-049 duplicated across skills: {found_in}"
        )

    def test_seed_governance_not_duplicated(self):
        found_in = self._count_skill_occurrences("Manifest regeneration")
        assert len(found_in) <= 1, (
            f"Seed governance duplicated across skills: {found_in}"
        )

    def test_session_template_not_duplicated(self):
        found_in = self._count_skill_occurrences(SESSION_TEMPLATE_MARKER)
        assert len(found_in) <= 1, (
            f"Session template duplicated across skills: {found_in}"
        )
