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
from anthropic import Anthropic

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
        self.anthropic_client = Anthropic(
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
        """
        Build a document synchronously (non-streaming).
        
        Args:
            doc_type_id: The document type to build
            space_type: 'project' | 'organization' | 'team'
            space_id: UUID of owning entity
            inputs: Additional inputs (user_query, etc.)
            options: Build options (model, temperature, etc.)
            created_by: Creator identifier
            
        Returns:
            BuildResult with document details or error
        """
        inputs = inputs or {}
        options = options or {}
        
        # ADR-010: Use injected logger (graceful degradation if not provided)
        llm_logger = self.llm_logger
        run_id = None
        
        try:
            # 1. Load document config from registry
            config = await get_document_config(self.db, doc_type_id)
            
            # 2. Get handler
            handler = get_handler(config["handler_id"])
            
            # 3. Check dependencies
            can_build_now, missing = await self.can_build(doc_type_id, space_type, space_id)
            
            if not can_build_now:
                raise DependencyNotMetError(doc_type_id, missing)
            
            # 4. Gather input documents
            input_docs, input_ids = await self._gather_inputs(config, space_type, space_id)
            
            # 5. Load prompts
            system_prompt, prompt_id, schema = await self.prompt_service.get_prompt_for_role_task(
                role_name=config["builder_role"],
                task_name=config["builder_task"]
            )
            
            # 6. Build user message
            user_message = self._build_user_message(config, inputs, input_docs)
            
            # 7. Prepare LLM call
            model = options.get("model") or self.model
            if model in (None, "", "string"):
                model = self.model
            max_tokens = options.get("max_tokens") or 4096
            temperature = options.get("temperature") if options.get("temperature") is not None else 0.7
            
            logger.info(f"LLM call: model={model!r}, max_tokens={max_tokens}, temp={temperature}")
            
            # =====================================================================
            # ADR-010: START LLM RUN LOGGING
            # =====================================================================
            if llm_logger:
                try:
                    run_id = await llm_logger.start_run(
                        correlation_id=self.correlation_id,
                        project_id=space_id if space_type == "project" else None,
                        artifact_type=doc_type_id,
                        role=config["builder_role"],
                        model_provider="anthropic",
                        model_name=model,
                        prompt_id=prompt_id,
                        prompt_version="1.0.0",
                        effective_prompt=system_prompt,
                    )
                    await llm_logger.add_input(run_id, "system_prompt", system_prompt)
                    await llm_logger.add_input(run_id, "user_prompt", user_message)
                    if schema:
                        await llm_logger.add_input(run_id, "schema", json.dumps(schema, indent=2))
                except Exception as e:
                    logger.warning(f"LLM logging failed at start: {e}")
            # =====================================================================
            
            # 8. Call LLM
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            
            raw_content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # =====================================================================
            # ADR-010: LOG OUTPUT
            # =====================================================================
            if llm_logger and run_id:
                try:
                    await llm_logger.add_output(run_id, "raw_text", raw_content)
                except Exception as e:
                    logger.warning(f"LLM logging failed at output: {e}")
            # =====================================================================
            
            # 9. Process with handler
            result = handler.process(raw_content, config.get("schema_definition"))
            
            # 10. Persist document with relationships
            doc = await self.document_service.create_document(
                space_type=space_type,
                space_id=space_id,
                doc_type_id=doc_type_id,
                title=result["title"],
                content=result["data"],
                created_by=created_by,
                created_by_type="builder",
                builder_metadata={
                    "prompt_id": prompt_id,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "llm_run_id": str(run_id) if run_id else None,
                },
                derived_from=input_ids,
            )
            
            # 11. Render HTML
            html = handler.render(result["data"])
            
            # =====================================================================
            # ADR-010: COMPLETE RUN
            # =====================================================================
            if llm_logger and run_id:
                try:
                    await llm_logger.complete_run(
                        run_id,
                        status="SUCCESS",
                        usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                        }
                    )
                except Exception as e:
                    logger.warning(f"LLM logging failed at complete: {e}")
            # =====================================================================
            
            return BuildResult(
                success=True,
                doc_type_id=doc_type_id,
                document_id=str(doc.id),
                title=result["title"],
                data=result["data"],
                html=html,
                tokens={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": input_tokens + output_tokens,
                }
            )
            
        except DocumentNotFoundError as e:
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except HandlerNotFoundError as e:
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except DependencyNotMetError as e:
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except DocumentParseError as e:
            if llm_logger and run_id:
                try:
                    await llm_logger.log_error(run_id, "PARSE", "ERROR", "PARSE_ERROR", str(e))
                    await llm_logger.complete_run(run_id, "FAILED", {})
                except Exception as log_err:
                    logger.warning(f"LLM logging failed: {log_err}")
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except DocumentValidationError as e:
            if llm_logger and run_id:
                try:
                    await llm_logger.log_error(run_id, "VALIDATE", "ERROR", "VALIDATION_ERROR", str(e))
                    await llm_logger.complete_run(run_id, "FAILED", {})
                except Exception as log_err:
                    logger.warning(f"LLM logging failed: {log_err}")
            return BuildResult(success=False, doc_type_id=doc_type_id, error=str(e))
        except Exception as e:
            logger.error(f"Build failed for {doc_type_id}: {e}", exc_info=True)
            if llm_logger and run_id:
                try:
                    await llm_logger.log_error(run_id, "MODEL_CALL", "FATAL", "UNEXPECTED_ERROR", str(e))
                    await llm_logger.complete_run(run_id, "FAILED", {})
                except Exception as log_err:
                    logger.warning(f"LLM logging failed: {log_err}")
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
        """
        Build a document with streaming progress updates.
        
        Yields SSE-formatted progress updates.
        """
        inputs = inputs or {}
        options = options or {}
        
        # ADR-010: Use injected logger
        llm_logger = self.llm_logger
        run_id = None
        
        try:
            # Step 1: Load config
            yield ProgressUpdate("loading", "ðŸ“‹ Loading document configuration...", 5).to_sse()
            config = await get_document_config(self.db, doc_type_id)
            
            # Step 2: Get handler
            yield ProgressUpdate("loading", "ðŸ”§ Loading handler...", 10).to_sse()
            handler = get_handler(config["handler_id"])
            
            # Step 3: Check dependencies
            yield ProgressUpdate("checking", "ðŸ” Checking dependencies...", 15).to_sse()
            can_build_now, missing = await self.can_build(doc_type_id, space_type, space_id)
            
            if not can_build_now:
                yield ProgressUpdate(
                    "error", 
                    f"âŒ Missing dependencies: {', '.join(missing)}", 
                    15,
                    {"missing_dependencies": missing}
                ).to_sse()
                return
            
            # Step 4: Gather inputs
            yield ProgressUpdate("gathering", "ðŸ“¥ Gathering input documents...", 20).to_sse()
            input_docs, input_ids = await self._gather_inputs(config, space_type, space_id)
            
            # Step 5: Load prompts
            yield ProgressUpdate("prompts", "ðŸ“ Loading prompts...", 25).to_sse()
            system_prompt, prompt_id, schema = await self.prompt_service.get_prompt_for_role_task(
                role_name=config["builder_role"],
                task_name=config["builder_task"]
            )
            
            # Step 6: Build user message
            user_message = self._build_user_message(config, inputs, input_docs)
            
            # Step 7: Prepare LLM call
            model = options.get("model") or self.model
            if model in (None, "", "string"):
                model = self.model
            max_tokens = options.get("max_tokens") or 4096
            temperature = options.get("temperature") if options.get("temperature") is not None else 0.7
            
            # =====================================================================
            # ADR-010: START LLM RUN LOGGING
            # =====================================================================
            if llm_logger:
                try:
                    run_id = await llm_logger.start_run(
                        correlation_id=self.correlation_id,
                        project_id=space_id if space_type == "project" else None,
                        artifact_type=doc_type_id,
                        role=config["builder_role"],
                        model_provider="anthropic",
                        model_name=model,
                        prompt_id=prompt_id,
                        prompt_version="1.0.0",
                        effective_prompt=system_prompt,
                    )
                    
                    # Log inputs
                    await llm_logger.add_input(run_id, "system_prompt", system_prompt)
                    await llm_logger.add_input(run_id, "user_prompt", user_message)
                    
                    # Log input documents
                    for input_doc_type, content in input_docs.items():
                        await llm_logger.add_input(
                            run_id, 
                            "context_doc", 
                            f"{input_doc_type}:\n{json.dumps(content, indent=2)}"
                        )
                    
                    if schema:
                        await llm_logger.add_input(run_id, "schema", json.dumps(schema, indent=2))
                        
                except Exception as e:
                    logger.warning(f"LLM logging failed at start_run: {e}")
            # =====================================================================
            
            # Step 8: Call LLM (streaming)
            yield ProgressUpdate("generating", "ðŸ¤– Generating document...", 30).to_sse()
            
            accumulated_text = ""
            final_message = None
            
            try:
                with self.anthropic_client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                ) as stream:
                    for text in stream.text_stream:
                        accumulated_text += text
                        if len(accumulated_text) % 100 < len(text):
                            preview = accumulated_text[:100] + "..." if len(accumulated_text) > 100 else accumulated_text
                            yield ProgressUpdate(
                                "streaming", 
                                "ðŸ¤– Generating...", 
                                min(30 + len(accumulated_text) // 50, 70),
                                {"preview": preview}
                            ).to_sse()
                
                final_message = stream.get_final_message()
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens
                
                # =================================================================
                # ADR-010: LOG OUTPUT
                # =================================================================
                if llm_logger and run_id:
                    try:
                        await llm_logger.add_output(
                            run_id,
                            "raw_text",
                            accumulated_text,
                            parse_status=None,
                            validation_status=None
                        )
                    except Exception as e:
                        logger.warning(f"LLM logging failed at add_output: {e}")
                # =================================================================
                
            except Exception as e:
                # =================================================================
                # ADR-010: LOG LLM ERROR
                # =================================================================
                if llm_logger and run_id:
                    try:
                        await llm_logger.log_error(
                            run_id,
                            stage="MODEL_CALL",
                            severity="FATAL",
                            error_code="LLM_API_ERROR",
                            message=str(e),
                            details={"exception_type": type(e).__name__}
                        )
                        await llm_logger.complete_run(run_id, status="FAILED", usage={})
                    except Exception as log_err:
                        logger.warning(f"LLM logging failed during error handling: {log_err}")
                # =================================================================
                raise
            
            # Step 9: Parse
            yield ProgressUpdate("parsing", "ðŸ”„ Parsing response...", 75).to_sse()
            await asyncio.sleep(0.1)
            
            parse_status = None
            validation_status = None
            
            try:
                result = handler.process(accumulated_text, config.get("schema_definition"))
                parse_status = "PARSED"
                validation_status = "PASSED"
                
            except DocumentParseError as e:
                parse_status = "FAILED"
                if llm_logger and run_id:
                    try:
                        await llm_logger.log_error(
                            run_id,
                            stage="PARSE",
                            severity="ERROR",
                            error_code="PARSE_ERROR",
                            message=str(e)
                        )
                        await llm_logger.complete_run(run_id, status="FAILED", usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        })
                    except Exception as log_err:
                        logger.warning(f"LLM logging failed: {log_err}")
                raise
                
            except DocumentValidationError as e:
                parse_status = "PARSED"
                validation_status = "FAILED"
                if llm_logger and run_id:
                    try:
                        await llm_logger.log_error(
                            run_id,
                            stage="VALIDATE",
                            severity="ERROR",
                            error_code="VALIDATION_ERROR",
                            message=str(e)
                        )
                        await llm_logger.complete_run(run_id, status="FAILED", usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        })
                    except Exception as log_err:
                        logger.warning(f"LLM logging failed: {log_err}")
                raise
            
            # Step 10: Save
            yield ProgressUpdate("saving", "ðŸ’¾ Saving document...", 85).to_sse()
            
            doc = await self.document_service.create_document(
                space_type=space_type,
                space_id=space_id,
                doc_type_id=doc_type_id,
                title=result["title"],
                content=result["data"],
                created_by=created_by,
                created_by_type="builder",
                builder_metadata={
                    "prompt_id": prompt_id,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "llm_run_id": str(run_id) if run_id else None,
                },
                derived_from=input_ids,
            )
            
            # Step 11: Render
            yield ProgressUpdate("rendering", "ðŸŽ¨ Rendering document...", 95).to_sse()
            html = handler.render(result["data"])
            
            # =====================================================================
            # ADR-010: COMPLETE RUN LOGGING
            # =====================================================================
            if llm_logger and run_id:
                try:
                    await llm_logger.complete_run(
                        run_id,
                        status="SUCCESS",
                        usage={
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                        },
                        cost_usd=None,  # TODO: Calculate cost based on model pricing
                        metadata={
                            "document_id": str(doc.id),
                            "parse_status": parse_status,
                            "validation_status": validation_status,
                        }
                    )
                except Exception as e:
                    logger.warning(f"LLM logging failed at complete_run: {e}")
            # =====================================================================
            
            # Complete!
            yield ProgressUpdate(
                "complete",
                f"ðŸŽ‰ {config['name']} created!",
                100,
                {
                    "document_id": str(doc.id),
                    "title": result["title"],
                    "tokens": {
                        "input": input_tokens,
                        "output": output_tokens,
                        "total": input_tokens + output_tokens,
                    }
                }
            ).to_sse()
            
        except Exception as e:
            logger.error(f"Stream build failed for {doc_type_id}: {e}", exc_info=True)
            yield ProgressUpdate("error", f"âŒ Error: {str(e)}", 0).to_sse()
    
    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================
    
    async def _gather_inputs(
        self,
        config: Dict[str, Any],
        space_type: str,
        space_id: UUID
    ) -> tuple[Dict[str, Any], List[UUID]]:
        """
        Gather required and optional input documents.
        
        Returns:
            Tuple of (doc_type -> content dict, list of document IDs)
        """
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
        """
        Build the user message for the LLM.
        
        Combines user inputs with gathered input documents.
        """
        parts = []
        
        # Add document type context
        parts.append(f"Create a {config['name']}.")
        
        if config.get("description"):
            parts.append(f"\nDocument purpose: {config['description']}")
        
        # Add user query if provided
        if user_inputs.get("user_query"):
            parts.append(f"\nUser request:\n{user_inputs['user_query']}")
        
        # Add project description if provided
        if user_inputs.get("project_description"):
            parts.append(f"\nProject description:\n{user_inputs['project_description']}")
        
        # Add input documents
        if input_docs:
            parts.append("\n\n--- Input Documents ---")
            for doc_type, content in input_docs.items():
                parts.append(f"\n### {doc_type}:\n```json\n{json.dumps(content, indent=2)}\n```")
        
        # Add output instruction
        parts.append("\n\nRemember: Output ONLY valid JSON matching the schema. No markdown, no prose.")
        
        return "\n".join(parts)

