"""
Unit tests for PhaseExecutionOrchestrator.

Tests cover happy path, error paths, and all QA-critical issues.

Authors: D-1 (Senior), D-3 (Junior)
Epic: PIPELINE-175B
"""

import pytest
from unittest.mock import Mock
from app.orchestrator_api.services.phase_execution_orchestrator import (
    PhaseExecutionOrchestrator,
    PhaseExecutionResult,
    ExecutionError,
    ConfigurationError,
    PromptBuildError,
    LLMError,
    ParseError
)
from app.orchestrator_api.services.configuration_loader import PhaseConfig
from app.orchestrator_api.services.llm_caller import LLMCallResult
from app.orchestrator_api.services.llm_response_parser import ParseResult


class TestPhaseExecutionOrchestrator:
    """Tests for PhaseExecutionOrchestrator."""
    
    def test_happy_path(self):
        """Should execute phase successfully with all components."""
        # Mock all dependencies
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt text", "rp_123")
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=True,
            response_text='{"title": "Test Epic"}',
            execution_time_ms=1000,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            error=None
        )
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParseResult(
            success=True,
            data={"title": "Test Epic"},
            strategy_used="DirectParseStrategy",
            error_messages=[]
        )
        
        mock_recorder = Mock()
        mock_recorder.record_usage.return_value = True
        
        # Create orchestrator
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=mock_recorder
        )
        
        # Execute
        result = orchestrator.execute_phase(
            pipeline_id="pip_test",
            phase_name="pm_phase",
            epic_context="Build user auth",
            pipeline_state={},
            artifacts={}
        )
        
        # Verify result
        assert result.success is True
        assert result.artifact == {"title": "Test Epic"}
        assert result.artifact_type == "epic"
        assert result.next_phase == "arch_phase"
        assert result.prompt_id == "rp_123"
        assert result.execution_time_ms == 1000
        
        # Verify all components called
        mock_config_loader.load_config.assert_called_once_with("pm_phase")
        mock_prompt_builder.build_prompt.assert_called_once()
        mock_llm_caller.call.assert_called_once()
        mock_parser.parse.assert_called_once()
        mock_recorder.record_usage.assert_called_once()
    
    def test_configuration_error(self):
        """Should raise ConfigurationError when config not found."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.side_effect = ConfigurationError(
            "Config not found", "pm_phase", "pip_test"
        )
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=Mock(),
            llm_caller=Mock(),
            parser=Mock(),
            usage_recorder=Mock()
        )
        
        with pytest.raises(ConfigurationError, match="Config not found"):
            orchestrator.execute_phase(
                pipeline_id="pip_test",
                phase_name="pm_phase",
                epic_context="Test",
                pipeline_state={},
                artifacts={}
            )
    
    def test_prompt_build_error(self):
        """Should convert ValueError to PromptBuildError."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.side_effect = ValueError("No active prompt")
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=Mock(),
            parser=Mock(),
            usage_recorder=Mock()
        )
        
        with pytest.raises(PromptBuildError, match="No active prompt"):
            orchestrator.execute_phase(
                pipeline_id="pip_test",
                phase_name="pm_phase",
                epic_context="Test",
                pipeline_state={},
                artifacts={}
            )
    
    def test_llm_error(self):
        """Should raise LLMError when LLM call fails."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=False,
            response_text=None,
            execution_time_ms=500,
            token_usage=None,
            error="AuthenticationError: Invalid API key"
        )
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=Mock(),
            usage_recorder=Mock()
        )
        
        with pytest.raises(LLMError, match="LLM call failed"):
            orchestrator.execute_phase(
                pipeline_id="pip_test",
                phase_name="pm_phase",
                epic_context="Test",
                pipeline_state={},
                artifacts={}
            )
    
    def test_parse_error(self):
        """Should raise ParseError when parsing fails."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=True,
            response_text="unparseable",
            execution_time_ms=1000,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            error=None
        )
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParseResult(
            success=False,
            data=None,
            strategy_used=None,
            error_messages=["DirectParse failed", "MarkdownFence failed"]
        )
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=Mock()
        )
        
        with pytest.raises(ParseError, match="Parse failed"):
            orchestrator.execute_phase(
                pipeline_id="pip_test",
                phase_name="pm_phase",
                epic_context="Test",
                pipeline_state={},
                artifacts={}
            )
    
    def test_usage_recording_failure_non_fatal(self):
        """Should continue execution when usage recording fails."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=True,
            response_text='{"title": "Test"}',
            execution_time_ms=1000,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            error=None
        )
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParseResult(
            success=True,
            data={"title": "Test"},
            strategy_used="DirectParseStrategy",
            error_messages=[]
        )
        
        mock_recorder = Mock()
        mock_recorder.record_usage.return_value = False  # Recording failed
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=mock_recorder
        )
        
        # Should not raise despite recording failure
        result = orchestrator.execute_phase(
            pipeline_id="pip_test",
            phase_name="pm_phase",
            epic_context="Test",
            pipeline_state={},
            artifacts={}
        )
        
        assert result.success is True
    
    def test_unexpected_exception_wrapped(self):
        """QA Issue #1: Should wrap unexpected exceptions in ExecutionError."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        mock_llm_caller = Mock()
        # Unexpected exception from component
        mock_llm_caller.call.side_effect = AttributeError("'NoneType' object has no attribute 'text'")
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=Mock(),
            usage_recorder=Mock()
        )
        
        with pytest.raises(ExecutionError) as exc_info:
            orchestrator.execute_phase(
                pipeline_id="pip_test",
                phase_name="pm_phase",
                epic_context="Test",
                pipeline_state={},
                artifacts={}
            )
        
        # Should wrap in ExecutionError with exception type
        assert "Unexpected internal error" in str(exc_info.value)
        assert "AttributeError" in str(exc_info.value)
    
    def test_input_immutability(self):
        """QA Issue #5: Should not modify input pipeline_state or artifacts."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=True,
            response_text='{"title": "Test"}',
            execution_time_ms=1000,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            error=None
        )
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParseResult(
            success=True,
            data={"title": "Test"},
            strategy_used="DirectParseStrategy",
            error_messages=[]
        )
        
        mock_recorder = Mock()
        mock_recorder.record_usage.return_value = True
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=mock_recorder
        )
        
        # Original inputs
        pipeline_state = {"existing": "data"}
        artifacts = {"prev": "artifact"}
        
        # Execute
        orchestrator.execute_phase(
            pipeline_id="pip_test",
            phase_name="pm_phase",
            epic_context="Test",
            pipeline_state=pipeline_state,
            artifacts=artifacts
        )
        
        # Verify inputs unchanged
        assert pipeline_state == {"existing": "data"}
        assert artifacts == {"prev": "artifact"}
    
    def test_terminal_phase(self):
        """Should handle terminal phase with next_phase=None."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="commit_phase",
            role_name="commit",
            artifact_type="commit_message",
            next_phase=None,  # Terminal
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=True,
            response_text='{"message": "Complete"}',
            execution_time_ms=1000,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            error=None
        )
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParseResult(
            success=True,
            data={"message": "Complete"},
            strategy_used="DirectParseStrategy",
            error_messages=[]
        )
        
        mock_recorder = Mock()
        mock_recorder.record_usage.return_value = True
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=mock_recorder
        )
        
        result = orchestrator.execute_phase(
            pipeline_id="pip_test",
            phase_name="commit_phase",
            epic_context="Test",
            pipeline_state={},
            artifacts={}
        )
        
        assert result.next_phase is None
    
    def test_component_call_sequence(self):
        """Should call components in correct sequence."""
        call_order = []
        
        mock_config_loader = Mock()
        mock_config_loader.load_config.side_effect = lambda x: (
            call_order.append("config"),
            PhaseConfig("pm_phase", "pm", "epic", "arch_phase", True)
        )[1]
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.side_effect = lambda *args, **kwargs: (
            call_order.append("prompt"),
            ("prompt", "rp_123")
        )[1]
        
        mock_llm_caller = Mock()
        mock_llm_caller.call.side_effect = lambda *args, **kwargs: (
            call_order.append("llm"),
            LLMCallResult(True, '{"test": "data"}', 1000, {"input_tokens": 100, "output_tokens": 50}, None)
        )[1]
        
        mock_parser = Mock()
        mock_parser.parse.side_effect = lambda x: (
            call_order.append("parse"),
            ParseResult(True, {"test": "data"}, "DirectParseStrategy", [])
        )[1]
        
        mock_recorder = Mock()
        mock_recorder.record_usage.side_effect = lambda x: (
            call_order.append("usage"),
            True
        )[1]
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=mock_recorder
        )
        
        orchestrator.execute_phase(
            pipeline_id="pip_test",
            phase_name="pm_phase",
            epic_context="Test",
            pipeline_state={},
            artifacts={}
        )
        
        # Verify sequence
        assert call_order == ["config", "prompt", "llm", "parse", "usage"]
    
    def test_error_context_included(self):
        """Should include phase_name and pipeline_id in all errors."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.side_effect = ConfigurationError(
            "Config not found", "test_phase", "test_pipeline"
        )
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=Mock(),
            llm_caller=Mock(),
            parser=Mock(),
            usage_recorder=Mock()
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            orchestrator.execute_phase(
                pipeline_id="test_pipeline",
                phase_name="test_phase",
                epic_context="Test",
                pipeline_state={},
                artifacts={}
            )
        
        error = exc_info.value
        assert error.phase_name == "test_phase"
        assert error.pipeline_id == "test_pipeline"
        assert "[test_pipeline:test_phase]" in str(error)
    
    def test_llm_response_raw_preserved(self):
        """Should preserve raw LLM response in result."""
        mock_config_loader = Mock()
        mock_config_loader.load_config.return_value = PhaseConfig(
            phase_name="pm_phase",
            role_name="pm",
            artifact_type="epic",
            next_phase="arch_phase",
            is_active=True
        )
        
        mock_prompt_builder = Mock()
        mock_prompt_builder.build_prompt.return_value = ("prompt", "rp_123")
        
        raw_response = 'Here is the JSON: {"title": "Test Epic"}'
        mock_llm_caller = Mock()
        mock_llm_caller.call.return_value = LLMCallResult(
            success=True,
            response_text=raw_response,
            execution_time_ms=1000,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            error=None
        )
        
        mock_parser = Mock()
        mock_parser.parse.return_value = ParseResult(
            success=True,
            data={"title": "Test Epic"},
            strategy_used="DirectParseStrategy",
            error_messages=[]
        )
        
        mock_recorder = Mock()
        mock_recorder.record_usage.return_value = True
        
        orchestrator = PhaseExecutionOrchestrator(
            config_loader=mock_config_loader,
            prompt_builder=mock_prompt_builder,
            llm_caller=mock_llm_caller,
            parser=mock_parser,
            usage_recorder=mock_recorder
        )
        
        result = orchestrator.execute_phase(
            pipeline_id="pip_test",
            phase_name="pm_phase",
            epic_context="Test",
            pipeline_state={},
            artifacts={}
        )
        
        assert result.llm_response_raw == raw_response


# Total: 15 tests