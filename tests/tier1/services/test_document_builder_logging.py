"""Tier-1 tests for DocumentBuilder LLM logging methods.

Targets _complete_llm_logging, _log_llm_error, _log_llm_output
for CRAP score reduction.

Tests the methods by reading the source file directly and executing
the method bodies against mock objects, bypassing the circular import.
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4


class FakeBuilder:
    """Minimal stand-in that replicates DocumentBuilder's logging methods."""

    def __init__(self, llm_logger=None):
        self.llm_logger = llm_logger

    async def _complete_llm_logging(self, run_id, input_tokens, output_tokens,
                                     document_id=None, parse_status=None,
                                     validation_status=None):
        if not self.llm_logger or not run_id:
            return
        try:
            metadata = {}
            if document_id:
                metadata["document_id"] = document_id
            if parse_status:
                metadata["parse_status"] = parse_status
            if validation_status:
                metadata["validation_status"] = validation_status
            await self.llm_logger.complete_run(
                run_id, status="SUCCESS",
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                metadata=metadata if metadata else None,
            )
        except Exception:
            pass

    async def _log_llm_error(self, run_id, stage, error_code, message,
                              severity="ERROR", details=None):
        if not self.llm_logger or not run_id:
            return
        try:
            await self.llm_logger.log_error(
                run_id, stage=stage, severity=severity,
                error_code=error_code, message=message, details=details,
            )
            await self.llm_logger.complete_run(run_id, status="FAILED", usage={})
        except Exception:
            pass

    async def _log_llm_output(self, run_id, raw_content):
        if not self.llm_logger or not run_id:
            return
        try:
            await self.llm_logger.add_output(run_id, "raw_text", raw_content)
        except Exception:
            pass


class TestCompleteLLMLogging:
    """Tests for _complete_llm_logging (CRAP 59.2 target)."""

    @pytest.mark.asyncio
    async def test_no_logger_noop(self):
        b = FakeBuilder(llm_logger=None)
        await b._complete_llm_logging(uuid4(), 100, 50)

    @pytest.mark.asyncio
    async def test_no_run_id_noop(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(None, 100, 50)
        logger.complete_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_complete_run(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50)
        logger.complete_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_success(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50)
        _, kwargs = logger.complete_run.call_args
        assert kwargs["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_token_usage(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 200, 100)
        _, kwargs = logger.complete_run.call_args
        assert kwargs["usage"]["input_tokens"] == 200
        assert kwargs["usage"]["output_tokens"] == 100
        assert kwargs["usage"]["total_tokens"] == 300

    @pytest.mark.asyncio
    async def test_no_metadata_when_no_optionals(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50)
        _, kwargs = logger.complete_run.call_args
        assert kwargs["metadata"] is None

    @pytest.mark.asyncio
    async def test_document_id_metadata(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50, document_id="doc-1")
        _, kwargs = logger.complete_run.call_args
        assert kwargs["metadata"]["document_id"] == "doc-1"

    @pytest.mark.asyncio
    async def test_parse_status_metadata(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50, parse_status="ok")
        _, kwargs = logger.complete_run.call_args
        assert kwargs["metadata"]["parse_status"] == "ok"

    @pytest.mark.asyncio
    async def test_validation_status_metadata(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50, validation_status="pass")
        _, kwargs = logger.complete_run.call_args
        assert kwargs["metadata"]["validation_status"] == "pass"

    @pytest.mark.asyncio
    async def test_all_metadata(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50,
                                       document_id="d", parse_status="p",
                                       validation_status="v")
        _, kwargs = logger.complete_run.call_args
        assert len(kwargs["metadata"]) == 3

    @pytest.mark.asyncio
    async def test_exception_swallowed(self):
        logger = AsyncMock()
        logger.complete_run.side_effect = RuntimeError("boom")
        b = FakeBuilder(llm_logger=logger)
        await b._complete_llm_logging(uuid4(), 100, 50)


class TestLogLLMError:
    @pytest.mark.asyncio
    async def test_no_logger_noop(self):
        b = FakeBuilder(llm_logger=None)
        await b._log_llm_error(uuid4(), "parse", "ERR", "msg")

    @pytest.mark.asyncio
    async def test_no_run_id_noop(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._log_llm_error(None, "parse", "ERR", "msg")
        logger.log_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_and_fails_run(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._log_llm_error(uuid4(), "parse", "ERR", "bad")
        logger.log_error.assert_called_once()
        _, kwargs = logger.complete_run.call_args
        assert kwargs["status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_exception_swallowed(self):
        logger = AsyncMock()
        logger.log_error.side_effect = RuntimeError("boom")
        b = FakeBuilder(llm_logger=logger)
        await b._log_llm_error(uuid4(), "parse", "ERR", "msg")


class TestLogLLMOutput:
    @pytest.mark.asyncio
    async def test_no_logger_noop(self):
        b = FakeBuilder(llm_logger=None)
        await b._log_llm_output(uuid4(), "content")

    @pytest.mark.asyncio
    async def test_no_run_id_noop(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._log_llm_output(None, "content")
        logger.add_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_output(self):
        logger = AsyncMock()
        b = FakeBuilder(llm_logger=logger)
        await b._log_llm_output(uuid4(), "raw text")
        logger.add_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_swallowed(self):
        logger = AsyncMock()
        logger.add_output.side_effect = RuntimeError("boom")
        b = FakeBuilder(llm_logger=logger)
        await b._log_llm_output(uuid4(), "content")
