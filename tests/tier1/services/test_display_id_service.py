"""Tests for WS-ID-002: Display ID Service — minting and prefix resolution.

Tests parse_display_id(), resolve_display_id(), and mint_display_id()
per ADR-055 Document Identity Standard.

No runtime, no DB (uses mocks), no LLM.
"""

import re
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.domain.services.display_id_service import (
    parse_display_id,
    resolve_display_id,
    mint_display_id,
)


# ============================================================================
# parse_display_id tests
# ============================================================================

class TestParseDisplayId:
    """Pure function: split {TYPE}-{NNN} into (prefix, number_str)."""

    def test_wpc_001(self):
        assert parse_display_id("WPC-001") == ("WPC", "001")

    def test_pd_001(self):
        assert parse_display_id("PD-001") == ("PD", "001")

    def test_ep_042(self):
        assert parse_display_id("EP-042") == ("EP", "042")

    def test_four_char_prefix(self):
        assert parse_display_id("BLI-001") == ("BLI", "001")

    def test_large_number(self):
        assert parse_display_id("WP-999") == ("WP", "999")

    def test_four_digit_number(self):
        assert parse_display_id("WS-1234") == ("WS", "1234")

    def test_old_snake_case_format_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("wp_wb_001")

    def test_old_ws_format_rejected(self):
        """WS-WB-001 has too many segments — old format, rejected."""
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("WS-WB-001")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("")

    def test_single_char_prefix_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("X-001")

    def test_single_digit_number_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("WP-1")

    def test_two_digit_number_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("WP-01")

    def test_lowercase_prefix_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("wp-001")

    def test_five_char_prefix_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("ABCDE-001")

    def test_legacy_backfill_format_rejected(self):
        with pytest.raises(ValueError, match="Invalid display_id format"):
            parse_display_id("LEGACY-abcd1234")


# ============================================================================
# resolve_display_id tests (mock db)
# ============================================================================

def _mock_db_for_resolve(doc_type_id_result):
    """Create a mock db session that returns doc_type_id_result for scalar()."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = doc_type_id_result
    db = AsyncMock()
    db.execute.return_value = mock_result
    return db


class TestResolveDisplayId:
    """Resolve display_id prefix to doc_type_id via mock DB."""

    @pytest.mark.asyncio
    async def test_resolve_wpc(self):
        db = _mock_db_for_resolve("work_package_candidate")
        result = await resolve_display_id(db, "WPC-001")
        assert result == "work_package_candidate"

    @pytest.mark.asyncio
    async def test_resolve_pd(self):
        db = _mock_db_for_resolve("project_discovery")
        result = await resolve_display_id(db, "PD-001")
        assert result == "project_discovery"

    @pytest.mark.asyncio
    async def test_unknown_prefix_raises(self):
        db = _mock_db_for_resolve(None)
        with pytest.raises(ValueError, match="Unknown display_id prefix"):
            await resolve_display_id(db, "ZZ-001")

    @pytest.mark.asyncio
    async def test_invalid_format_raises_before_db(self):
        """Invalid format raises ValueError without hitting DB."""
        db = AsyncMock()
        with pytest.raises(ValueError, match="Invalid display_id format"):
            await resolve_display_id(db, "wp_wb_001")
        db.execute.assert_not_called()


# ============================================================================
# mint_display_id tests (mock db)
# ============================================================================

def _mock_db_for_mint(prefix_result, max_id_result):
    """Create a mock db session for mint_display_id.

    First execute() returns the prefix, second returns the max display_id.
    """
    prefix_mock = MagicMock()
    prefix_mock.scalar.return_value = prefix_result

    max_mock = MagicMock()
    max_mock.scalar.return_value = max_id_result

    db = AsyncMock()
    db.execute.side_effect = [prefix_mock, max_mock]
    return db


class TestMintDisplayId:
    """Mint sequential display_ids via mock DB."""

    SPACE_ID = UUID("00000000-0000-0000-0000-000000000001")

    @pytest.mark.asyncio
    async def test_first_mint_returns_001(self):
        db = _mock_db_for_mint("WPC", None)
        result = await mint_display_id(db, self.SPACE_ID, "work_package_candidate")
        assert result == "WPC-001"

    @pytest.mark.asyncio
    async def test_mint_after_003_returns_004(self):
        db = _mock_db_for_mint("WPC", "WPC-003")
        result = await mint_display_id(db, self.SPACE_ID, "work_package_candidate")
        assert result == "WPC-004"

    @pytest.mark.asyncio
    async def test_mint_after_099_returns_100(self):
        db = _mock_db_for_mint("WP", "WP-099")
        result = await mint_display_id(db, self.SPACE_ID, "work_package")
        assert result == "WP-100"

    @pytest.mark.asyncio
    async def test_mint_first_pd_returns_pd_001(self):
        db = _mock_db_for_mint("PD", None)
        result = await mint_display_id(db, self.SPACE_ID, "project_discovery")
        assert result == "PD-001"

    @pytest.mark.asyncio
    async def test_no_prefix_raises(self):
        db = _mock_db_for_mint(None, None)
        with pytest.raises(ValueError, match="has no display_prefix"):
            await mint_display_id(db, self.SPACE_ID, "nonexistent_type")

    @pytest.mark.asyncio
    async def test_mint_format_is_zero_padded(self):
        db = _mock_db_for_mint("WS", None)
        result = await mint_display_id(db, self.SPACE_ID, "work_statement")
        assert re.match(r'^WS-\d{3,}$', result), f"Expected zero-padded format, got {result}"

    @pytest.mark.asyncio
    async def test_mint_preserves_prefix_from_registry(self):
        """Prefix comes from DB registry, not from doc_type_id string."""
        db = _mock_db_for_mint("INT", None)
        result = await mint_display_id(db, self.SPACE_ID, "intent_packet")
        assert result.startswith("INT-"), f"Expected INT- prefix, got {result}"
