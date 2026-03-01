"""
Document Builder - The one class that builds any document type.

This replaces all the mentor classes with a single, registry-driven builder.
The builder:
1. Looks up document config from registry
2. Checks dependencies
3. Gathers inputs
4. Loads prompts
5. Calls LLM (streaming or sync)
6. Hands off to handler for processing
7. Persists the document with relationships

Adding a new document type requires NO changes to this class.

Week 2 (ADR-010): Integrated LLM execution logging for telemetry and replay.
"""

from typing import Dict, Any, List, Optional, AsyncGenerator, Protocol
from dataclasses import dataclass
from uuid import UUID
import json
import asyncio
import logging
import httpx
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.domain.registry.loader import (
    get_document_config,
    DocumentNotFoundError,
)
from app.domain.handlers import (
    get_handler,
    DocumentParseError,
    DocumentValidationError,
    DependencyNotMetError,
    HandlerNotFoundError,
)
from app.domain.services.llm_response_parser import LLMResponseParser
from app.domain.services.llm_execution_logger import LLMExecutionLogger  # ADR-010
from app.api.services.document_service import DocumentService
from app.domain.services.document_builder_pure import (
    resolve_model_params,
    build_user_message as pure_build_user_message,
    compute_stream_progress,
    should_emit_stream_update,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PROTOCOLS - Dependency Injection Interfaces
# =============================================================================

class PromptServiceProtocol(Protocol):
    """Interface for prompt service."""
    
    async def get_prompt_for_role_task(
        self,
        role_name: str,
        task_name: str
    ) -> tuple[str, str, Dict[str, Any]]:
        """
        Get prompt for a role/task combination.
        
        Returns:
            Tuple of (system_prompt, prompt_id, expected_schema)
        """
        ...


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BuildResult:
    """Result of a document build operation."""
    success: bool
    doc_type_id: str
    document_id: Optional[str] = None
    title: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    html: Optional[str] = None
    error: Optional[str] = None
    tokens: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "doc_type_id": self.doc_type_id,
            "document_id": self.document_id,
            "title": self.title,
            "error": self.error,
            "tokens": self.tokens,
        }


@dataclass  
class ProgressUpdate:
    """Progress update for streaming builds."""
    status: str
    message: str
    progress: int
    data: Optional[Dict[str, Any]] = None
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        payload = {
            "status": self.status,
            "message": self.message,
            "progress": self.progress,
        }
        if self.data:
            payload["data"] = self.data
        return f"data: {json.dumps(payload)}\n\n"

@dataclass
class BuildContext:
    config: Dict[str, Any]
    handler: Any
    input_docs: Dict[str, Any]
    input_ids: List[UUID]
    system_prompt: str
    prompt_id: str
    schema: Optional[Dict[str, Any]]
    user_message: str
    model: str
    max_tokens: int
    temperature: float
    doc_type_id: str
    space_type: str
    space_id: UUID

# =============================================================================
# DOCUMENT BUILDER
# =============================================================================

class DocumentBuilder:
    """
    Builds any document type using the registry and handlers.
    
    This is the replacement for all mentor classes.
    One class, any document type.
    """
    
    def __init__(
        self,
        db,  # AsyncSession
        prompt_service: PromptServiceProtocol,
        document_service: Optional[DocumentService] = None,
        model: Optional[str] = None,
        correlation_id: Optional[UUID] = None,  # ADR-010: UUID from middleware
        llm_logger: Optional[LLMExecutionLogger] = None,  # ADR-010: Injected logger
    ):
        """
        Initialize builder with dependencies.
        
        Args:
            db: Database session for registry queries
            prompt_service: Service for loading prompts
            document_service: Service for document CRUD (created if not provided)
            model: Optional model override
            correlation_id: Request correlation ID for telemetry (UUID from middleware)
            llm_logger: Optional LLM execution logger for ADR-010 telemetry
        """
        self.db = db
        self.prompt_service = prompt_service
        self.document_service = document_service or DocumentService(db)
        self.model = model or "claude-sonnet-4-20250514"
        self.correlation_id = correlation_id  # Stored as UUID
        self.llm_logger = llm_logger  # ADR-010: Injected, not created here
        self.llm_parser = LLMResponseParser()
        self.anthropic_client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=httpx.Timeout(300.0, connect=10.0)
        )
    
    # =========================================================================
    # PUBLIC API - Check Buildability
    # =========================================================================
    
    async def can_build(
        self,
        doc_type_id: str,
        space_type: str,
        space_id: UUID,
    ) -> tuple[bool, List[str]]:
        """
        Check if a document type can be built in a given space.
        
        Returns (can_build, missing_dependencies)
        """
        config = await get_document_config(self.db, doc_type_id)
        required = config.get("required_inputs", [])
        
        if not required:
            return True, []
        
        existing = await self.document_service.get_existing_doc_types(space_type, space_id)
        missing = [dep for dep in required if dep not in existing]
        
        return len(missing) == 0, missing
    # =========================================================================
    # PRIVATE - Build Preparation (Shared by build and build_stream)
    # =========================================================================
    
    async def _prepare_build(
        self,
        doc_type_id: str,
        space_type: str,
        space_id: UUID,
        inputs: Dict[str, Any],
        options: Dict[str, Any],
    ) -> BuildContext:
        config = await get_document_config(self.db, doc_type_id)
        handler = get_handler(config["handler_id"])
        can_build_now, missing = await self.can_build(doc_type_id, space_type, space_id)
        if not can_build_now:
            raise DependencyNotMetError(doc_type_id, missing)
        input_docs, input_ids = await self._gather_inputs(config, space_type, space_id)
        system_prompt, prompt_id, schema = await self.prompt_service.get_prompt_for_role_task(
            role_name=config["builder_role"],
            task_name=config["builder_task"]
        )
        user_message = self._build_user_message(config, inputs, input_docs)
        model, max_tokens, temperature = resolve_model_params(options, self.model)

        return BuildContext(
            config=config, handler=handler, input_docs=input_docs, input_ids=input_ids,
            system_prompt=system_prompt, prompt_id=prompt_id, schema=schema,
            user_message=user_message, model=model, max_tokens=max_tokens,
            temperature=temperature, doc_type_id=doc_type_id,
            space_type=space_type, space_id=space_id,
        )
    
    async def _start_llm_logging(self, ctx: BuildContext, input_docs: Optional[Dict[str, Any]] = None) -> Optional[UUID]:
        if not self.llm_logger:
            return None
        try:
            run_id = await self.llm_logger.start_run(
                correlation_id=self.correlation_id,
                project_id=ctx.space_id if ctx.space_type == "project" else None,
                artifact_type=ctx.doc_type_id, role=ctx.config["builder_role"],
                model_provider="anthropic", model_name=ctx.model,
                prompt_id=ctx.prompt_id, prompt_version="1.0.0",
                effective_prompt=ctx.system_prompt,
            )
            await self.llm_logger.add_input(run_id, "system_prompt", ctx.system_prompt)
            await self.llm_logger.add_input(run_id, "user_prompt", ctx.user_message)
            if input_docs:
                for input_doc_type, content in input_docs.items():
                    await self.llm_logger.add_input(run_id, "context_doc", f"{input_doc_type}:\n{json.dumps(content, indent=2)}")
            if ctx.schema:
                await self.llm_logger.add_input(run_id, "schema", json.dumps(ctx.schema, indent=2))
            return run_id
        except Exception as e:
            logger.warning(f"LLM logging failed at start: {e}")
            return None
    
    async def _log_llm_output(self, run_id: Optional[UUID], raw_content: str) -> None:
        if not self.llm_logger or not run_id:
            return
        try:
            await self.llm_logger.add_output(run_id, "raw_text", raw_content)
        except Exception as e:
            logger.warning(f"LLM logging failed at output: {e}")
    
    async def _log_llm_error(self, run_id: Optional[UUID], stage: str, error_code: str, message: str, severity: str = "ERROR", details: Optional[Dict[str, Any]] = None) -> None:
        if not self.llm_logger or not run_id:
            return
        try:
            await self.llm_logger.log_error(run_id, stage=stage, severity=severity, error_code=error_code, message=message, details=details)
            await self.llm_logger.complete_run(run_id, status="FAILED", usage={})
        except Exception as e:
            logger.warning(f"LLM logging failed: {e}")
    
    async def _complete_llm_logging(self, run_id: Optional[UUID], input_tokens: int, output_tokens: int, document_id: Optional[str] = None, parse_status: Optional[str] = None, validation_status: Optional[str] = None) -> None:
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
            await self.llm_logger.complete_run(run_id, status="SUCCESS", usage={"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens}, metadata=metadata if metadata else None)
        except Exception as e:
            logger.warning(f"LLM logging failed at complete: {e}")
    
    async def _persist_document(self, ctx: BuildContext, result: Dict[str, Any], input_tokens: int, output_tokens: int, run_id: Optional[UUID], created_by: Optional[str]):
        parent_doc = await self.document_service.create_document(
            space_type=ctx.space_type, space_id=ctx.space_id, doc_type_id=ctx.doc_type_id,
            title=result["title"], content=result["data"], created_by=created_by,
            created_by_type="builder",
            builder_metadata={"prompt_id": ctx.prompt_id, "model": ctx.model, "input_tokens": input_tokens, "output_tokens": output_tokens, "llm_run_id": str(run_id) if run_id else None},
            derived_from=ctx.input_ids,
        )

        # Create child documents if the handler defines them
        await self._create_child_documents(ctx, result, parent_doc.id, created_by)

        return parent_doc

    async def _create_child_documents(
        self,
        ctx: BuildContext,
        result: Dict[str, Any],
        parent_id: UUID,
        created_by: Optional[str]
    ) -> List[UUID]:
        """
        Create child documents extracted by the handler.

        For example, implementation_plan creates Epic documents.

        Returns list of created child document IDs.
        """
        child_specs = ctx.handler.get_child_documents(result["data"], result["title"])

        if not child_specs:
            return []

        created_ids = []
        for spec in child_specs:
            try:
                child_doc = await self.document_service.create_document(
                    space_type=ctx.space_type,
                    space_id=ctx.space_id,
                    doc_type_id=spec["doc_type_id"],
                    title=spec["title"],
                    content=spec["content"],
                    created_by=created_by,
                    created_by_type="builder",
                    builder_metadata={
                        "extracted_from": ctx.doc_type_id,
                        "parent_document_id": str(parent_id),
                        "identifier": spec.get("identifier"),
                    },
                    derived_from=[parent_id],
                )
                created_ids.append(child_doc.id)
                logger.info(f"Created child document: {child_doc.id} ({spec['doc_type_id']})")
            except Exception as e:
                logger.error(f"Failed to create child document {spec.get('identifier')}: {e}")
                # Continue with other children, don't fail the whole operation

        return created_ids

    # =========================================================================
    # PUBLIC API - Sync Build
    # =========================================================================
    
    async def build(
        self,
        doc_type_id: str,
        space_type: str,
        space_id: UUID,
        inputs: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> BuildResult:
        inputs = inputs or {}
        options = options or {}
        run_id = None
        
        try:
            ctx = await self._prepare_build(doc_type_id, space_type, space_id, inputs, options)
            logger.info(f"LLM call: model={ctx.model!r}, max_tokens={ctx.max_tokens}, temp={ctx.temperature}")
            
            run_id = await self._start_llm_logging(ctx)
            
            response = self.anthropic_client.messages.create(
                model=ctx.model, max_tokens=ctx.max_tokens, temperature=ctx.temperature,
                system=ctx.system_prompt, messages=[{"role": "user", "content": ctx.user_message}]
            )
            
            raw_content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            await self._log_llm_output(run_id, raw_content)
            result = ctx.handler.process(raw_content, ctx.config.get("schema_definition"))
            doc = await self._persist_document(ctx, result, input_tokens, output_tokens, run_id, created_by)
            html = ctx.handler.render(result["data"])
            await self._complete_llm_logging(run_id, input_tokens, output_tokens, str(doc.id))
            
            return BuildResult(
                success=True, doc_type_id=doc_type_id, document_id=str(doc.id),
                title=result["title"], data=result["data"], html=html,
                tokens={"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens}
            )
            
        except DocumentNotFoundError as e:
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except HandlerNotFoundError as e:
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except DependencyNotMetError as e:
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except DocumentParseError as e:
            await self._log_llm_error(run_id, "PARSE", "PARSE_ERROR", str(e))
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except DocumentValidationError as e:
            await self._log_llm_error(run_id, "VALIDATE", "VALIDATION_ERROR", str(e))
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except Exception as e:
            logger.error(f"Build failed for {doc_type_id}: {e}", exc_info=True)
            await self._log_llm_error(run_id, "MODEL_CALL", "UNEXPECTED_ERROR", str(e), severity="FATAL")
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))

    # =========================================================================
    # PUBLIC API - Streaming Build
    # =========================================================================
    
    async def build_stream(
        self,
        doc_type_id: str,
        space_type: str,
        space_id: UUID,
        inputs: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        inputs = inputs or {}
        options = options or {}
        run_id = None
        
        try:
            yield ProgressUpdate("loading", "Loading document configuration...", 5).to_sse()
            config = await get_document_config(self.db, doc_type_id)
            
            yield ProgressUpdate("loading", "Loading handler...", 10).to_sse()
            handler = get_handler(config["handler_id"])
            
            yield ProgressUpdate("checking", "Checking dependencies...", 15).to_sse()
            can_build_now, missing = await self.can_build(doc_type_id, space_type, space_id)
            
            if not can_build_now:
                yield ProgressUpdate("error", f"Missing dependencies: {', '.join(missing)}", 15, {"missing_dependencies": missing}).to_sse()
                return
            
            yield ProgressUpdate("gathering", "Gathering input documents...", 20).to_sse()
            input_docs, input_ids = await self._gather_inputs(config, space_type, space_id)
            
            yield ProgressUpdate("prompts", "Loading prompts...", 25).to_sse()
            system_prompt, prompt_id, schema = await self.prompt_service.get_prompt_for_role_task(
                role_name=config["builder_role"], task_name=config["builder_task"]
            )
            
            user_message = self._build_user_message(config, inputs, input_docs)
            
            model, max_tokens, temperature = resolve_model_params(options, self.model)
            
            ctx = BuildContext(
                config=config, handler=handler, input_docs=input_docs, input_ids=input_ids,
                system_prompt=system_prompt, prompt_id=prompt_id, schema=schema,
                user_message=user_message, model=model, max_tokens=max_tokens,
                temperature=temperature, doc_type_id=doc_type_id,
                space_type=space_type, space_id=space_id,
            )
            
            run_id = await self._start_llm_logging(ctx, input_docs)
            
            yield ProgressUpdate("generating", "Generating document...", 30).to_sse()
            accumulated_text = ""
            
            try:
                async with self.anthropic_client.messages.stream(
                    model=model, max_tokens=max_tokens, temperature=temperature,
                    system=system_prompt, messages=[{"role": "user", "content": user_message}]
                ) as stream:
                    async for text in stream.text_stream:
                        accumulated_text += text
                        if should_emit_stream_update(len(accumulated_text), len(text)):
                            preview = accumulated_text[:100] + "..." if len(accumulated_text) > 100 else accumulated_text
                            yield ProgressUpdate("streaming", "Generating...", compute_stream_progress(len(accumulated_text)), {"preview": preview}).to_sse()
                
                final_message = await stream.get_final_message()
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens
                await self._log_llm_output(run_id, accumulated_text)
                
            except Exception as e:
                await self._log_llm_error(run_id, "MODEL_CALL", "LLM_API_ERROR", str(e), severity="FATAL", details={"exception_type": type(e).__name__})
                raise
            
            yield ProgressUpdate("parsing", "Parsing response...", 75).to_sse()
            await asyncio.sleep(0.1)
            
            parse_status = None
            validation_status = None
            
            try:
                result = handler.process(accumulated_text, config.get("schema_definition"))
                parse_status = "PARSED"
                validation_status = "PASSED"
            except DocumentParseError as e:
                await self._log_llm_error(run_id, "PARSE", "PARSE_ERROR", str(e))
                raise
            except DocumentValidationError as e:
                await self._log_llm_error(run_id, "VALIDATE", "VALIDATION_ERROR", str(e))
                raise
            
            yield ProgressUpdate("saving", "Saving document...", 85).to_sse()
            doc = await self._persist_document(ctx, result, input_tokens, output_tokens, run_id, created_by)
            
            yield ProgressUpdate("rendering", "Rendering document...", 95).to_sse()
            handler.render(result["data"])
            
            await self._complete_llm_logging(run_id, input_tokens, output_tokens, str(doc.id), parse_status, validation_status)
            
            yield ProgressUpdate("complete", f"{config['name']} created!", 100, {
                "document_id": str(doc.id), "title": result["title"],
                "tokens": {"input": input_tokens, "output": output_tokens, "total": input_tokens + output_tokens}
            }).to_sse()
            
        except Exception as e:
            logger.error(f"Stream build failed for {doc_type_id}: {e}", exc_info=True)
            yield ProgressUpdate("error", f"Error: {str(e)}", 0).to_sse()

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    
    async def _gather_inputs(
        self,
        config: Dict[str, Any],
        space_type: str,
        space_id: UUID
    ) -> tuple[Dict[str, Any], List[UUID]]:
        inputs = {}
        input_ids = []
        
        required = config.get("required_inputs", [])
        optional = config.get("optional_inputs", [])
        
        for doc_type in required + optional:
            doc = await self.document_service.get_latest(space_type, space_id, doc_type)
            if doc:
                inputs[doc_type] = doc.content
                input_ids.append(doc.id)
        
        return inputs, input_ids
    
    def _build_user_message(
        self,
        config: Dict[str, Any],
        user_inputs: Dict[str, Any],
        input_docs: Dict[str, Any]
    ) -> str:
        return pure_build_user_message(config, user_inputs, input_docs)
