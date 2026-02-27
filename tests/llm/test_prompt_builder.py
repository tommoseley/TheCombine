"""Tests for prompt builder."""


from app.llm.models import MessageRole
from app.llm.prompt_builder import (
    PromptBuilder,
    PromptContext,
    DEFAULT_ROLE_TEMPLATES,
)


class TestPromptBuilder:
    """Tests for PromptBuilder."""
    
    def test_build_system_prompt_for_role(self):
        """Builds system prompt for known role."""
        builder = PromptBuilder()
        
        prompt = builder.build_system_prompt("PM")
        
        assert "Product Manager" in prompt
        assert "requirements" in prompt.lower()
    
    def test_build_system_prompt_with_context(self):
        """Adds context to system prompt."""
        builder = PromptBuilder()
        context = PromptContext(
            workflow_name="Strategy",
            step_name="Discovery",
            scope_id="project-123",
        )
        
        prompt = builder.build_system_prompt("BA", context)
        
        assert "Business Analyst" in prompt
        assert "Strategy" in prompt
        assert "Discovery" in prompt
    
    def test_build_system_prompt_unknown_role(self):
        """Uses default for unknown role."""
        builder = PromptBuilder()
        
        prompt = builder.build_system_prompt("UnknownRole")
        
        assert "AI assistant" in prompt
    
    def test_build_user_prompt_simple(self):
        """Builds simple user prompt."""
        builder = PromptBuilder()
        
        prompt = builder.build_user_prompt("Analyze the requirements.")
        
        assert "Task" in prompt
        assert "Analyze the requirements" in prompt
    
    def test_build_user_prompt_with_documents(self):
        """Includes input documents in user prompt."""
        builder = PromptBuilder()
        docs = [
            {"type": "Requirements", "content": "Must support OAuth."},
            {"type": "Architecture", "content": "Use microservices."},
        ]
        
        prompt = builder.build_user_prompt("Review inputs.", docs)
        
        assert "Input Documents" in prompt
        assert "Requirements" in prompt
        assert "OAuth" in prompt
        assert "Architecture" in prompt
    
    def test_build_user_prompt_with_clarifications(self):
        """Includes clarification answers."""
        builder = PromptBuilder()
        context = PromptContext(
            workflow_name="Test",
            step_name="Step1",
            scope_id="scope",
            clarification_answers={"What is the budget?": "$10,000"},
        )
        
        prompt = builder.build_user_prompt("Do task.", context=context)
        
        assert "Clarifications" in prompt
        assert "budget" in prompt
        assert "$10,000" in prompt
    
    def test_build_user_prompt_with_remediation(self):
        """Includes remediation feedback."""
        builder = PromptBuilder()
        context = PromptContext(
            workflow_name="Test",
            step_name="Step1",
            scope_id="scope",
            remediation_feedback="Missing acceptance criteria.",
        )
        
        prompt = builder.build_user_prompt("Do task.", context=context)
        
        assert "Feedback" in prompt
        assert "Missing acceptance criteria" in prompt
    
    def test_build_messages(self):
        """Builds complete message list."""
        builder = PromptBuilder()
        
        system, messages = builder.build_messages(
            role="Developer",
            task_prompt="Write the code.",
            input_documents=[{"type": "Spec", "content": "Build a widget."}],
        )
        
        assert "Developer" in system
        assert len(messages) == 1
        assert messages[0].role == MessageRole.USER
        assert "widget" in messages[0].content
    
    def test_list_roles(self):
        """Lists available roles."""
        builder = PromptBuilder()
        
        roles = builder.list_roles()
        
        assert "PM" in roles
        assert "BA" in roles
        assert "Developer" in roles
        assert "QA" in roles
        assert "Architect" in roles
        assert "default" not in roles
    
    def test_custom_role_templates(self):
        """Uses custom role templates."""
        custom = {"CustomRole": "You are a custom assistant."}
        builder = PromptBuilder(role_templates=custom)
        
        prompt = builder.build_system_prompt("CustomRole")
        
        assert "custom assistant" in prompt
    
    def test_set_role_template(self):
        """Can set role template dynamically."""
        builder = PromptBuilder()
        builder.set_role_template("NewRole", "New role template.")
        
        prompt = builder.build_system_prompt("NewRole")
        
        assert "New role template" in prompt


class TestDefaultRoleTemplates:
    """Tests for default role templates."""
    
    def test_all_roles_have_json_instruction(self):
        """All roles instruct JSON output."""
        for role, template in DEFAULT_ROLE_TEMPLATES.items():
            assert "JSON" in template, f"{role} template missing JSON instruction"
    
    def test_pm_template(self):
        """PM template has expected content."""
        assert "Product Manager" in DEFAULT_ROLE_TEMPLATES["PM"]
        assert "requirements" in DEFAULT_ROLE_TEMPLATES["PM"].lower()
    
    def test_qa_template(self):
        """QA template has expected content."""
        assert "Quality Assurance" in DEFAULT_ROLE_TEMPLATES["QA"]
        assert "defects" in DEFAULT_ROLE_TEMPLATES["QA"].lower()
    
    def test_architect_template(self):
        """Architect template has expected content."""
        assert "Technical Architect" in DEFAULT_ROLE_TEMPLATES["Architect"]
        assert "architecture" in DEFAULT_ROLE_TEMPLATES["Architect"].lower()
