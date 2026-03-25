"""Portable governance converter per ADR-060.

Converts Combine-native governance policies into declarative constraints
suitable for export outside the Combine runtime environment.

Strips operational references (scripts, paths, commands) and replaces
them with requirement-style declarations.

Pure function — no DB, no IO beyond the input data.
"""

from __future__ import annotations

import re


# Patterns that reference Combine-internal infrastructure
# Order matters: specific replacements before generic stripping
_OPERATIONAL_PATTERNS = [
    # Specific tool invocations (must run before generic path stripping)
    (re.compile(r'`?ops/scripts/tier0\.sh\s+[^\n`]+`?'), "Tier-0 verification must pass before work is considered complete"),
    (re.compile(r'`ops/scripts/tier0\.sh`'), "Tier-0 verification"),
    # Bash/shell command blocks referencing Combine tooling
    (re.compile(r'```bash\n.*?tier0\.sh.*?```', re.DOTALL), None),
    # Generic path references (after specific replacements)
    (re.compile(r'`?ops/scripts/\S+`?', re.IGNORECASE), None),
    (re.compile(r'`?seed/prompts?/\S+`?', re.IGNORECASE), None),
    (re.compile(r'`?seed/schemas?/\S+`?', re.IGNORECASE), None),
    (re.compile(r'`?combine-config/\S+`?', re.IGNORECASE), None),
]

# Section-level replacements for portable mode
_SECTION_REPLACEMENTS: dict[str, str] = {
    # POL-WS-001 Section 6 references tier0.sh
    "Tier 0 Verification in WS Mode": (
        "### Verification Before Completion\n\n"
        "All work statements MUST be verified against acceptance criteria before completion.\n"
        "Verification MUST confirm:\n\n"
        "- All procedural steps executed\n"
        "- All verification checklist items pass\n"
        "- No files modified outside declared scope\n"
        "- Test suite passes"
    ),
}

# Source attribution patterns to generalize
_SOURCE_PATTERNS = [
    (re.compile(r'\*Source: CLAUDE\.md [^*]+\*'), "*Source: Project governance policy*"),
    (re.compile(r'\*Source: Established [^*]+\*'), "*Source: Project conventions*"),
]


def convert_policies_to_portable(
    policies: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Convert a list of governance policies to portable (declarative) form.

    Each policy dict has 'title' and 'content' keys.
    Returns new list with the same structure but content rewritten.

    Args:
        policies: List of policy dicts from _load_governance_policies().

    Returns:
        New list of policy dicts with portable content.
    """
    return [
        {
            "title": pol["title"],
            "content": _convert_policy_content(pol["content"]),
        }
        for pol in policies
    ]


def _convert_policy_content(content: str) -> str:
    """Convert a single policy's content to portable form."""
    result = content

    # Replace operational references with declarative equivalents
    for pattern, replacement in _OPERATIONAL_PATTERNS:
        if replacement:
            result = pattern.sub(replacement, result)
        else:
            result = pattern.sub("", result)

    # Replace specific sections
    for section_title, replacement_text in _SECTION_REPLACEMENTS.items():
        section_pattern = re.compile(
            r'###\s*' + re.escape(section_title) + r'\n.*?(?=\n###|\n##|\Z)',
            re.DOTALL,
        )
        result = section_pattern.sub(replacement_text, result)

    # Generalize source attributions
    for pattern, replacement in _SOURCE_PATTERNS:
        result = pattern.sub(replacement, result)

    # Clean up artifacts: multiple blank lines, trailing whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r' +\n', '\n', result)

    return result.strip()
