"""
Tests for RolePromptService.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from app.orchestrator_api.services.role_prompt_service import RolePromptService
from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository


class TestRolePromptService:
    """Test suite for RolePromptService."""
    
    def test_build_prompt_all_sections(self, db_session):
        """Test building prompt with all sections present."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        # Create prompt with all fields
        prompt = role_repo.create(
            role_name="test_role",
            version="1.0",
            starting_prompt="Welcome to the test",
            bootstrapper="You are a test role",
            instructions="Follow these test instructions",
            working_schema={"test": "schema"},
            set_active=True
        )
        
        # Build prompt with all context
        prompt_text, prompt_id = service.build_prompt(
            role_name="test_role",
            pipeline_id="test_pipeline",
            phase="test_phase",
            epic_context="Test epic description",
            pipeline_state={"state": "test"},
            artifacts={"previous": "artifact"}
        )
        
        # Verify all sections present
        assert "Welcome to the test" in prompt_text
        assert "# Role Bootstrap" in prompt_text
        assert "You are a test role" in prompt_text
        assert "# Instructions" in prompt_text
        assert "Follow these test instructions" in prompt_text
        assert "# Working Schema" in prompt_text
        assert '"test": "schema"' in prompt_text
        assert "# Epic Context" in prompt_text
        assert "Test epic description" in prompt_text
        assert "# Pipeline State" in prompt_text
        assert '"state": "test"' in prompt_text
        assert "# Previous Artifacts" in prompt_text
        assert '"previous": "artifact"' in prompt_text
        
        # Verify prompt_id returned
        assert prompt_id == prompt.id
    
    def test_build_prompt_minimal_sections(self, db_session):
        """Test building prompt with only required fields."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        # Create minimal prompt
        prompt = role_repo.create(
            role_name="minimal_role",
            version="1.0",
            bootstrapper="Minimal bootstrap",
            instructions="Minimal instructions",
            set_active=True
        )
        
        # Build prompt with no optional context
        prompt_text, prompt_id = service.build_prompt(
            role_name="minimal_role",
            pipeline_id="test_pipeline",
            phase="test_phase"
        )
        
        # Verify only required sections present
        assert "# Role Bootstrap" in prompt_text
        assert "Minimal bootstrap" in prompt_text
        assert "# Instructions" in prompt_text
        assert "Minimal instructions" in prompt_text
        
        # Verify optional sections absent
        assert "# Working Schema" not in prompt_text
        assert "# Epic Context" not in prompt_text
        assert "# Pipeline State" not in prompt_text
        assert "# Previous Artifacts" not in prompt_text
    
    def test_build_prompt_no_active_prompt(self, db_session):
        """Test building prompt for role with no active prompt raises ValueError."""
        service = RolePromptService()
        
        with pytest.raises(ValueError) as exc_info:
            service.build_prompt(
                role_name="nonexistent_role",
                pipeline_id="test_pipeline",
                phase="test_phase"
            )
        
        assert "No active prompt found for role: nonexistent_role" in str(exc_info.value)
    
    def test_build_prompt_stale_warning(self, db_session, caplog):
        """Test that stale prompt (>365 days) triggers warning."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        # Create old prompt
        prompt = role_repo.create(
            role_name="old_test",
            version="1.0",
            bootstrapper="Old bootstrap",
            instructions="Old instructions",
            set_active=True
        )
        
        # Manually set created_at to >365 days ago (directly in database)
        from database import SessionLocal
        session = SessionLocal()
        try:
            db_prompt = session.query(type(prompt)).filter_by(id=prompt.id).first()
            db_prompt.created_at = datetime.now(timezone.utc) - timedelta(days=400)
            session.commit()
        finally:
            session.close()
        
        # Build prompt (should trigger warning)
        with caplog.at_level("WARNING"):
            prompt_text, prompt_id = service.build_prompt(
                role_name="old_test",
                pipeline_id="test_pipeline",
                phase="test_phase"
            )
        
        # Verify warning logged
        assert any("days old" in record.message for record in caplog.records)
        assert any("old_test" in record.message for record in caplog.records)
    
    def test_build_prompt_recent_no_warning(self, db_session, caplog):
        """Test that recent prompt (<365 days) does not trigger warning."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        # Create recent prompt
        prompt = role_repo.create(
            role_name="recent_test",
            version="1.0",
            bootstrapper="Recent bootstrap",
            instructions="Recent instructions",
            set_active=True
        )
        
        # Build prompt
        with caplog.at_level("WARNING"):
            prompt_text, prompt_id = service.build_prompt(
                role_name="recent_test",
                pipeline_id="test_pipeline",
                phase="test_phase"
            )
        
        # Verify no warning logged
        assert not any("days old" in record.message for record in caplog.records)
    
    def test_build_prompt_empty_artifacts_omitted(self, db_session):
        """Test that empty artifacts dict is omitted from prompt."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        prompt = role_repo.create(
            role_name="test_role",
            version="1.0",
            bootstrapper="Bootstrap",
            instructions="Instructions",
            set_active=True
        )
        
        # Build prompt with empty artifacts dict
        prompt_text, prompt_id = service.build_prompt(
            role_name="test_role",
            pipeline_id="test_pipeline",
            phase="test_phase",
            artifacts={}  # Empty dict
        )
        
        # Verify artifacts section omitted
        assert "# Previous Artifacts" not in prompt_text
    
    def test_build_prompt_section_order(self, db_session):
        """Test that sections appear in correct order."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        prompt = role_repo.create(
            role_name="test_role",
            version="1.0",
            starting_prompt="Starting",
            bootstrapper="Bootstrap",
            instructions="Instructions",
            working_schema={"schema": "test"},
            set_active=True
        )
        
        prompt_text, _ = service.build_prompt(
            role_name="test_role",
            pipeline_id="test_pipeline",
            phase="test_phase",
            epic_context="Epic",
            pipeline_state={"state": "test"},
            artifacts={"artifact": "test"}
        )
        
        # Find positions of each section
        pos_starting = prompt_text.find("Starting")
        pos_bootstrap = prompt_text.find("# Role Bootstrap")
        pos_instructions = prompt_text.find("# Instructions")
        pos_schema = prompt_text.find("# Working Schema")
        pos_epic = prompt_text.find("# Epic Context")
        pos_state = prompt_text.find("# Pipeline State")
        pos_artifacts = prompt_text.find("# Previous Artifacts")
        
        # Verify order
        assert pos_starting < pos_bootstrap < pos_instructions < pos_schema < pos_epic < pos_state < pos_artifacts
    
    def test_build_prompt_json_format_valid(self, db_session):
        """Test that JSON sections in prompt are valid JSON."""
        role_repo = RolePromptRepository()
        service = RolePromptService()
        
        prompt = role_repo.create(
            role_name="test_role",
            version="1.0",
            bootstrapper="Bootstrap",
            instructions="Instructions",
            working_schema={"test": "schema"},
            set_active=True
        )
        
        prompt_text, _ = service.build_prompt(
            role_name="test_role",
            pipeline_id="test_pipeline",
            phase="test_phase",
            pipeline_state={"state": "test", "value": 123},
            artifacts={"artifact": {"nested": "data"}}
        )
        
        # Extract JSON blocks and verify they're valid
        import re
        json_blocks = re.findall(r'```json\n(.*?)\n```', prompt_text, re.DOTALL)
        
        assert len(json_blocks) >= 2  # At least working_schema and pipeline_state
        
        for block in json_blocks:
            # Should be parseable JSON
            parsed = json.loads(block)
            assert isinstance(parsed, (dict, list))