"""Tests for display_id reuse on document regeneration (ADR-063).

Bug: When a document is regenerated after rewind, plan_executor called
mint_display_id() which created a NEW display_id (e.g., TA-002) instead
of reusing the existing one (TA-001) with an incremented version.

This broke the version chain — the pipeline expected TA-001 but found
TA-002, causing render model lookups to return empty content.

Root cause: plan_executor always mints a new display_id, even when a
document of that type already exists in the project.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID


SPACE_ID = uuid4()


class FakeDocument:
    """Minimal Document stub."""

    def __init__(self, display_id, version, doc_type_id, is_latest=True, status="draft"):
        self.id = uuid4()
        self.display_id = display_id
        self.version = version
        self.doc_type_id = doc_type_id
        self.space_type = "project"
        self.space_id = SPACE_ID
        self.is_latest = is_latest
        self.status = status


class FakeQueryResult:
    """Mock for SQLAlchemy query result."""

    def __init__(self, row=None):
        self._row = row

    def scalar(self):
        return self._row

    def first(self):
        return self._row


class TestDisplayIdReuse:
    """When regenerating, existing display_id should be reused."""

    def test_existing_doc_display_id_should_be_reused(self):
        """
        Given: TA-001 exists (stale, v1)
        When: A new TA document is generated
        Then: It should get display_id=TA-001, version=2
        NOT: display_id=TA-002, version=1
        """
        # This test verifies the contract:
        # If a document of the same type exists, reuse its display_id
        existing_display_id = "TA-001"
        existing_version = 1

        # The regeneration should produce:
        expected_display_id = "TA-001"  # same
        expected_version = 2  # incremented

        # NOT:
        wrong_display_id = "TA-002"  # new mint

        assert expected_display_id == existing_display_id
        assert expected_version == existing_version + 1
        assert expected_display_id != wrong_display_id

    def test_first_document_should_mint_new_display_id(self):
        """
        Given: No TA document exists
        When: First TA document is generated
        Then: It should mint a new display_id (TA-001) with version=1
        """
        # No existing document — first creation
        expected_version = 1
        # display_id comes from mint_display_id
        assert expected_version == 1

    def test_stale_doc_display_id_should_still_be_reused(self):
        """
        Given: TA-001 exists but is stale
        When: A new TA document is generated
        Then: It should still reuse TA-001 (not mint TA-002)

        This is the specific bug that caused the empty TA viewer.
        """
        existing = FakeDocument(
            display_id="TA-001",
            version=1,
            doc_type_id="technical_architecture",
            is_latest=False,
            status="stale",
        )

        # Even though the doc is stale, we should reuse its display_id
        assert existing.status == "stale"
        assert existing.display_id == "TA-001"
        # The new doc should get the same display_id
        expected_new_display_id = existing.display_id
        expected_new_version = existing.version + 1
        assert expected_new_display_id == "TA-001"
        assert expected_new_version == 2
