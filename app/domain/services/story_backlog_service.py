"""
Story Backlog Service - Business logic for story backlog operations.

WS-STORY-BACKLOG-COMMANDS-SLICE-2: Generate stories for epics.
WS-ADR-035: Durable LLM execution with thread queue.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.services.document_service import DocumentService
from app.api.services.role_prompt_service import RolePromptService
from app.llm import AnthropicProvider, Message
from app.core.config import settings
from app.domain.services.thread_execution_service import ThreadExecutionService
from app.domain.services.llm_execution_logger import LLMExecutionLogger  # ADR-010
from app.persistence import (
    ThreadStatus,
    WorkItemStatus,
    ErrorCode,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerateEpicResult:
    """Result of generating stories for an epic."""
    status: str
    epic_id: str
    stories_generated: int
    stories_written: int
    thread_id: Optional[UUID] = None  # ADR-035: Thread reference
    stories: List[dict] = None  # The generated story summaries
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.stories is None:
            self.stories = []


@dataclass
class GenerateAllResult:
    """Result of generating stories for all epics."""
    status: str
    epics_processed: int
    total_stories_generated: int
    thread_id: Optional[UUID] = None  # ADR-035: Parent thread reference
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def project_story_to_summary(full_story: dict, epic_id: str) -> dict:
    """
    Convert full BA story to summary for StoryBacklog.
    
    This is the projection step - lossy by design.
    Full story lives in StoryDetail document.
    """
    story_id = full_story.get("id") or full_story.get("story_id")
    description = full_story.get("description") or full_story.get("intent") or ""
    phase = full_story.get("mvp_phase") or full_story.get("phase") or "mvp"
    
    if phase == "later-phase":
        phase = "later"
    
    return {
        "story_id": story_id,
        "title": full_story.get("title", "Untitled Story"),
        "intent": description[:200] if len(description) > 200 else description,
        "phase": phase,
        "detail_ref": {
            "document_type": "StoryDetailView",
            "params": {"story_id": story_id}
        }
    }


class StoryBacklogService:
    """Service for story backlog operations with durable execution (ADR-035)."""
    
    def __init__(self, db: AsyncSession, llm_logger: Optional[LLMExecutionLogger] = None):
        self.db = db
        self.doc_service = DocumentService(db)
        self.prompt_service = RolePromptService(db)
        self.thread_service = ThreadExecutionService(db)
        self.llm_logger = llm_logger  # ADR-010: Optional execution logger    
    # =========================================================================
    # LLM LOGGING HELPERS (ADR-010)
    # =========================================================================
    
    async def _start_llm_run(
        self, llm_logger: Optional[LLMExecutionLogger], project_id: UUID,
        epic_id: str, prompt_text: str, user_message: str,
    ) -> Optional[UUID]:
        if not llm_logger:
            return None
        try:
            from uuid import uuid4
            run_id = await llm_logger.start_run(
                correlation_id=uuid4(), project_id=project_id, role="ba",
                artifact_type="story_backlog", model_provider="anthropic",
                model_name="claude-sonnet-4-20250514", prompt_id="ba:story_backlog",
                prompt_version="1.0", effective_prompt=prompt_text,
            )
            await llm_logger.add_input(run_id, "system_prompt", prompt_text)
            await llm_logger.add_input(run_id, "user_prompt", user_message)
            await llm_logger.add_input(run_id, "context_doc", json.dumps({"epic_id": epic_id}))
            return run_id
        except Exception as e:
            logger.warning(f"LLM logging failed at start for {epic_id}: {e}")
            return None
    
    async def _log_llm_output(
        self, llm_logger: Optional[LLMExecutionLogger], run_id: Optional[UUID],
        epic_id: str, raw_response: str,
    ) -> None:
        if not llm_logger or not run_id:
            return
        try:
            await llm_logger.add_output(run_id, "raw_text", raw_response)
        except Exception as e:
            logger.warning(f"LLM logging failed at output for {epic_id}: {e}")
    
    async def _complete_llm_run(
        self, llm_logger: Optional[LLMExecutionLogger], run_id: Optional[UUID],
        epic_id: str, success: bool, usage: dict = None,
    ) -> None:
        if not llm_logger or not run_id:
            return
        try:
            await llm_logger.complete_run(run_id, status="SUCCESS" if success else "FAILED", usage=usage or {})
        except Exception as e:
            logger.warning(f"LLM logging failed at complete for {epic_id}: {e}")
    
    async def _log_llm_error(
        self, llm_logger: Optional[LLMExecutionLogger], run_id: Optional[UUID],
        epic_id: str, error_msg: str,
    ) -> None:
        if not llm_logger or not run_id:
            return
        try:
            await llm_logger.log_error(run_id, "LLM_CALL", "ERROR", "LLM_ERROR", error_msg)
            await llm_logger.complete_run(run_id, "FAILED", {})
        except Exception as e:
            logger.warning(f"LLM logging failed at error for {epic_id}: {e}")
    
    async def generate_epic_stories(
        self,
        project_id: UUID,
        epic_id: str,
        created_by: Optional[str] = None,
    ) -> GenerateEpicResult:
        """Generate stories for a single epic with durable execution (ADR-035)."""
        
        # 1. Create or get thread (idempotency check)
        idempotency_key = ThreadExecutionService.make_idempotency_key(
            operation="story_generate_epic",
            space_type="project",
            space_id=project_id,
            target_doc_type="story_backlog",
            target_id=epic_id,
        )
        
        thread, created = await self.thread_service.get_or_create_thread(
            kind="story_generate_epic",
            space_type="project",
            space_id=project_id,
            target_ref={"doc_type": "story_backlog", "epic_id": epic_id},
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        
        # If thread already exists and is complete, check for stories
        if not created and thread.status == ThreadStatus.COMPLETE:
            story_backlog = await self.doc_service.get_latest(
                space_type="project", space_id=project_id, doc_type_id="story_backlog"
            )
            if story_backlog:
                for epic in story_backlog.content.get("epics", []):
                    if epic.get("epic_id") == epic_id:
                        return GenerateEpicResult(
                            status="skipped", epic_id=epic_id, stories_generated=0, stories_written=0,
                            thread_id=thread.id, stories=epic.get("stories", []),
                        )
        
        # If thread is still running, return its status
        if not created and thread.status == ThreadStatus.RUNNING:
            return GenerateEpicResult(
                status="running", epic_id=epic_id, stories_generated=0, stories_written=0,
                thread_id=thread.id,
            )
        
        # 2. Load StoryBacklog
        story_backlog = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="story_backlog"
        )
        
        if not story_backlog:
            await self.thread_service.fail_thread(thread.id)
            return GenerateEpicResult(
                status="error", epic_id=epic_id, stories_generated=0, stories_written=0,
                thread_id=thread.id, error="StoryBacklog not found. Call init first."
            )
        
        # 3. Find epic in StoryBacklog
        epics = story_backlog.content.get("epics", [])
        epic_index = None
        epic_data = None
        
        for i, e in enumerate(epics):
            if e.get("epic_id") == epic_id:
                epic_index = i
                epic_data = e
                break
        
        if epic_data is None:
            await self.thread_service.fail_thread(thread.id)
            return GenerateEpicResult(
                status="error", epic_id=epic_id, stories_generated=0, stories_written=0,
                thread_id=thread.id, error=f"Epic '{epic_id}' not found in StoryBacklog"
            )
        
        # 4. Check if epic already has stories
        existing_stories = epic_data.get("stories", [])
        if existing_stories:
            await self.thread_service.complete_thread(thread.id)
            return GenerateEpicResult(
                status="skipped", epic_id=epic_id, stories_generated=0, stories_written=0,
                thread_id=thread.id, stories=existing_stories,
            )
        
        # 5. Create work item and start execution
        work_item = await self.thread_service.create_work_item(
            thread_id=thread.id, lock_scope=f"epic:{epic_id}",
        )
        await self.thread_service.start_thread(thread.id)
        await self.thread_service.start_work_item(work_item.id)
        
        # 6. Load context
        epic_backlog = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="epic_backlog"
        )
        architecture = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="technical_architecture"
        )
        
        # 7. Build LLM prompt
        prompt_text, task_id = await self.prompt_service.build_prompt(
            role_name="ba", task_name="story_backlog",
        )
        user_message = self._build_user_message(epic_id, epic_data, epic_backlog, architecture)
        
        # Record prompt in ledger
        await self.thread_service.record_prompt(
            thread_id=thread.id, work_item_id=work_item.id,
            prompt_data={
                "system_prompt": prompt_text, "user_message": user_message,
                "model": "claude-sonnet-4-20250514", "task_id": task_id,
            }
        )
        
        # 8. Call LLM with logging
        run_id = await self._start_llm_run(self.llm_logger, project_id, epic_id, prompt_text, user_message)

        try:
            llm_output, raw_response, llm_usage = await self._call_llm_with_raw(prompt_text, user_message)
            await self.thread_service.record_response(
                thread_id=thread.id, work_item_id=work_item.id,
                response_data={"raw_content": raw_response, "parsed": llm_output}
            )
            
            await self._log_llm_output(self.llm_logger, run_id, epic_id, raw_response)
                    
        except Exception as e:
            error_msg = str(e)
            await self.thread_service.record_error(
                thread_id=thread.id, work_item_id=work_item.id,
                error_data={"error": error_msg, "stage": "llm_call"}
            )
            
            await self._log_llm_error(self.llm_logger, run_id, epic_id, error_msg)
            
            error_code = ErrorCode.PROVIDER_TIMEOUT if "timeout" in error_msg.lower() else ErrorCode.UNKNOWN
            await self.thread_service.fail_work_item(work_item.id, error_code, error_msg)
            await self.thread_service.fail_thread(thread.id)
            return GenerateEpicResult(
                status="error", epic_id=epic_id, stories_generated=0, stories_written=0,
                thread_id=thread.id, error=error_msg,
            )
        
        # 9. Extract stories
        stories = self._extract_stories(llm_output)
        await self.thread_service.record_parse_report(
            thread_id=thread.id, work_item_id=work_item.id,
            report_data={"stories_extracted": len(stories), "valid": len(stories) > 0}
        )
        
        if not stories:
            await self._complete_llm_run(self.llm_logger, run_id, epic_id, success=False)
            
            await self.thread_service.fail_work_item(work_item.id, ErrorCode.SCHEMA_INVALID, "LLM returned no stories")
            await self.thread_service.fail_thread(thread.id)
            return GenerateEpicResult(
                status="error", epic_id=epic_id, stories_generated=0, stories_written=0,
                thread_id=thread.id, error="LLM returned no stories",
            )
        
        await self._complete_llm_run(self.llm_logger, run_id, epic_id, success=True, usage=llm_usage)
        
        # 10. Store StoryDetails and project summaries
        summaries, stories_written = await self._store_stories(project_id, epic_id, stories)
        
        # 11. Update StoryBacklog
        updated_content = story_backlog.content.copy()
        updated_content["epics"][epic_index]["stories"] = summaries
        await self.doc_service.create_document(
            space_type="project", space_id=project_id, doc_type_id="story_backlog",
            title="Story Backlog", content=updated_content,
            summary=f"Story backlog with {len(updated_content['epics'])} epics",
            created_by="story-backlog-generate", created_by_type="builder"
        )
        
        # Record mutation in ledger
        await self.thread_service.record_mutation(
            thread_id=thread.id, work_item_id=work_item.id,
            mutation_data={
                "doc_type": "story_backlog", "epic_id": epic_id,
                "stories_added": len(summaries), "story_details_created": stories_written,
            }
        )
        
        # 12. Complete work item and thread
        await self.thread_service.apply_work_item(work_item.id)
        await self.thread_service.complete_thread(thread.id)
        await self.db.commit()
        
        logger.info(f"Generated {len(stories)} stories for epic {epic_id}")
        
        return GenerateEpicResult(
            status="completed", epic_id=epic_id, stories_generated=len(stories),
            stories_written=stories_written, thread_id=thread.id, stories=summaries,
        )

    
    def _build_user_message(self, epic_id: str, epic_data: dict, epic_backlog: Any, architecture: Any) -> str:
        """Build user message for LLM."""
        parts = [
            "Generate implementation-ready BA stories for the following epic.",
            "", "# Epic to Process",
            f"Epic ID: {epic_id}",
            f"Epic Name: {epic_data.get('name', 'Unknown')}",
            f"Epic Intent: {epic_data.get('intent', 'No intent provided')}",
            f"MVP Phase: {epic_data.get('mvp_phase', 'mvp')}",
        ]
        
        if epic_backlog and epic_backlog.content:
            for eb_epic in epic_backlog.content.get("epics", []):
                eb_epic_id = eb_epic.get("epic_id") or eb_epic.get("id")
                if eb_epic_id == epic_id or eb_epic.get("title") == epic_data.get("name"):
                    parts.extend(["", "# Epic Details from Epic Backlog", "```json", json.dumps(eb_epic, indent=2), "```"])
                    break
        
        if architecture and architecture.content:
            components = architecture.content.get("components", [])
            if components:
                comp_names = [c.get("name") or c.get("id") for c in components]
                parts.extend(["", "# Architecture Context", f"Available components: {', '.join(comp_names)}"])
        
        parts.extend(["", "Output ONLY valid JSON matching the schema. Generate 3-8 stories."])
        return "\n".join(parts)
    
    async def _call_llm_with_raw(self, system_prompt: str, user_message: str) -> tuple:
        """Call LLM and return both parsed output and raw response."""
        provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, enable_caching=True)
        messages = [Message.user(user_message)]
        response = await provider.complete(
            messages=messages, model="claude-sonnet-4-20250514",
            max_tokens=8192, temperature=0.7, system_prompt=system_prompt,
        )
        raw_content = response.content
        parse_content = raw_content
        if "```json" in parse_content:
            parse_content = parse_content.split("```json")[1].split("```")[0]
        elif "```" in parse_content:
            parse_content = parse_content.split("```")[1].split("```")[0]
        parsed = json.loads(parse_content.strip())
        
        # ADR-010: Return usage data for telemetry
        usage = {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "total_tokens": response.input_tokens + response.output_tokens,
        }
        return parsed, raw_content, usage
    
    def _extract_stories(self, llm_output: dict) -> List[dict]:
        """Extract stories from LLM output."""
        if "stories" in llm_output:
            return llm_output["stories"]
        elif "epics" in llm_output and len(llm_output["epics"]) > 0:
            return llm_output["epics"][0].get("stories", [])
        return []
    
    async def _store_stories(self, project_id: UUID, epic_id: str, stories: List[dict]) -> tuple:
        """Store StoryDetail documents and return summaries."""
        summaries = []
        stories_written = 0
        for story in stories:
            story_id = story.get("id") or story.get("story_id")
            if not story_id:
                continue
            story_detail = {
                "story_id": story_id, "epic_id": epic_id, "title": story.get("title", ""),
                "description": story.get("description", ""),
                "acceptance_criteria": story.get("acceptance_criteria", []),
                "related_arch_components": story.get("related_arch_components", []),
                "related_pm_story_ids": story.get("related_pm_story_ids", []),
                "notes": story.get("notes", []), "mvp_phase": story.get("mvp_phase", "mvp")
            }
            try:
                await self.doc_service.create_document(
                    space_type="project", space_id=project_id, doc_type_id="story_detail",
                    title=story.get("title", story_id), content=story_detail,
                    summary=f"Story: {story.get('title', story_id)}",
                    created_by="story-backlog-generate", created_by_type="builder"
                )
                stories_written += 1
            except Exception as e:
                logger.warning(f"Failed to create StoryDetail for {story_id}: {e}")
            summaries.append(project_story_to_summary(story, epic_id))
        return summaries, stories_written

    
    async def _generate_epic_stories_llm_only(
        self,
        project_id: UUID,
        epic_id: str,
        epic_data: dict,
        epic_backlog: Any,
        architecture: Any,
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Generate stories for an epic via LLM only (no save).
        Used for parallel generation.
        Returns dict with epic_id, stories, error.
        
        ADR-010: Creates isolated DB session for telemetry to avoid
        race conditions during parallel execution.
        """
        from app.core.database import async_session_factory
        from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
        from uuid import uuid4
        
        run_id = None
        log_session = None
        llm_logger = None
        
        try:
            # Build prompt
            prompt_text, task_id = await self.prompt_service.build_prompt(
                role_name="ba", task_name="story_backlog",
            )
            user_message = self._build_user_message(epic_id, epic_data, epic_backlog, architecture)
            
            # ADR-010: Create isolated session for telemetry (parallel safety)
            try:
                log_session = async_session_factory()
                await log_session.__aenter__()
                log_repo = PostgresLLMLogRepository(log_session)
                llm_logger = LLMExecutionLogger(log_repo)
                run_id = await self._start_llm_run(llm_logger, project_id, epic_id, prompt_text, user_message)
            except Exception as e:
                logger.warning(f"LLM logging failed at start for {epic_id}: {e}")
            
            # Call LLM
            llm_output, raw_response, llm_usage = await self._call_llm_with_raw(prompt_text, user_message)
            
            await self._log_llm_output(llm_logger, run_id, epic_id, raw_response)
            
            # Extract stories
            stories = self._extract_stories(llm_output)
            
            await self._complete_llm_run(llm_logger, run_id, epic_id, success=bool(stories), usage=llm_usage)
            
            if not stories:
                return {"epic_id": epic_id, "stories": [], "error": "LLM returned no stories"}
            
            return {"epic_id": epic_id, "stories": stories, "error": None}
            
        except Exception as e:
            logger.error(f"Failed to generate stories for epic {epic_id}: {e}")
            
            await self._log_llm_error(llm_logger, run_id, epic_id, str(e))
            
            return {"epic_id": epic_id, "stories": [], "error": str(e)}
        
        finally:
            # Clean up isolated session
            if log_session:
                try:
                    await log_session.__aexit__(None, None, None)
                except Exception:
                    pass

    async def generate_all_stories(self, project_id: UUID, created_by: Optional[str] = None) -> GenerateAllResult:
        """Generate stories for all epics in PARALLEL with durable execution (ADR-035)."""
        import asyncio
        
        # Create parent thread
        idempotency_key = ThreadExecutionService.make_idempotency_key(
            operation="story_generate_all", space_type="project", space_id=project_id,
            target_doc_type="story_backlog", target_id="all",
        )
        
        parent_thread, created = await self.thread_service.get_or_create_thread(
            kind="story_generate_all", space_type="project", space_id=project_id,
            target_ref={"doc_type": "story_backlog"}, idempotency_key=idempotency_key,
            created_by=created_by,
        )
        
        if not created and parent_thread.status == ThreadStatus.RUNNING:
            return GenerateAllResult(
                status="running", epics_processed=0, total_stories_generated=0, thread_id=parent_thread.id,
            )
        
        if not created and parent_thread.status == ThreadStatus.COMPLETE:
            child_summary = await self.thread_service.get_child_summary(parent_thread.id)
            return GenerateAllResult(
                status="skipped", epics_processed=sum(child_summary.values()),
                total_stories_generated=0, thread_id=parent_thread.id,
            )
        
        story_backlog = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="story_backlog"
        )
        
        if not story_backlog:
            await self.thread_service.fail_thread(parent_thread.id)
            return GenerateAllResult(
                status="error", epics_processed=0, total_stories_generated=0,
                thread_id=parent_thread.id, errors=["StoryBacklog not found. Call init first."]
            )
        
        epics = story_backlog.content.get("epics", [])
        if not epics:
            await self.thread_service.complete_thread(parent_thread.id)
            return GenerateAllResult(
                status="completed", epics_processed=0, total_stories_generated=0, thread_id=parent_thread.id,
            )
        
        # Filter to epics that need stories
        epics_needing_stories = [e for e in epics if not e.get("stories")]
        
        if not epics_needing_stories:
            await self.thread_service.complete_thread(parent_thread.id)
            return GenerateAllResult(
                status="skipped", epics_processed=len(epics), total_stories_generated=0,
                thread_id=parent_thread.id,
            )
        
        await self.thread_service.start_thread(parent_thread.id)
        
        # Load shared context once
        epic_backlog = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="epic_backlog"
        )
        architecture = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="technical_architecture"
        )
        
        # Generate stories for all epics IN PARALLEL
        logger.info(f"Starting parallel generation for {len(epics_needing_stories)} epics")
        
        tasks = [
            self._generate_epic_stories_llm_only(
                project_id=project_id,
                epic_id=epic.get("epic_id"),
                epic_data=epic,
                epic_backlog=epic_backlog,
                architecture=architecture,
                created_by=created_by,
            )
            for epic in epics_needing_stories
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update StoryBacklog
        total_stories = 0
        errors = []
        updated_content = story_backlog.content.copy()
        epic_id_to_index = {e.get("epic_id"): i for i, e in enumerate(updated_content["epics"])}
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                continue
            
            epic_id = result["epic_id"]
            stories = result["stories"]
            error = result["error"]
            
            if error:
                errors.append(f"{epic_id}: {error}")
                continue
            
            if not stories:
                continue
            
            # Store StoryDetails
            summaries, stories_written = await self._store_stories(project_id, epic_id, stories)
            total_stories += len(stories)
            
            # Update epic in content
            if epic_id in epic_id_to_index:
                updated_content["epics"][epic_id_to_index[epic_id]]["stories"] = summaries
        
        # Save StoryBacklog once with all updates
        await self.doc_service.create_document(
            space_type="project", space_id=project_id, doc_type_id="story_backlog",
            title="Story Backlog", content=updated_content,
            summary=f"Story backlog with {len(updated_content['epics'])} epics",
            created_by="story-backlog-generate", created_by_type="builder"
        )
        
        await self.thread_service.complete_thread(parent_thread.id)
        await self.db.commit()
        
        logger.info(f"Parallel generation complete: {total_stories} stories for {len(epics_needing_stories)} epics")
        
        return GenerateAllResult(
            status="completed" if not errors else "completed_with_errors",
            epics_processed=len(epics_needing_stories), total_stories_generated=total_stories,
            thread_id=parent_thread.id, errors=errors if errors else None
        )



    async def generate_all_stories_stream(self, project_id: UUID, created_by: Optional[str] = None):
        """
        Generate stories for all epics with SSE streaming.
        Yields results as each epic completes (parallel execution, streaming output).
        """
        import asyncio
        import json
        
        # Load StoryBacklog
        story_backlog = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="story_backlog"
        )
        
        if not story_backlog:
            yield f"data: {json.dumps({'type': 'error', 'message': 'StoryBacklog not found'})}\n\n"
            return
        
        epics = story_backlog.content.get("epics", [])
        epics_needing_stories = [e for e in epics if not e.get("stories")]
        
        if not epics_needing_stories:
            yield f"data: {json.dumps({'type': 'complete', 'message': 'All epics already have stories', 'total_epics': len(epics), 'total_stories': 0})}\n\n"
            return
        
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'total_epics': len(epics_needing_stories)})}\n\n"
        
        # Load shared context once
        epic_backlog = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="epic_backlog"
        )
        architecture = await self.doc_service.get_latest(
            space_type="project", space_id=project_id, doc_type_id="technical_architecture"
        )
        
        # Create tasks for all epics
        tasks = {
            asyncio.create_task(
                self._generate_epic_stories_llm_only(
                    project_id=project_id,
                    epic_id=epic.get("epic_id"),
                    epic_data=epic,
                    epic_backlog=epic_backlog,
                    architecture=architecture,
                    created_by=created_by,
                )
            ): epic.get("epic_id")
            for epic in epics_needing_stories
        }
        
        # Track results for final save
        all_results = []
        completed_count = 0
        total_stories = 0
        errors = []
        
        # Process as each task completes
        pending = set(tasks.keys())
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                epic_id = tasks[task]
                completed_count += 1
                
                try:
                    result = task.result()
                    all_results.append(result)
                    
                    if result.get("error"):
                        errors.append(f"{epic_id}: {result['error']}")
                        yield f"data: {json.dumps({'type': 'epic_error', 'epic_id': epic_id, 'error': result['error'], 'completed': completed_count, 'total': len(epics_needing_stories)})}\n\n"
                    else:
                        stories = result.get("stories", [])
                        story_count = len(stories)
                        total_stories += story_count
                        
                        # Store StoryDetails immediately
                        summaries, _ = await self._store_stories(project_id, epic_id, stories)
                        result["summaries"] = summaries
                        
                        yield f"data: {json.dumps({'type': 'epic_complete', 'epic_id': epic_id, 'stories_generated': story_count, 'stories': summaries, 'completed': completed_count, 'total': len(epics_needing_stories)})}\n\n"
                        
                except Exception as e:
                    errors.append(f"{epic_id}: {str(e)}")
                    yield f"data: {json.dumps({'type': 'epic_error', 'epic_id': epic_id, 'error': str(e), 'completed': completed_count, 'total': len(epics_needing_stories)})}\n\n"
        
        # Update StoryBacklog with all results
        updated_content = story_backlog.content.copy()
        epic_id_to_index = {e.get("epic_id"): i for i, e in enumerate(updated_content["epics"])}
        
        for result in all_results:
            epic_id = result.get("epic_id")
            summaries = result.get("summaries", [])
            if summaries and epic_id in epic_id_to_index:
                updated_content["epics"][epic_id_to_index[epic_id]]["stories"] = summaries
        
        # Save StoryBacklog once with all updates
        await self.doc_service.create_document(
            space_type="project", space_id=project_id, doc_type_id="story_backlog",
            title="Story Backlog", content=updated_content,
            summary=f"Story backlog with {len(updated_content['epics'])} epics",
            created_by="story-backlog-generate", created_by_type="builder"
        )
        await self.db.commit()
        
        # Send complete event
        yield f"data: {json.dumps({'type': 'complete', 'total_epics': len(epics_needing_stories), 'total_stories': total_stories, 'errors': errors if errors else None})}\n\n"















