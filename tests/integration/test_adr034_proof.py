"""
Integration tests for ADR-034 proof of concept.

Per WS-ADR-034-POC Phase 8.4: End-to-end integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.domain.services.prompt_assembler import PromptAssembler, AssembledPrompt
from app.domain.services.render_model_builder import RenderModelBuilder, RenderModel
from app.api.services.fragment_registry_service import FRAGMENT_ALIASES


class TestADR034ProofOfConcept:
    """Integration tests proving ADR-034 acceptance criteria."""
    
    @pytest.fixture
    def epic_backlog_docdef(self):
        """Create EpicBacklog document definition fixture."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:EpicBacklog:1.0.0"
        docdef.prompt_header = {
            "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
            "constraints": [
                "Output valid JSON matching the document schema.",
                "Be specific and actionable.",
                "Do not invent requirements not supported by inputs.",
                "Each epic must have at least one open question if unknowns exist."
            ],
        }
        docdef.sections = [{
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {"epic_id": "/id", "epic_title": "/title"},
        }]
        return docdef
    
    @pytest.fixture
    def open_question_component(self):
        """Create OpenQuestionV1 component fixture."""
        comp = MagicMock()
        comp.component_id = "component:OpenQuestionV1:1.0.0"
        comp.schema_id = "schema:OpenQuestionV1"
        comp.generation_guidance = {
            "bullets": [
                "Provide a stable question id (e.g., Q-001).",
                "Write a clear, specific question that requires human decision.",
                "Set blocking=true only if work cannot proceed responsibly without an answer.",
                "Explain why_it_matters in one sentence.",
                "Include options only if there are meaningful discrete choices.",
                "If options exist, default_response SHOULD match one option.",
                "Use notes for assumptions, context, or follow-up suggestions."
            ]
        }
        comp.view_bindings = {
            "web": {"fragment_id": "fragment:OpenQuestionV1:web:1.0.0"}
        }
        return comp
    
    @pytest.fixture
    def sample_epic_data(self):
        """Create sample Epic Backlog document data."""
        return {
            "epics": [
                {
                    "id": "E-001",
                    "title": "User Authentication",
                    "open_questions": [
                        {
                            "id": "Q-001",
                            "text": "Should we support SSO?",
                            "blocking": True,
                            "why_it_matters": "Affects architecture decisions.",
                        },
                        {
                            "id": "Q-002",
                            "text": "What password policy?",
                            "blocking": False,
                            "why_it_matters": "Security compliance requirement.",
                        },
                    ],
                },
                {
                    "id": "E-002",
                    "title": "Dashboard",
                    "open_questions": [
                        {
                            "id": "Q-003",
                            "text": "Real-time or polling?",
                            "blocking": True,
                            "why_it_matters": "Infrastructure cost implications.",
                        },
                    ],
                },
            ]
        }
    
    @pytest.mark.asyncio
    async def test_epic_backlog_prompt_assembly_includes_open_question_bullets(
        self, epic_backlog_docdef, open_question_component
    ):
        """Test that EpicBacklog prompt assembly includes OpenQuestion bullets."""
        mock_docdef_service = AsyncMock()
        mock_docdef_service.get.return_value = epic_backlog_docdef
        
        mock_component_service = AsyncMock()
        mock_component_service.get.return_value = open_question_component
        
        assembler = PromptAssembler(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        result = await assembler.assemble("docdef:EpicBacklog:1.0.0")
        
        # Should include all OpenQuestion bullets
        assert "Provide a stable question id" in result.component_bullets[0]
        assert len(result.component_bullets) == 7
        
        # Should include header
        assert "Business Analyst" in result.header["role"]
        assert len(result.header["constraints"]) == 4
        
        # Should have schema bundle
        assert result.schema_bundle is not None
        assert "schema:OpenQuestionV1" in result.schema_bundle["component_schemas"]
    
    @pytest.mark.asyncio
    async def test_epic_backlog_render_model_produces_question_blocks_with_context(
        self, epic_backlog_docdef, open_question_component, sample_epic_data
    ):
        """Test that EpicBacklog produces RenderBlocks with epic context."""
        mock_docdef_service = AsyncMock()
        mock_docdef_service.get.return_value = epic_backlog_docdef
        
        mock_component_service = AsyncMock()
        mock_component_service.get.return_value = open_question_component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        result = await builder.build("docdef:EpicBacklog:1.0.0", sample_epic_data)
        
        # Should have 3 blocks (2 questions from E-001, 1 from E-002)
        assert len(result.blocks) == 3
        
        # All blocks should be OpenQuestionV1 type
        for block in result.blocks:
            assert block.type == "schema:OpenQuestionV1"
        
        # First two blocks should have E-001 context
        assert result.blocks[0].context["epic_id"] == "E-001"
        assert result.blocks[0].context["epic_title"] == "User Authentication"
        assert result.blocks[1].context["epic_id"] == "E-001"
        
        # Third block should have E-002 context
        assert result.blocks[2].context["epic_id"] == "E-002"
        assert result.blocks[2].context["epic_title"] == "Dashboard"
        
        # Verify data from questions
        assert result.blocks[0].data["id"] == "Q-001"
        assert result.blocks[2].data["id"] == "Q-003"
    
    def test_fragment_alias_resolution_in_view_bindings(self, open_question_component):
        """Test that canonical fragment IDs in view_bindings map via alias."""
        # Component stores canonical format
        fragment_id = open_question_component.view_bindings["web"]["fragment_id"]
        assert fragment_id == "fragment:OpenQuestionV1:web:1.0.0"
        
        # Alias mapping exists
        assert fragment_id in FRAGMENT_ALIASES
        assert FRAGMENT_ALIASES[fragment_id] == "OpenQuestionV1Fragment"
    
    @pytest.fixture
    def epic_backlog_v1_1_docdef(self):
        """Create EpicBacklog v1.1.0 document definition with container shape."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:EpicBacklog:1.1.0"
        docdef.prompt_header = {
            "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
            "constraints": [
                "Output valid JSON matching the document schema.",
                "Be specific and actionable.",
                "Do not invent requirements not supported by inputs.",
                "Each epic must have at least one open question if unknowns exist."
            ],
        }
        docdef.sections = [{
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {"epic_id": "/id", "epic_title": "/title"},
        }]
        return docdef
    
    @pytest.fixture
    def open_questions_block_component(self):
        """Create OpenQuestionsBlockV1 container component fixture."""
        comp = MagicMock()
        comp.component_id = "component:OpenQuestionsBlockV1:1.0.0"
        comp.schema_id = "schema:OpenQuestionsBlockV1"
        comp.generation_guidance = {
            "bullets": [
                "This is a container block for rendering; generation guidance is minimal.",
                "Item-level guidance is provided by OpenQuestionV1."
            ]
        }
        comp.view_bindings = {
            "web": {"fragment_id": "fragment:OpenQuestionsBlockV1:web:1.0.0"}
        }
        return comp
    
    @pytest.mark.asyncio
    async def test_epic_backlog_v1_1_produces_container_block(
        self, epic_backlog_v1_1_docdef, open_questions_block_component, sample_epic_data
    ):
        """EpicBacklog v1.1.0 produces single container block with all questions."""
        mock_docdef_service = AsyncMock()
        mock_docdef_service.get.return_value = epic_backlog_v1_1_docdef
        
        mock_component_service = AsyncMock()
        mock_component_service.get.return_value = open_questions_block_component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        result = await builder.build("docdef:EpicBacklog:1.1.0", sample_epic_data)
        
        # Should have 2 container blocks (one per epic)
        assert len(result.blocks) == 2
        
        # First block: Epic E-001 with 2 questions
        assert result.blocks[0].type == "schema:OpenQuestionsBlockV1"
        assert result.blocks[0].context["epic_id"] == "E-001"
        assert len(result.blocks[0].data["items"]) == 2
        assert result.blocks[0].data["items"][0]["id"] == "Q-001"
        
        # Second block: Epic E-002 with 1 question
        assert result.blocks[1].type == "schema:OpenQuestionsBlockV1"
        assert result.blocks[1].context["epic_id"] == "E-002"
        assert len(result.blocks[1].data["items"]) == 1
        assert result.blocks[1].data["items"][0]["id"] == "Q-003"
    
    @pytest.mark.asyncio
    async def test_v1_0_vs_v1_1_comparison(
        self, epic_backlog_docdef, open_question_component,
        epic_backlog_v1_1_docdef, open_questions_block_component, sample_epic_data
    ):
        """Compare v1.0.0 (nested_list) vs v1.1.0 (container) output."""
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        # v1.0.0 with nested_list
        mock_docdef_service.get.return_value = epic_backlog_docdef
        mock_component_service.get.return_value = open_question_component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        result_v1_0 = await builder.build("docdef:EpicBacklog:1.0.0", sample_epic_data)
        
        # v1.0.0: 3 blocks (one per question)
        assert len(result_v1_0.blocks) == 3
        assert all(b.type == "schema:OpenQuestionV1" for b in result_v1_0.blocks)
        
        # v1.1.0 with container
        mock_docdef_service.get.return_value = epic_backlog_v1_1_docdef
        mock_component_service.get.return_value = open_questions_block_component
        
        result_v1_1 = await builder.build("docdef:EpicBacklog:1.1.0", sample_epic_data)
        
        # v1.1.0: 2 blocks (one per epic), total 3 questions across them
        assert len(result_v1_1.blocks) == 2
        assert all(b.type == "schema:OpenQuestionsBlockV1" for b in result_v1_1.blocks)
        total_items = sum(len(b.data["items"]) for b in result_v1_1.blocks)
        assert total_items == 3

    # ==========================================================================
    # WS-ADR-034-EXP2: Structural Variety Tests
    # ==========================================================================
    
    @pytest.fixture
    def root_questions_docdef(self):
        """Create root-level questions docdef (S1)."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:RootQuestionsTest:1.0.0"
        docdef.prompt_header = {"role": "Test", "constraints": []}
        docdef.sections = [{
            "section_id": "root_questions",
            "title": "Open Questions",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions"
            # No repeat_over - root level
        }]
        return docdef
    
    @pytest.mark.asyncio
    async def test_s1_root_level_container(
        self, root_questions_docdef, open_questions_block_component
    ):
        """S1: Root-level container renders correctly without repeat_over."""
        mock_docdef_service = AsyncMock()
        mock_docdef_service.get.return_value = root_questions_docdef
        
        mock_component_service = AsyncMock()
        mock_component_service.get.return_value = open_questions_block_component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        # Root-level payload - no epics, questions at root
        document_data = {
            "open_questions": [
                {"id": "Q-001", "text": "Root question 1", "blocking": True},
                {"id": "Q-002", "text": "Root question 2", "blocking": False},
            ]
        }
        
        result = await builder.build("docdef:RootQuestionsTest:1.0.0", document_data)
        
        # Should have exactly ONE container block
        assert len(result.blocks) == 1
        assert result.blocks[0].type == "schema:OpenQuestionsBlockV1"
        assert result.blocks[0].key == "root_questions:container"
        
        # Block should contain both questions
        assert len(result.blocks[0].data["items"]) == 2
        assert result.blocks[0].data["items"][0]["id"] == "Q-001"
        assert result.blocks[0].data["items"][1]["id"] == "Q-002"
        
        # No context for root level
        assert result.blocks[0].context is None
    
    @pytest.fixture
    def deep_nesting_docdef(self):
        """Create deep nesting test docdef (S3 probe)."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:DeepNestingTest:1.0.0"
        docdef.prompt_header = {"role": "Test", "constraints": []}
        docdef.sections = [{
            "section_id": "deep_questions",
            "title": "Capability Questions",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {"epic_id": "/id", "epic_title": "/title"}
        }]
        return docdef
    
    @pytest.mark.asyncio
    async def test_s3_deep_nesting_probe_documents_limitation(
        self, deep_nesting_docdef, open_questions_block_component
    ):
        """
        S3 Probe: Document behavior with 3-level nested payload.
        
        Payload: /epics/*/capabilities/*/open_questions
        Config: repeat_over=/epics, source_pointer=/open_questions
        
        Expected: Current config cannot reach /capabilities/*/open_questions.
        It will look for /open_questions directly under each epic, find none,
        and produce empty or no blocks.
        
        This test documents the current boundary, not a failure.
        """
        mock_docdef_service = AsyncMock()
        mock_docdef_service.get.return_value = deep_nesting_docdef
        
        mock_component_service = AsyncMock()
        mock_component_service.get.return_value = open_questions_block_component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        # 3-level nested payload: epics -> capabilities -> open_questions
        document_data = {
            "epics": [
                {
                    "id": "E-001",
                    "title": "Epic 1",
                    "capabilities": [
                        {
                            "id": "C-001",
                            "name": "Capability 1",
                            "open_questions": [
                                {"id": "Q-001", "text": "Deep Q1", "blocking": True}
                            ]
                        },
                        {
                            "id": "C-002",
                            "name": "Capability 2",
                            "open_questions": [
                                {"id": "Q-002", "text": "Deep Q2", "blocking": False}
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = await builder.build("docdef:DeepNestingTest:1.0.0", document_data)
        
        # DOCUMENTED BEHAVIOR (PROBE OUTCOME):
        # Current limitation: repeat_over=/epics + source_pointer=/open_questions
        # looks for /open_questions at each epic level, NOT inside /capabilities.
        # Since epics don't have direct /open_questions, result is empty.
        
        # This documents the boundary:
        # "Container sections support at most one level of parent iteration.
        #  Nested iteration (e.g., /epics/*/capabilities/*) is not supported."
        
        # The container block is produced (iterating epics), but items are empty
        # because /open_questions doesn't exist directly under each epic
        if len(result.blocks) == 0:
            # No blocks produced - epics had no direct /open_questions
            pass  # Acceptable outcome - boundary documented
        else:
            # If a block was produced, items should be empty
            assert result.blocks[0].data["items"] == [] or len(result.blocks[0].data.get("items", [])) == 0

    # ==========================================================================
    # WS-ADR-034-EXP3: Stories Container Tests (Second Container Type)
    # ==========================================================================
    
    @pytest.fixture
    def stories_block_component(self):
        """Create StoriesBlockV1 container component fixture."""
        comp = MagicMock()
        comp.component_id = "component:StoriesBlockV1:1.0.0"
        comp.schema_id = "schema:StoriesBlockV1"
        comp.generation_guidance = {
            "bullets": [
                "This is a render-only container. Do not generate new stories here.",
                "Render items in the order provided."
            ]
        }
        comp.view_bindings = {
            "web": {"fragment_id": "fragment:StoriesBlockV1:web:1.0.0"}
        }
        return comp
    
    @pytest.fixture
    def story_backlog_docdef(self):
        """Create story backlog test docdef."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:StoryBacklogTest:1.0.0"
        docdef.prompt_header = {"role": "Test", "constraints": []}
        docdef.sections = [{
            "section_id": "epic_stories",
            "title": "Stories",
            "order": 10,
            "component_id": "component:StoriesBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/stories",
            "repeat_over": "/epics",
            "context": {"epic_id": "/id", "epic_title": "/title"}
        }]
        return docdef
    
    @pytest.fixture
    def story_backlog_data(self):
        """Fixture with 2 epics and 5 stories split across them."""
        return {
            "epics": [
                {
                    "id": "E-001",
                    "title": "User Authentication",
                    "stories": [
                        {"id": "S-001", "epic_id": "E-001", "title": "Login form", "description": "Create login UI", "status": "done"},
                        {"id": "S-002", "epic_id": "E-001", "title": "Password reset", "description": "Implement reset flow", "status": "in_progress"},
                        {"id": "S-003", "epic_id": "E-001", "title": "Remember me", "description": "Add persistence option", "status": "draft"},
                    ]
                },
                {
                    "id": "E-002",
                    "title": "Dashboard",
                    "stories": [
                        {"id": "S-004", "epic_id": "E-002", "title": "Metrics overview", "description": "Show key metrics", "status": "ready"},
                        {"id": "S-005", "epic_id": "E-002", "title": "Activity feed", "description": "Recent activity stream", "status": "blocked"},
                    ]
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_exp3_stories_grouped_under_epics(
        self, story_backlog_docdef, stories_block_component, story_backlog_data
    ):
        """EXP3: Stories are correctly grouped under epics via container block."""
        mock_docdef_service = AsyncMock()
        mock_docdef_service.get.return_value = story_backlog_docdef
        
        mock_component_service = AsyncMock()
        mock_component_service.get.return_value = stories_block_component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        result = await builder.build("docdef:StoryBacklogTest:1.0.0", story_backlog_data)
        
        # Should have exactly 2 container blocks (one per epic)
        assert len(result.blocks) == 2
        
        # First block: Epic E-001 with 3 stories
        block_1 = result.blocks[0]
        assert block_1.type == "schema:StoriesBlockV1"
        assert block_1.context["epic_id"] == "E-001"
        assert block_1.context["epic_title"] == "User Authentication"
        assert len(block_1.data["items"]) == 3
        assert block_1.data["items"][0]["id"] == "S-001"
        
        # Second block: Epic E-002 with 2 stories
        block_2 = result.blocks[1]
        assert block_2.type == "schema:StoriesBlockV1"
        assert block_2.context["epic_id"] == "E-002"
        assert block_2.context["epic_title"] == "Dashboard"
        assert len(block_2.data["items"]) == 2
        assert block_2.data["items"][0]["id"] == "S-004"
    
    @pytest.mark.asyncio
    async def test_exp3_second_container_type_same_machinery(
        self, story_backlog_docdef, stories_block_component,
        epic_backlog_v1_1_docdef, open_questions_block_component, sample_epic_data
    ):
        """EXP3: StoriesBlockV1 uses same machinery as OpenQuestionsBlockV1."""
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        # Test OpenQuestionsBlockV1
        mock_docdef_service.get.return_value = epic_backlog_v1_1_docdef
        mock_component_service.get.return_value = open_questions_block_component
        
        oq_result = await builder.build("docdef:EpicBacklog:1.1.0", sample_epic_data)
        
        # Test StoriesBlockV1
        mock_docdef_service.get.return_value = story_backlog_docdef
        mock_component_service.get.return_value = stories_block_component
        
        story_data = {
            "epics": [{
                "id": "E-001",
                "title": "Test Epic",
                "stories": [
                    {"id": "S-001", "epic_id": "E-001", "title": "Story", "description": "Desc", "status": "draft"}
                ]
            }]
        }
        
        story_result = await builder.build("docdef:StoryBacklogTest:1.0.0", story_data)
        
        # Both should produce container blocks with same structure
        assert len(oq_result.blocks) >= 1
        assert len(story_result.blocks) == 1
        
        # Both have items array
        assert "items" in oq_result.blocks[0].data
        assert "items" in story_result.blocks[0].data
        
        # Both have context
        assert oq_result.blocks[0].context is not None
        assert story_result.blocks[0].context is not None

    @pytest.mark.asyncio
    async def test_existing_fragment_rendering_unchanged(self):
        """Test that existing fragment rendering mechanism is not affected."""
        # This test verifies the fragment registry still works with legacy IDs
        mock_db = AsyncMock()
        
        from app.api.services.fragment_registry_service import FragmentRegistryService
        from app.api.models.fragment_artifact import FragmentArtifact
        
        service = FragmentRegistryService(mock_db)
        
        # Mock existing fragment lookup
        existing_fragment = FragmentArtifact(
            id=uuid4(),
            fragment_id="OpenQuestionV1Fragment",
            schema_type_id="OpenQuestionV1",
            fragment_markup="<div>{{ block.data.text }}</div>", sha256="abc123", status="accepted", version="1.0",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_fragment
        mock_db.execute.return_value = mock_result
        
        # Legacy lookup still works
        result = await service.get_fragment("OpenQuestionV1Fragment")
        assert result is not None
        assert result.fragment_id == "OpenQuestionV1Fragment"
        
        # Canonical lookup via alias also works
        result = await service.resolve_fragment_id("fragment:OpenQuestionV1:web:1.0.0")
        assert result is not None








