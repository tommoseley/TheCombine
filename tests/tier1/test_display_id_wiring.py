"""Tests for WS-ID-003: Display ID wiring into document creation paths.

Validates that all document creation paths call mint_display_id() and set
the display_id column on the created Document per ADR-055.

No runtime, no DB (uses mocks), no LLM.
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


# ============================================================================
# Helpers
# ============================================================================

SPACE_ID = uuid4()
DISPLAY_ID_PATTERN = re.compile(r'^[A-Z]{2,4}-\d{3,}$')


def _mock_db_for_mint(prefix: str, max_id: str | None):
    """Build a mock db session that mint_display_id can use.

    First execute() returns the display_prefix.
    Second execute() returns the current max display_id (or None).
    """
    prefix_result = MagicMock()
    prefix_result.scalar.return_value = prefix

    max_result = MagicMock()
    max_result.scalar.return_value = max_id

    db = AsyncMock()
    db.execute.side_effect = [prefix_result, max_result]
    return db


# ============================================================================
# 1. plan_executor — parent document creation
# ============================================================================

class TestPlanExecutorParentMintsCalled:
    """Verify _execute_node_steps sets display_id on the parent Document."""

    def test_parent_document_gets_display_id(self):
        """Parent creation source: mints display_id and passes it to Document()."""
        import inspect
        import sys

        mock_production = MagicMock()
        mock_production.publish_event = AsyncMock()
        sys.modules.setdefault("app.api.v1.routers.production", mock_production)

        from app.domain.workflow.plan_executor import PlanExecutor
        source = inspect.getsource(PlanExecutor._persist_produced_documents)
        assert 'mint_display_id' in source, (
            "_persist_produced_documents must call mint_display_id"
        )
        assert 'display_id=did' in source or 'display_id=' in source, (
            "_persist_produced_documents must pass display_id to Document constructor"
        )


class TestPlanExecutorParentDisplayId:
    """Verify the mint_display_id import and Document constructor wiring."""

    def test_mint_display_id_imported_in_plan_executor(self):
        """plan_executor.py source imports mint_display_id (lazy)."""
        import inspect
        import sys

        mock_production = MagicMock()
        mock_production.publish_event = AsyncMock()
        sys.modules.setdefault("app.api.v1.routers.production", mock_production)

        import app.domain.workflow.plan_executor as pe_mod
        source = inspect.getsource(pe_mod)
        assert 'from app.domain.services.display_id_service import mint_display_id' in source, (
            "plan_executor must import mint_display_id"
        )

    def test_parent_document_constructor_includes_display_id(self):
        """Verify plan_executor source includes display_id= in parent Document()."""
        import inspect
        import sys

        mock_production = MagicMock()
        mock_production.publish_event = AsyncMock()
        sys.modules.setdefault("app.api.v1.routers.production", mock_production)

        from app.domain.workflow.plan_executor import PlanExecutor
        source = inspect.getsource(PlanExecutor._persist_produced_documents)
        assert 'display_id=did' in source or 'display_id=' in source, (
            "_persist_produced_documents must set display_id on parent Document"
        )

    def test_child_document_constructor_includes_display_id(self):
        """Verify plan_executor source includes display_id= in child Document()."""
        import inspect
        import sys

        mock_production = MagicMock()
        mock_production.publish_event = AsyncMock()
        sys.modules.setdefault("app.api.v1.routers.production", mock_production)

        from app.domain.workflow.plan_executor import PlanExecutor
        source = inspect.getsource(PlanExecutor._upsert_child_document)
        assert 'display_id=did' in source or 'display_id=' in source, (
            "_upsert_child_document must set display_id on child Document"
        )


# ============================================================================
# 2. plan_executor — child document spawning
# ============================================================================

class TestPlanExecutorChildMinting:
    """Verify _upsert_child_document mints display_id for new children."""

    @pytest.mark.asyncio
    async def test_new_child_gets_minted_display_id(self):
        """When creating a new child, mint_display_id is called and result set."""
        import sys

        mock_production = MagicMock()
        mock_production.publish_event = AsyncMock()
        sys.modules.setdefault("app.api.v1.routers.production", mock_production)

        from app.domain.workflow.plan_executor import PlanExecutor

        pe = PlanExecutor.__new__(PlanExecutor)
        pe._db_session = AsyncMock()

        state = MagicMock()
        state.project_id = str(SPACE_ID)
        parent_id = uuid4()

        spec = {
            "identifier": "epic_alpha",
            "doc_type_id": "epic",
            "title": "Epic Alpha",
            "content": {"name": "alpha"},
        }

        with patch(
            "app.domain.services.display_id_service.mint_display_id",
            new_callable=AsyncMock,
            return_value="EP-001",
        ) as mock_mint:
            result = await pe._upsert_child_document(
                spec, {}, state, parent_id,
            )

        assert result == "created"
        mock_mint.assert_awaited_once_with(
            pe._db_session, UUID(state.project_id), "epic",
        )
        # Verify Document was added with display_id
        created_doc = pe._db_session.add.call_args[0][0]
        assert created_doc.display_id == "EP-001"

    @pytest.mark.asyncio
    async def test_existing_child_update_does_not_remint(self):
        """When updating an existing child, mint_display_id is NOT called."""
        import sys

        mock_production = MagicMock()
        mock_production.publish_event = AsyncMock()
        sys.modules.setdefault("app.api.v1.routers.production", mock_production)

        from app.domain.workflow.plan_executor import PlanExecutor

        pe = PlanExecutor.__new__(PlanExecutor)
        pe._db_session = AsyncMock()

        state = MagicMock()
        state.project_id = str(SPACE_ID)
        parent_id = uuid4()

        existing_doc = MagicMock()
        existing_doc.instance_id = "epic_alpha"
        existing_doc.version = 1
        existing_children = {"epic_alpha": existing_doc}

        spec = {
            "identifier": "epic_alpha",
            "doc_type_id": "epic",
            "title": "Epic Alpha Updated",
            "content": {"name": "alpha_v2"},
        }

        with patch(
            "app.domain.services.display_id_service.mint_display_id",
            new_callable=AsyncMock,
        ) as mock_mint:
            result = await pe._upsert_child_document(
                spec, existing_children, state, parent_id,
            )

        assert result == "updated"
        mock_mint.assert_not_awaited()


# ============================================================================
# 3. project_creation_service — concierge_intake
# ============================================================================

class TestProjectCreationServiceMinting:
    """Verify create_project_from_intake mints display_id for concierge_intake."""

    @pytest.mark.asyncio
    async def test_concierge_intake_gets_display_id(self):
        """Intake document creation calls mint_display_id and sets result."""
        from app.api.services.project_creation_service import create_project_from_intake

        mock_db = AsyncMock()
        project_id = uuid4()

        # Mock the Project creation (flush returns project with id)
        mock_project = MagicMock()
        mock_project.id = project_id
        mock_project.project_id = "TST-001"
        mock_project.name = "Test Project"

        # Mock generate_unique_project_id
        with patch(
            "app.api.services.project_creation_service.generate_unique_project_id",
            new_callable=AsyncMock,
            return_value="TST-001",
        ), patch(
            "app.domain.services.display_id_service.mint_display_id",
            new_callable=AsyncMock,
            return_value="CI-001",
        ) as mock_mint, patch(
            "app.api.services.project_creation_service.Document",
        ) as MockDocument, patch(
            "app.api.services.project_creation_service.Project",
            return_value=mock_project,
        ):
            MockDocument.return_value = MagicMock()

            await create_project_from_intake(
                db=mock_db,
                intake_document={"project_name": "Test Project", "summary": {"description": "A test"}},
                execution_id="exec-001",
            )

            mock_mint.assert_awaited_once_with(mock_db, project_id, "concierge_intake")
            # Verify Document was called with display_id
            doc_call_kwargs = MockDocument.call_args
            # Check kwargs or positional — Document is called with keyword args
            assert doc_call_kwargs.kwargs.get("display_id") == "CI-001" or \
                   (doc_call_kwargs[1].get("display_id") == "CI-001" if len(doc_call_kwargs) > 1 else False), \
                   f"Document must be created with display_id='CI-001', got: {doc_call_kwargs}"

    def test_mint_display_id_imported_in_project_creation_service(self):
        """project_creation_service.py source imports mint_display_id (lazy)."""
        import inspect
        import app.api.services.project_creation_service as pcs_mod
        source = inspect.getsource(pcs_mod)
        assert 'from app.domain.services.display_id_service import mint_display_id' in source, (
            "project_creation_service must import mint_display_id"
        )


# ============================================================================
# 4. intents.py — intent_packet
# ============================================================================

class TestIntentRouterMinting:
    """Verify intent creation mints display_id for intent_packet."""

    def test_mint_display_id_imported_in_intents(self):
        """intents.py source imports mint_display_id (lazy)."""
        import inspect
        import app.api.v1.routers.intents as intents_mod
        source = inspect.getsource(intents_mod)
        assert 'from app.domain.services.display_id_service import mint_display_id' in source, (
            "intents.py must import mint_display_id"
        )

    def test_create_intent_source_includes_display_id(self):
        """Verify intents.py source includes display_id= in Document constructor."""
        import inspect
        from app.api.v1.routers.intents import create_intent
        source = inspect.getsource(create_intent)
        assert 'display_id=did' in source or 'display_id=' in source, (
            "create_intent must set display_id on Document"
        )

    def test_create_intent_source_calls_mint(self):
        """Verify intents.py source calls mint_display_id."""
        import inspect
        from app.api.v1.routers.intents import create_intent
        source = inspect.getsource(create_intent)
        assert 'mint_display_id' in source, (
            "create_intent must call mint_display_id"
        )


# ============================================================================
# 5. document_service.create_document() — generic path
# ============================================================================

class TestDocumentServiceMinting:
    """Verify DocumentService.create_document accepts and uses display_id."""

    @pytest.mark.asyncio
    async def test_explicit_display_id_is_set(self):
        """When display_id is provided, it is used directly (no minting)."""
        from app.api.services.document_service import DocumentService

        mock_db = AsyncMock()
        # get_latest returns None (no existing version)
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        svc = DocumentService(mock_db)

        with patch(
            "app.domain.services.display_id_service.mint_display_id",
            new_callable=AsyncMock,
        ) as mock_mint, patch.object(
            svc, 'get_latest', new_callable=AsyncMock, return_value=None,
        ):
            doc = await svc.create_document(
                space_type="project",
                space_id=SPACE_ID,
                doc_type_id="work_package",
                title="Test WP",
                content={"data": "test"},
                display_id="WP-042",
            )

            mock_mint.assert_not_awaited()
            assert doc.display_id == "WP-042"

    @pytest.mark.asyncio
    async def test_auto_mint_when_display_id_not_provided(self):
        """When display_id is None, mint_display_id is called automatically."""
        from app.api.services.document_service import DocumentService

        mock_db = AsyncMock()

        svc = DocumentService(mock_db)

        with patch(
            "app.domain.services.display_id_service.mint_display_id",
            new_callable=AsyncMock,
            return_value="WP-001",
        ) as mock_mint, patch.object(
            svc, 'get_latest', new_callable=AsyncMock, return_value=None,
        ):
            doc = await svc.create_document(
                space_type="project",
                space_id=SPACE_ID,
                doc_type_id="work_package",
                title="Test WP",
                content={"data": "test"},
                # display_id intentionally omitted
            )

            mock_mint.assert_awaited_once_with(mock_db, SPACE_ID, "work_package")
            assert doc.display_id == "WP-001"

    def test_create_document_accepts_display_id_parameter(self):
        """create_document() signature includes display_id parameter."""
        import inspect
        from app.api.services.document_service import DocumentService
        sig = inspect.signature(DocumentService.create_document)
        param_names = list(sig.parameters.keys())
        assert 'display_id' in param_names, (
            f"create_document must accept display_id parameter. Params: {param_names}"
        )


# ============================================================================
# 6. Format validation — all display_ids match {TYPE}-{NNN}
# ============================================================================

class TestDisplayIdFormatContract:
    """Verify the minted display_ids follow the {TYPE}-{NNN} format."""

    @pytest.mark.asyncio
    async def test_first_mint_format(self):
        """First mint returns {PREFIX}-001 format."""
        from app.domain.services.display_id_service import mint_display_id

        db = _mock_db_for_mint("WP", None)
        result = await mint_display_id(db, SPACE_ID, "work_package")
        assert DISPLAY_ID_PATTERN.match(result), f"Expected {{TYPE}}-{{NNN}}, got {result}"
        assert result == "WP-001"

    @pytest.mark.asyncio
    async def test_sequential_format(self):
        """Sequential mint returns properly incremented format."""
        from app.domain.services.display_id_service import mint_display_id

        db = _mock_db_for_mint("WP", "WP-005")
        result = await mint_display_id(db, SPACE_ID, "work_package")
        assert DISPLAY_ID_PATTERN.match(result), f"Expected {{TYPE}}-{{NNN}}, got {result}"
        assert result == "WP-006"

    @pytest.mark.asyncio
    async def test_concierge_intake_prefix(self):
        """Concierge intake uses CI prefix."""
        from app.domain.services.display_id_service import mint_display_id

        db = _mock_db_for_mint("CI", None)
        result = await mint_display_id(db, SPACE_ID, "concierge_intake")
        assert result == "CI-001"
        assert DISPLAY_ID_PATTERN.match(result)

    @pytest.mark.asyncio
    async def test_intent_packet_prefix(self):
        """Intent packet uses INT prefix."""
        from app.domain.services.display_id_service import mint_display_id

        db = _mock_db_for_mint("INT", None)
        result = await mint_display_id(db, SPACE_ID, "intent_packet")
        assert result == "INT-001"
        assert DISPLAY_ID_PATTERN.match(result)


# ============================================================================
# 7. Sequential minting produces incrementing numbers
# ============================================================================

class TestSequentialMinting:
    """Verify sequential minting produces incrementing numbers."""

    @pytest.mark.asyncio
    async def test_sequential_mints_increment(self):
        """Minting after WP-001 gives WP-002, after WP-002 gives WP-003."""
        from app.domain.services.display_id_service import mint_display_id

        # First: no existing
        db1 = _mock_db_for_mint("WP", None)
        r1 = await mint_display_id(db1, SPACE_ID, "work_package")
        assert r1 == "WP-001"

        # Second: after WP-001
        db2 = _mock_db_for_mint("WP", "WP-001")
        r2 = await mint_display_id(db2, SPACE_ID, "work_package")
        assert r2 == "WP-002"

        # Third: after WP-002
        db3 = _mock_db_for_mint("WP", "WP-002")
        r3 = await mint_display_id(db3, SPACE_ID, "work_package")
        assert r3 == "WP-003"

    @pytest.mark.asyncio
    async def test_zero_padding_preserved(self):
        """Numbers are zero-padded to at least 3 digits."""
        from app.domain.services.display_id_service import mint_display_id

        db = _mock_db_for_mint("EP", None)
        result = await mint_display_id(db, SPACE_ID, "epic")
        assert result == "EP-001"
        assert len(result.split("-")[1]) >= 3

    @pytest.mark.asyncio
    async def test_large_numbers_not_truncated(self):
        """Numbers above 999 are not truncated."""
        from app.domain.services.display_id_service import mint_display_id

        db = _mock_db_for_mint("WP", "WP-999")
        result = await mint_display_id(db, SPACE_ID, "work_package")
        assert result == "WP-1000"
