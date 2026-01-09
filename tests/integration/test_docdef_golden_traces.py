"""
Golden-trace tests for DocDefs.

These tests assert stable UX semantics:
- Block counts
- Block types  
- Presence of detail_ref
- Absence of excluded fields

Per docs/governance/SUMMARY_VIEW_CONTRACT.md:
Summary views must include exclude_fields and must not carry typed arrays.

These are "don't regress UX semantics" alarms.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.services.render_model_builder import RenderModelBuilder
from app.api.models.document_definition import DocumentDefinition
from app.api.models.component_artifact import ComponentArtifact


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_docdef_service():
    return AsyncMock()


@pytest.fixture
def mock_component_service():
    return AsyncMock()


def make_docdef(docdef_id: str, sections: list) -> DocumentDefinition:
    """Helper to create DocumentDefinition."""
    return DocumentDefinition(
        id=uuid4(),
        document_def_id=docdef_id,
        document_schema_id=None,
        prompt_header={},
        sections=sections,
        status="accepted",
    )


def make_component(component_id: str, schema_id: str) -> ComponentArtifact:
    """Helper to create ComponentArtifact."""
    return ComponentArtifact(
        id=uuid4(),
        component_id=component_id,
        schema_id=schema_id,
        generation_guidance={},
        view_bindings={},
        status="accepted",
    )


# =============================================================================
# EpicBacklogView Golden Trace
# =============================================================================

class TestEpicBacklogViewGoldenTrace:
    """Golden-trace tests for docdef:EpicBacklogView:1.0.0"""
    
    EXCLUDED_FIELDS = ["risks", "open_questions", "requirements", "acceptance_criteria"]
    
    @pytest.fixture
    def sample_backlog_data(self):
        return {
            "epics": [
                {
                    "epic_id": "AUTH-100",
                    "title": "User Authentication",
                    "vision": "Enable secure auth.",
                    "phase": "MVP",
                    "risks": [{"id": "R-001", "description": "Risk", "likelihood": "high"}],
                    "open_questions": [{"id": "Q-001", "text": "Question"}],
                    "requirements": ["Req 1", "Req 2"],
                    "acceptance_criteria": ["AC 1"],
                },
                {
                    "epic_id": "DASH-200",
                    "title": "Dashboard",
                    "vision": "Insights at a glance.",
                    "phase": "Later",
                    "risks": [],
                    "open_questions": [],
                    "requirements": [],
                    "acceptance_criteria": [],
                },
            ]
        }
    
    @pytest.fixture
    def backlog_docdef_sections(self):
        return [
            {
                "section_id": "epic_summaries",
                "title": "Epics",
                "order": 10,
                "component_id": "component:EpicSummaryBlockV1:1.0.0",
                "shape": "container",
                "repeat_over": "/epics",
                "source_pointer": "/",
                "exclude_fields": ["risks", "open_questions", "requirements", "acceptance_criteria"],
                "context": {"epic_id": "/epic_id", "epic_title": "/title"},
                "derived_fields": [
                    {"field": "risk_level", "function": "risk_level", "source": "/risks"},
                ],
                "detail_ref_template": {
                    "document_type": "EpicDetailView",
                    "params": {"epic_id": "/epic_id"}
                },
            },
        ]
    
    @pytest.mark.asyncio
    async def test_block_count_matches_epic_count(
        self, mock_docdef_service, mock_component_service, sample_backlog_data, backlog_docdef_sections
    ):
        """INVARIANT: One block per epic."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:EpicSummaryBlockV1:1.0.0", "schema:EpicSummaryBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicBacklogView:1.0.0", sample_backlog_data)
        
        assert len(result.blocks) == 2  # 2 epics = 2 blocks
    
    @pytest.mark.asyncio
    async def test_block_types_are_epic_summary(
        self, mock_docdef_service, mock_component_service, sample_backlog_data, backlog_docdef_sections
    ):
        """INVARIANT: All blocks are EpicSummaryBlockV1."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:EpicSummaryBlockV1:1.0.0", "schema:EpicSummaryBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicBacklogView:1.0.0", sample_backlog_data)
        
        for block in result.blocks:
            assert block.type == "schema:EpicSummaryBlockV1"
    
    @pytest.mark.asyncio
    async def test_detail_ref_present_in_all_blocks(
        self, mock_docdef_service, mock_component_service, sample_backlog_data, backlog_docdef_sections
    ):
        """INVARIANT: Every block has detail_ref."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:EpicSummaryBlockV1:1.0.0", "schema:EpicSummaryBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicBacklogView:1.0.0", sample_backlog_data)
        
        for block in result.blocks:
            assert "detail_ref" in block.data
            assert block.data["detail_ref"]["document_type"] == "EpicDetailView"
            assert "epic_id" in block.data["detail_ref"]["params"]
    
    @pytest.mark.asyncio
    async def test_excluded_fields_not_in_block_data(
        self, mock_docdef_service, mock_component_service, sample_backlog_data, backlog_docdef_sections
    ):
        """INVARIANT: Excluded fields stripped from summary blocks."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:EpicSummaryBlockV1:1.0.0", "schema:EpicSummaryBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicBacklogView:1.0.0", sample_backlog_data)
        
        for block in result.blocks:
            for excluded_field in self.EXCLUDED_FIELDS:
                assert excluded_field not in block.data, f"{excluded_field} should be excluded"
    
    @pytest.mark.asyncio
    async def test_derived_risk_level_present(
        self, mock_docdef_service, mock_component_service, sample_backlog_data, backlog_docdef_sections
    ):
        """INVARIANT: risk_level is derived, not raw risks array."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:EpicSummaryBlockV1:1.0.0", "schema:EpicSummaryBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicBacklogView:1.0.0", sample_backlog_data)
        
        # First epic has high risk
        assert result.blocks[0].data["risk_level"] == "high"
        # Second epic has no risks
        assert result.blocks[1].data["risk_level"] == "low"


# =============================================================================
# EpicDetailView Golden Trace
# =============================================================================

class TestEpicDetailViewGoldenTrace:
    """Golden-trace tests for docdef:EpicDetailView:1.0.0"""
    
    @pytest.fixture
    def sample_epic_data(self):
        return {
            "vision": "Enable secure auth.",
            "problem": "No auth exists.",
            "business_goals": ["Goal 1", "Goal 2"],
            "in_scope": ["Scope 1"],
            "out_of_scope": ["Out 1"],
            "requirements": ["Req 1"],
            "acceptance_criteria": ["AC 1"],
            "risks": [{"id": "R-001", "description": "Risk", "likelihood": "high", "impact": "High"}],
            "open_questions": [{"id": "Q-001", "text": "Question", "blocking": True, "why_it_matters": "Reason"}],
            "dependencies": [{"depends_on_id": "AUTH-100", "reason": "Needed", "blocking": True}],
        }
    
    @pytest.fixture
    def detail_docdef_sections(self):
        return [
            {"section_id": "vision", "order": 10, "component_id": "component:ParagraphBlockV1:1.0.0", "shape": "single", "source_pointer": "/vision", "context": {"title": "Vision"}},
            {"section_id": "problem", "order": 20, "component_id": "component:ParagraphBlockV1:1.0.0", "shape": "single", "source_pointer": "/problem", "context": {"title": "Problem"}},
            {"section_id": "business_goals", "order": 30, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/business_goals", "context": {"title": "Goals"}},
            {"section_id": "in_scope", "order": 40, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/in_scope", "context": {"title": "In Scope"}},
            {"section_id": "out_of_scope", "order": 50, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/out_of_scope", "context": {"title": "Out of Scope"}},
            {"section_id": "requirements", "order": 60, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/requirements", "context": {"title": "Requirements"}},
            {"section_id": "acceptance_criteria", "order": 70, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/acceptance_criteria", "context": {"title": "AC"}},
            {"section_id": "risks", "order": 80, "component_id": "component:RisksBlockV1:1.0.0", "shape": "container", "source_pointer": "/risks", "context": {"title": "Risks"}},
            {"section_id": "open_questions", "order": 90, "component_id": "component:OpenQuestionsBlockV1:1.0.0", "shape": "container", "source_pointer": "/open_questions", "context": {"title": "Questions"}},
            {"section_id": "dependencies", "order": 100, "component_id": "component:DependenciesBlockV1:1.0.0", "shape": "container", "source_pointer": "/dependencies", "context": {"title": "Dependencies"}},
        ]
    
    @pytest.mark.asyncio
    async def test_block_count_matches_section_count(
        self, mock_docdef_service, mock_component_service, sample_epic_data, detail_docdef_sections
    ):
        """INVARIANT: One block per section with data."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicDetailView:1.0.0", detail_docdef_sections
        )
        
        # Mock component returns based on component_id
        async def get_component(component_id):
            schema_map = {
                "component:ParagraphBlockV1:1.0.0": "schema:ParagraphBlockV1",
                "component:StringListBlockV1:1.0.0": "schema:StringListBlockV1",
                "component:RisksBlockV1:1.0.0": "schema:RisksBlockV1",
                "component:OpenQuestionsBlockV1:1.0.0": "schema:OpenQuestionsBlockV1",
                "component:DependenciesBlockV1:1.0.0": "schema:DependenciesBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id, "schema:Unknown"))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicDetailView:1.0.0", sample_epic_data)
        
        # 10 sections, all have data
        assert len(result.blocks) == 10
    
    @pytest.mark.asyncio
    async def test_block_types_match_components(
        self, mock_docdef_service, mock_component_service, sample_epic_data, detail_docdef_sections
    ):
        """INVARIANT: Block types match expected schema types."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:EpicDetailView:1.0.0", detail_docdef_sections
        )
        
        async def get_component(component_id):
            schema_map = {
                "component:ParagraphBlockV1:1.0.0": "schema:ParagraphBlockV1",
                "component:StringListBlockV1:1.0.0": "schema:StringListBlockV1",
                "component:RisksBlockV1:1.0.0": "schema:RisksBlockV1",
                "component:OpenQuestionsBlockV1:1.0.0": "schema:OpenQuestionsBlockV1",
                "component:DependenciesBlockV1:1.0.0": "schema:DependenciesBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id, "schema:Unknown"))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:EpicDetailView:1.0.0", sample_epic_data)
        
        expected_types = {
            "schema:ParagraphBlockV1",
            "schema:StringListBlockV1",
            "schema:RisksBlockV1",
            "schema:OpenQuestionsBlockV1",
            "schema:DependenciesBlockV1",
        }
        actual_types = {block.type for block in result.blocks}
        
        assert actual_types == expected_types


# =============================================================================
# ProjectDiscovery Golden Trace
# =============================================================================

class TestProjectDiscoveryGoldenTrace:
    """Golden-trace tests for docdef:ProjectDiscovery:1.0.0"""
    
    @pytest.fixture
    def sample_discovery_data(self):
        return {
            "preliminary_summary": {
                "problem_understanding": "Test problem",
                "architectural_intent": "Test intent",
                "scope_pressure_points": "Test pressure",
            },
            "known_constraints": ["Constraint 1"],
            "assumptions": ["Assumption 1"],
            "identified_risks": [{"id": "R-001", "description": "Risk", "likelihood": "medium", "impact_on_planning": "Medium"}],
            "mvp_guardrails": ["Guardrail 1"],
            "recommendations_for_pm": ["Rec 1"],
        }
    
    @pytest.fixture
    def discovery_docdef_sections(self):
        return [
            {"section_id": "summary", "order": 10, "component_id": "component:SummaryBlockV1:1.0.0", "shape": "single", "source_pointer": "/preliminary_summary", "context": {}},
            {"section_id": "constraints", "order": 20, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/known_constraints", "context": {"title": "Constraints"}},
            {"section_id": "assumptions", "order": 30, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/assumptions", "context": {"title": "Assumptions"}},
            {"section_id": "risks", "order": 40, "component_id": "component:RisksBlockV1:1.0.0", "shape": "container", "source_pointer": "/identified_risks", "context": {"title": "Risks"}},
            {"section_id": "guardrails", "order": 50, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/mvp_guardrails", "context": {"title": "Guardrails"}},
            {"section_id": "recommendations", "order": 60, "component_id": "component:StringListBlockV1:1.0.0", "shape": "container", "source_pointer": "/recommendations_for_pm", "context": {"title": "Recommendations"}},
        ]
    
    @pytest.mark.asyncio
    async def test_block_count(
        self, mock_docdef_service, mock_component_service, sample_discovery_data, discovery_docdef_sections
    ):
        """INVARIANT: 6 blocks for complete discovery."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:ProjectDiscovery:1.0.0", discovery_docdef_sections
        )
        
        async def get_component(component_id):
            schema_map = {
                "component:SummaryBlockV1:1.0.0": "schema:SummaryBlockV1",
                "component:StringListBlockV1:1.0.0": "schema:StringListBlockV1",
                "component:RisksBlockV1:1.0.0": "schema:RisksBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id, "schema:Unknown"))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:ProjectDiscovery:1.0.0", sample_discovery_data)
        
        assert len(result.blocks) == 6

# =============================================================================
# StorySummaryView Golden Trace
# =============================================================================

class TestStorySummaryViewGoldenTrace:
    """Golden-trace tests for docdef:StorySummaryView:1.0.0"""
    
    FORBIDDEN_FIELDS = [
        "acceptance_criteria", "in_scope", "out_of_scope",
        "dependencies", "open_questions", "implementation_notes"
    ]
    
    @pytest.fixture
    def summary_docdef_sections(self):
        return [
            {
                "section_id": "story_intent",
                "order": 10,
                "component_id": "component:ParagraphBlockV1:1.0.0",
                "shape": "single",
                "source_pointer": "/intent",
                "context": {"title": ""},
                "detail_ref_template": {
                    "document_type": "StoryDetailView",
                    "params": {"story_id": "/story_id"}
                },
            },
            {
                "section_id": "phase",
                "order": 20,
                "component_id": "component:IndicatorBlockV1:1.0.0",
                "shape": "single",
                "source_pointer": "/phase",
                "context": {"title": "Phase"},
            },
            {
                "section_id": "risk_level",
                "order": 30,
                "component_id": "component:IndicatorBlockV1:1.0.0",
                "shape": "single",
                "derived_from": {
                    "function": "risk_level",
                    "source": "/risks",
                    "omit_when_source_empty": True
                },
                "context": {"title": "Risk"},
            },
        ]
    
    @pytest.mark.asyncio
    async def test_with_risks_produces_3_blocks(
        self, mock_docdef_service, mock_component_service, summary_docdef_sections
    ):
        """INVARIANT: Story with risks → 3 blocks."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StorySummaryView:1.0.0", summary_docdef_sections
        )
        
        async def get_component(component_id):
            schema_map = {
                "component:ParagraphBlockV1:1.0.0": "schema:ParagraphBlockV1",
                "component:IndicatorBlockV1:1.0.0": "schema:IndicatorBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StorySummaryView:1.0.0", {
            "story_id": "AUTH-101",
            "intent": "User can register.",
            "phase": "MVP",
            "risks": [{"id": "R-001", "description": "Risk", "likelihood": "high"}]
        })
        
        assert len(result.blocks) == 3
        assert result.blocks[0].type == "schema:ParagraphBlockV1"
        assert result.blocks[1].type == "schema:IndicatorBlockV1"
        assert result.blocks[2].type == "schema:IndicatorBlockV1"
        assert result.blocks[2].data["value"] == "high"
    
    @pytest.mark.asyncio
    async def test_without_risks_produces_2_blocks(
        self, mock_docdef_service, mock_component_service, summary_docdef_sections
    ):
        """INVARIANT: Story without risks → 2 blocks (risk_level omitted)."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StorySummaryView:1.0.0", summary_docdef_sections
        )
        
        async def get_component(component_id):
            schema_map = {
                "component:ParagraphBlockV1:1.0.0": "schema:ParagraphBlockV1",
                "component:IndicatorBlockV1:1.0.0": "schema:IndicatorBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StorySummaryView:1.0.0", {
            "story_id": "AUTH-102",
            "intent": "User can reset password.",
            "phase": "Later",
            "risks": []
        })
        
        assert len(result.blocks) == 2
        assert result.blocks[0].type == "schema:ParagraphBlockV1"
        assert result.blocks[1].type == "schema:IndicatorBlockV1"
        # No risk_level block
        block_keys = [b.key for b in result.blocks]
        assert "risk_level:derived" not in block_keys
    
    @pytest.mark.asyncio
    async def test_detail_ref_present(
        self, mock_docdef_service, mock_component_service, summary_docdef_sections
    ):
        """INVARIANT: detail_ref to StoryDetailView required."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StorySummaryView:1.0.0", summary_docdef_sections
        )
        
        async def get_component(component_id):
            schema_map = {
                "component:ParagraphBlockV1:1.0.0": "schema:ParagraphBlockV1",
                "component:IndicatorBlockV1:1.0.0": "schema:IndicatorBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StorySummaryView:1.0.0", {
            "story_id": "AUTH-101",
            "intent": "Test",
            "phase": "MVP",
            "risks": []
        })
        
        intent_block = result.blocks[0]
        assert "detail_ref" in intent_block.data
        assert intent_block.data["detail_ref"]["document_type"] == "StoryDetailView"
        assert intent_block.data["detail_ref"]["params"]["story_id"] == "AUTH-101"
    
    @pytest.mark.asyncio
    async def test_no_forbidden_fields_in_output(
        self, mock_docdef_service, mock_component_service, summary_docdef_sections
    ):
        """INVARIANT: Forbidden list fields never appear in summary."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StorySummaryView:1.0.0", summary_docdef_sections
        )
        
        async def get_component(component_id):
            schema_map = {
                "component:ParagraphBlockV1:1.0.0": "schema:ParagraphBlockV1",
                "component:IndicatorBlockV1:1.0.0": "schema:IndicatorBlockV1",
            }
            return make_component(component_id, schema_map.get(component_id))
        
        mock_component_service.get.side_effect = get_component
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        
        # Input with all forbidden fields present
        result = await builder.build("docdef:StorySummaryView:1.0.0", {
            "story_id": "AUTH-101",
            "intent": "Test",
            "phase": "MVP",
            "risks": [],
            "acceptance_criteria": ["AC1", "AC2"],
            "in_scope": ["Scope1"],
            "out_of_scope": ["Out1"],
            "dependencies": [{"depends_on_id": "X"}],
            "open_questions": [{"id": "Q1"}],
            "implementation_notes": ["Note1"],
        })
        
        # None of the forbidden fields should appear
        block_keys = [b.key for b in result.blocks]
        for field in self.FORBIDDEN_FIELDS:
            assert not any(field in key for key in block_keys), f"{field} should not appear"


# =============================================================================
# StoryBacklogView Golden Trace
# =============================================================================

class TestStoryBacklogViewGoldenTrace:
    """Golden-trace tests for docdef:StoryBacklogView:1.0.0"""
    
    FORBIDDEN_STORY_FIELDS = [
        "acceptance_criteria", "in_scope", "out_of_scope",
        "dependencies", "open_questions", "implementation_notes", "risks"
    ]
    
    @pytest.fixture
    def backlog_docdef_sections(self):
        return [
            {
                "section_id": "epic_stories",
                "order": 10,
                "component_id": "component:StoriesBlockV1:1.0.0",
                "shape": "container",
                "repeat_over": "/epics",
                "source_pointer": "/stories",
                "context": {"epic_id": "/id", "epic_title": "/title"},
            },
        ]
    
    @pytest.mark.asyncio
    async def test_grouping_2_epics_3_stories(
        self, mock_docdef_service, mock_component_service, backlog_docdef_sections
    ):
        """INVARIANT: 2 epics with 2+1 stories → 2 container blocks."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StoryBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:StoriesBlockV1:1.0.0", "schema:StoriesBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StoryBacklogView:1.0.0", {
            "epics": [
                {
                    "id": "AUTH-100",
                    "title": "Authentication",
                    "stories": [
                        {"story_id": "S1", "title": "T1", "intent": "I1", "phase": "mvp",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S1"}}},
                        {"story_id": "S2", "title": "T2", "intent": "I2", "phase": "mvp", "risk_level": "high",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S2"}}},
                    ]
                },
                {
                    "id": "DASH-200",
                    "title": "Dashboard",
                    "stories": [
                        {"story_id": "S3", "title": "T3", "intent": "I3", "phase": "later",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S3"}}},
                    ]
                }
            ]
        })
        
        assert len(result.blocks) == 2
        assert len(result.blocks[0].data["items"]) == 2
        assert len(result.blocks[1].data["items"]) == 1
        assert result.blocks[0].context["epic_id"] == "AUTH-100"
        assert result.blocks[1].context["epic_id"] == "DASH-200"
    
    @pytest.mark.asyncio
    async def test_empty_epic_omitted(
        self, mock_docdef_service, mock_component_service, backlog_docdef_sections
    ):
        """INVARIANT: Epic with no stories → block omitted."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StoryBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:StoriesBlockV1:1.0.0", "schema:StoriesBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StoryBacklogView:1.0.0", {
            "epics": [
                {
                    "id": "AUTH-100",
                    "title": "Authentication",
                    "stories": [
                        {"story_id": "S1", "title": "T1", "intent": "I1", "phase": "mvp",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S1"}}},
                    ]
                },
                {
                    "id": "EMPTY-300",
                    "title": "Empty Epic",
                    "stories": []
                }
            ]
        })
        
        assert len(result.blocks) == 1
        assert result.blocks[0].context["epic_id"] == "AUTH-100"
    
    @pytest.mark.asyncio
    async def test_risk_level_absent_when_not_provided(
        self, mock_docdef_service, mock_component_service, backlog_docdef_sections
    ):
        """INVARIANT: Story without risk_level → field absent (not 'low')."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StoryBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:StoriesBlockV1:1.0.0", "schema:StoriesBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StoryBacklogView:1.0.0", {
            "epics": [
                {
                    "id": "AUTH-100",
                    "title": "Authentication",
                    "stories": [
                        {"story_id": "S1", "title": "T1", "intent": "I1", "phase": "mvp",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S1"}}},
                    ]
                }
            ]
        })
        
        story = result.blocks[0].data["items"][0]
        assert "risk_level" not in story
    
    @pytest.mark.asyncio
    async def test_detail_ref_present_on_all_stories(
        self, mock_docdef_service, mock_component_service, backlog_docdef_sections
    ):
        """INVARIANT: Every story has detail_ref to StoryDetailView."""
        mock_docdef_service.get.return_value = make_docdef(
            "docdef:StoryBacklogView:1.0.0", backlog_docdef_sections
        )
        mock_component_service.get.return_value = make_component(
            "component:StoriesBlockV1:1.0.0", "schema:StoriesBlockV1"
        )
        
        builder = RenderModelBuilder(mock_docdef_service, mock_component_service)
        result = await builder.build("docdef:StoryBacklogView:1.0.0", {
            "epics": [
                {
                    "id": "AUTH-100",
                    "title": "Authentication",
                    "stories": [
                        {"story_id": "S1", "title": "T1", "intent": "I1", "phase": "mvp",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S1"}}},
                        {"story_id": "S2", "title": "T2", "intent": "I2", "phase": "mvp",
                         "detail_ref": {"document_type": "StoryDetailView", "params": {"story_id": "S2"}}},
                    ]
                }
            ]
        })
        
        for story in result.blocks[0].data["items"]:
            assert "detail_ref" in story
            assert story["detail_ref"]["document_type"] == "StoryDetailView"
