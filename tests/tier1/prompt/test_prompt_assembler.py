"""Golden tests for PromptAssembler.

Per ADR-041 Section 11b: Test Plan

These tests verify:
- Determinism (same inputs -> byte-identical output)
- Token resolution (Workflow Tokens + Template Includes)
- Failure modes (explicit, typed errors)
"""

import pytest
from pathlib import Path
from uuid import UUID

from app.domain.prompt.assembler import PromptAssembler
from app.domain.prompt.errors import (
    UnresolvedTokenError,
    IncludeNotFoundError,
    NestedTokenError,
    EncodingError,
)


FIXTURES = Path("tests/fixtures/adr041")


class TestPromptAssemblerHappyPath:
    """Golden test: assembled prompt matches expected output byte-for-byte."""

    def test_assemble_matches_golden_fixture(self):
        """Happy path: assembled prompt is byte-identical to golden file."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        result = assembler.assemble(
            task_ref="clarification_generator_v1",
            includes={
                "PGC_CONTEXT": str(FIXTURES / "includes/pgc_context_project_discovery_v1.txt"),
                "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
            },
            correlation_id=UUID("00000000-0000-0000-0000-000000000001"),
        )

        expected_content = (
            FIXTURES / "expected/assembled_clarification_generator_project_discovery_v1.txt"
        ).read_text()
        expected_hash = (
            FIXTURES / "expected/assembled_clarification_generator_project_discovery_v1.sha256"
        ).read_text().strip()

        assert result.content == expected_content
        assert result.content_hash == expected_hash
        assert result.task_ref == "clarification_generator_v1"
        assert result.includes_resolved == {
            "PGC_CONTEXT": str(FIXTURES / "includes/pgc_context_project_discovery_v1.txt"),
            "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
        }
        assert result.correlation_id == UUID("00000000-0000-0000-0000-000000000001")
        assert result.assembled_at is not None

    def test_assembled_prompt_is_immutable(self):
        """AssembledPrompt is frozen dataclass."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        result = assembler.assemble(
            task_ref="clarification_generator_v1",
            includes={
                "PGC_CONTEXT": str(FIXTURES / "includes/pgc_context_project_discovery_v1.txt"),
                "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
            },
            correlation_id=UUID("00000000-0000-0000-0000-000000000001"),
        )

        with pytest.raises(AttributeError):
            result.content = "modified"


class TestPromptAssemblerFailureModes:
    """All failure modes produce explicit, typed errors."""

    def test_unresolved_workflow_token_fails(self):
        """Workflow Token without matching include fails explicitly."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        with pytest.raises(UnresolvedTokenError) as exc:
            assembler.assemble(
                task_ref="template_with_missing_token",
                includes={},
                correlation_id=UUID("00000000-0000-0000-0000-000000000002"),
            )

        assert exc.value.token == "UNDEFINED_TOKEN"

    def test_missing_include_file_fails(self):
        """Include pointing to non-existent file fails explicitly."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        with pytest.raises(IncludeNotFoundError) as exc:
            assembler.assemble(
                task_ref="clarification_generator_v1",
                includes={
                    "PGC_CONTEXT": "tests/fixtures/adr041/includes/does_not_exist.txt",
                    "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
                },
                correlation_id=UUID("00000000-0000-0000-0000-000000000003"),
            )

        assert "does_not_exist.txt" in exc.value.path

    def test_missing_template_fails(self):
        """Non-existent template fails explicitly."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        with pytest.raises(IncludeNotFoundError) as exc:
            assembler.assemble(
                task_ref="nonexistent_template",
                includes={},
                correlation_id=UUID("00000000-0000-0000-0000-000000000004"),
            )

        assert "nonexistent_template" in exc.value.path

    def test_nested_tokens_in_include_fails(self):
        """Include file containing tokens is prohibited."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        with pytest.raises(NestedTokenError) as exc:
            assembler.assemble(
                task_ref="clarification_generator_v1",
                includes={
                    "PGC_CONTEXT": str(FIXTURES / "includes/nested_tokens.txt"),
                    "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
                },
                correlation_id=UUID("00000000-0000-0000-0000-000000000005"),
            )

        assert "nested_tokens.txt" in exc.value.path
        assert exc.value.token == "NESTED"

    def test_non_utf8_include_fails(self):
        """Non-UTF8 file fails explicitly."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        with pytest.raises(EncodingError) as exc:
            assembler.assemble(
                task_ref="clarification_generator_v1",
                includes={
                    "PGC_CONTEXT": str(FIXTURES / "includes/non_utf8.bin"),
                    "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
                },
                correlation_id=UUID("00000000-0000-0000-0000-000000000006"),
            )

        assert "non_utf8.bin" in exc.value.path

    def test_crlf_normalized_to_lf(self):
        """CRLF line endings are normalized, hash is stable."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        result = assembler.assemble(
            task_ref="clarification_generator_v1",
            includes={
                "PGC_CONTEXT": str(FIXTURES / "includes/crlf_file.txt"),
                "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
            },
            correlation_id=UUID("00000000-0000-0000-0000-000000000007"),
        )

        # Verify no CRLF or CR in output
        assert "\r\n" not in result.content
        assert "\r" not in result.content

        # Verify hash is stable (computed on LF-normalized content)
        assert len(result.content_hash) == 64  # SHA-256 hex string


class TestPromptAssemblerDeterminism:
    """Assembly is deterministic: same inputs -> same output."""

    def test_same_inputs_produce_same_hash(self):
        """Multiple assemblies with same inputs produce identical hashes."""
        assembler = PromptAssembler(template_root=str(FIXTURES / "templates"))

        includes = {
            "PGC_CONTEXT": str(FIXTURES / "includes/pgc_context_project_discovery_v1.txt"),
            "OUTPUT_SCHEMA": str(FIXTURES / "includes/clarification_schema_v2.json"),
        }

        result1 = assembler.assemble(
            task_ref="clarification_generator_v1",
            includes=includes,
            correlation_id=UUID("00000000-0000-0000-0000-000000000008"),
        )

        result2 = assembler.assemble(
            task_ref="clarification_generator_v1",
            includes=includes,
            correlation_id=UUID("00000000-0000-0000-0000-000000000009"),
        )

        assert result1.content == result2.content
        assert result1.content_hash == result2.content_hash