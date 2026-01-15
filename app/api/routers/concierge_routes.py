"""
Concierge API routes - Conversational intake interface.

NOT a wizard. A guided architectural conversation with a conversion point.

Three modes (internal, not exposed):
- informational: answering questions about The Combine
- exploratory: architect-in-discovery questioning  
- ready_for_discovery: sufficient context gathered

Only creates governed artifacts after explicit consent.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.web.routes.shared import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concierge", tags=["concierge"])

def _is_htmx_request(request: Request) -> bool:
    """Check if this is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


def _fallback_response(conversation: List[Dict[str, str]]) -> Dict[str, Any]:
    """Simple heuristic fallback when LLM unavailable."""
    if not conversation:
        return {
            "response_type": "answer",
            "content": "Hello! I am the Concierge. Tell me what you would like to build, or ask me about how The Combine works.",
            "mode": "informational"
        }
    
    last_msg = conversation[-1]["content"].lower() if conversation else ""
    
    if any(word in last_msg for word in ["what is", "how does", "explain", "tell me about"]):
        return {
            "response_type": "answer",
            "content": "The Combine is a document-centric system that helps teams move from rough ideas to governed, high-quality artifacts. It uses structured AI assistance with explicit quality gates. What would you like to know more about?",
            "mode": "informational"
        }
    
    user_msgs = [m for m in conversation if m["role"] == "user"]
    if len(user_msgs) >= 4:
        return {
            "response_type": "recommend_discovery",
            "content": "I think I have enough context to start a formal Discovery document. This will capture what we have discussed, note the open questions, and give you something concrete to review and challenge. Would you like me to create it?",
            "mode": "ready"
        }
    
    questions = [
        "What problem are you trying to solve? Not the solution you are thinking of, but the underlying problem.",
        "Who are the main users or stakeholders affected by this?",
        "What would success look like? How would you know this worked?",
        "What constraints do you already know about - technical, timeline, budget, or organizational?",
    ]
    q_index = len(user_msgs) % len(questions)
    
    return {
        "response_type": "question",
        "content": questions[q_index],
        "mode": "exploratory"
    }

async def call_concierge_llm(conversation: List[Dict[str, str]], db: AsyncSession) -> Dict[str, Any]:
    """Call LLM to generate next concierge turn."""
    import os
    
    conv_text = "\n".join([
        f"{'User' if m['role'] == 'user' else 'Concierge'}: {m['content']}"
        for m in conversation[-10:]
    ])
    
    system_prompt = """You are the Concierge for The Combine, a document-centric Industrial AI system.

Your role has three modes:

1. INFORMATIONAL: If the user asks about The Combine, answer helpfully.
   - It helps teams move from ideas to governed artifacts
   - Uses AI-assisted discovery and planning
   - Documents have lifecycle tracking
   - Quality enforced through process

2. EXPLORATORY: If user describes a project, become a senior architect in discovery.
   - Ask ONE question at a time
   - Focus on: problem, context, constraints, success criteria
   - Do NOT design - just understand

3. READY: When you have enough (clear problem + bounded unknowns, usually 3-6 exchanges):
   - Signal readiness to create Discovery document
   - Suggest a concise project name (2-4 words, descriptive, no special characters)

Respond with JSON only:
{"response_type": "answer"|"question"|"recommend_discovery", "content": "your message", "mode": "informational"|"exploratory"|"ready", "suggested_name": "Project Name Here (only when mode is ready)"}"""

    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return _fallback_response(conversation)
        
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Conversation:\n{conv_text}\n\nRespond with JSON only."}]
        )
        
        response_text = response.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        return json.loads(response_text.strip())
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return _fallback_response(conversation)


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/", include_in_schema=False)
@router.get("/new", include_in_schema=False)
@router.get("/start", include_in_schema=False)
async def redirect_to_start():
    """Redirect legacy concierge routes to canonical /start."""
    return RedirectResponse(url="/start", status_code=status.HTTP_302_FOUND)


@router.get("/{session_id}", response_class=HTMLResponse)
async def get_session(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Get existing session with conversation history."""
    try:
        result = await db.execute(text(
            "SELECT user_id, state FROM concierge_intake_session WHERE id = :id"
        ), {"id": str(session_id)})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        if row.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        events = await db.execute(text("""
            SELECT event_type, payload_json FROM concierge_intake_event
            WHERE session_id = :sid AND event_type IN ('user_message', 'concierge_message')
            ORDER BY seq ASC
        """), {"sid": str(session_id)})
        
        messages = []
        for event in events.fetchall():
            payload = event.payload_json if isinstance(event.payload_json, dict) else json.loads(event.payload_json)
            messages.append({
                "role": "user" if event.event_type == "user_message" else "concierge",
                "content": payload.get("content", "")
            })
        
        context = {
            "session_id": str(session_id),
            "messages": messages
        }
        
        # HTMX request - return just the content partial
        if _is_htmx_request(request):
            return templates.TemplateResponse(
                request,
                "concierge/partials/_chat_content.html",
                context
            )
        
        # Full page request - return page with base.html
        return templates.TemplateResponse(
            request,
            "concierge/chat.html",
            context
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting session: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/message", response_class=HTMLResponse)
async def send_message(
    session_id: UUID,
    request: Request,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Process user message and get concierge response."""
    try:
        result = await db.execute(text(
            "SELECT user_id, state FROM concierge_intake_session WHERE id = :id"
        ), {"id": str(session_id)})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        if row.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        now = datetime.utcnow()
        
        seq_result = await db.execute(text(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM concierge_intake_event WHERE session_id = :sid"
        ), {"sid": str(session_id)})
        next_seq = seq_result.scalar()
        
        # Store user message
        await db.execute(text("""
            INSERT INTO concierge_intake_event (id, session_id, seq, event_type, payload_json, created_at)
            VALUES (:id, :sid, :seq, 'user_message', :payload, :now)
        """), {"id": str(uuid_module.uuid4()), "sid": str(session_id), "seq": next_seq, "payload": json.dumps({"content": content}), "now": now})
        
        # Get conversation history
        events = await db.execute(text("""
            SELECT event_type, payload_json FROM concierge_intake_event
            WHERE session_id = :sid AND event_type IN ('user_message', 'concierge_message')
            ORDER BY seq ASC
        """), {"sid": str(session_id)})
        
        conversation = []
        for event in events.fetchall():
            payload = event.payload_json if isinstance(event.payload_json, dict) else json.loads(event.payload_json)
            conversation.append({
                "role": "user" if event.event_type == "user_message" else "concierge",
                "content": payload.get("content", "")
            })
        conversation.append({"role": "user", "content": content})
        
        # Get LLM response
        llm_response = await call_concierge_llm(conversation, db)
        
        # Store concierge response
        await db.execute(text("""
            INSERT INTO concierge_intake_event (id, session_id, seq, event_type, payload_json, created_at)
            VALUES (:id, :sid, :seq, 'concierge_message', :payload, :now)
        """), {"id": str(uuid_module.uuid4()), "sid": str(session_id), "seq": next_seq + 1, "payload": json.dumps(llm_response), "now": now})
        
        mode = llm_response.get("mode", "informational")
        await db.execute(text(
            "UPDATE concierge_intake_session SET state = :state, updated_at = :now WHERE id = :id"
        ), {"state": mode, "now": now, "id": str(session_id)})
        
        await db.commit()
        
        # Build HTML response
        response_content = llm_response.get("content", "")
        html = f'''
<div class="flex items-start space-x-3 flex-row-reverse space-x-reverse">
    <div class="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center flex-shrink-0">
        <span class="text-white text-sm font-bold">U</span>
    </div>
    <div class="flex-1 text-right">
        <div class="inline-block rounded-lg p-4 max-w-prose text-left bg-gray-100 dark:bg-gray-700">
            <p class="text-gray-900 dark:text-white whitespace-pre-wrap">{content}</p>
        </div>
    </div>
</div>
<div class="flex items-start space-x-3">
    <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
        <span class="text-white text-sm font-bold">C</span>
    </div>
    <div class="flex-1">
        <div class="inline-block rounded-lg p-4 max-w-prose text-left bg-blue-50 dark:bg-blue-900/30">
            <p class="text-gray-900 dark:text-white whitespace-pre-wrap">{response_content}</p>
        </div>
    </div>
</div>
'''
        headers = {}
        if llm_response.get("response_type") == "recommend_discovery":
            headers["HX-Trigger"] = "showConsentPrompt"
        
        return HTMLResponse(content=html, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in send_message: %s", e, exc_info=True)
        await db.rollback()
        return HTMLResponse(content=f'<div class="p-4 bg-red-100 text-red-800 rounded">Error: {str(e)}</div>', status_code=500)


@router.post("/{session_id}/consent", response_class=HTMLResponse)
async def submit_consent(
    session_id: UUID,
    request: Request,
    accept: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Accept consent to create project."""
    logger.info("=== CONSENT ENDPOINT CALLED ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Accept value: {accept}")
    logger.info(f"User: {current_user.user_id}")
    try:
        result = await db.execute(text(
            "SELECT user_id, state FROM concierge_intake_session WHERE id = :id"
        ), {"id": str(session_id)})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        if row.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        now = datetime.utcnow()
        
        if accept.lower() == "true":
            # Get first user message as project description (brief summary)
            events = await db.execute(text("""
                SELECT payload_json FROM concierge_intake_event
                WHERE session_id = :sid AND event_type = 'user_message'
                ORDER BY seq ASC LIMIT 1
            """), {"sid": str(session_id)})
            
            first_event = events.fetchone()
            if first_event:
                payload = first_event.payload_json if isinstance(first_event.payload_json, dict) else json.loads(first_event.payload_json)
                description = payload.get("content", "")[:1000]  # First message, up to 1000 chars
            else:
                description = "Project created via Concierge"
            
            # Create project
            project_id = uuid_module.uuid4()
            project_short_id = str(project_id)[:8].upper()
            
            # Get suggested name from last concierge message
            project_name = f"Project {project_short_id}"
            last_concierge = await db.execute(text("""
                SELECT payload_json FROM concierge_intake_event
                WHERE session_id = :sid AND event_type = 'concierge_message'
                ORDER BY seq DESC LIMIT 1
            """), {"sid": str(session_id)})
            last_msg = last_concierge.fetchone()
            if last_msg:
                payload = last_msg.payload_json if isinstance(last_msg.payload_json, dict) else json.loads(last_msg.payload_json)
                suggested = payload.get("suggested_name")
                if suggested and len(suggested.strip()) > 0 and len(suggested) <= 50:
                    project_name = suggested.strip()
            
            user_id_str = str(current_user.user_id)
            await db.execute(text("""
                INSERT INTO projects (id, project_id, name, description, icon, owner_id, organization_id, created_by, created_at, updated_at)
                VALUES (:id, :project_id, :name, :desc, :icon, :owner, :org, :created_by, :now, :now)
            """), {
                "id": str(project_id),
                "project_id": project_short_id,
                "name": project_name,
                "desc": description,
                "icon": "folder",
                "owner": user_id_str,
                "org": user_id_str,
                "created_by": user_id_str,
                "now": now
            })
            
            seq_result = await db.execute(text(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM concierge_intake_event WHERE session_id = :sid"
            ), {"sid": str(session_id)})
            next_seq = seq_result.scalar()
            
            await db.execute(text("""
                INSERT INTO concierge_intake_event (id, session_id, seq, event_type, payload_json, created_at)
                VALUES (:id, :sid, :seq, 'consent_accepted', :payload, :now)
            """), {"id": str(uuid_module.uuid4()), "sid": str(session_id), "seq": next_seq, "payload": json.dumps({"project_id": str(project_id)}), "now": now})
            
            await db.execute(text("""
                UPDATE concierge_intake_session SET state = 'completed', project_id = :pid, updated_at = :now WHERE id = :id
            """), {"pid": str(project_id), "now": now, "id": str(session_id)})
            
            await db.commit()
            
            logger.info(f"=== PROJECT CREATED: {project_id} ===")
            
            return HTMLResponse(content=f'''
<div class="flex items-start space-x-3">
    <div class="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center flex-shrink-0">
        <span class="text-white text-sm font-bold">OK</span>
    </div>
    <div class="flex-1">
        <div class="inline-block rounded-lg p-4 max-w-prose text-left bg-green-50 dark:bg-green-900/30">
            <p class="text-gray-900 dark:text-white font-medium">Project created!</p>
            <p class="text-gray-700 dark:text-gray-300 mt-2">Your project is ready. I will generate a Discovery document.</p>
            <a href="/projects/{project_id}" class="inline-block mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">Go to Project</a>
        </div>
    </div>
</div>
''')
        else:
            return HTMLResponse(content='')
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in consent: %s", e, exc_info=True)
        await db.rollback()
        return HTMLResponse(content=f'<div class="p-4 bg-red-100 text-red-800 rounded">Error: {str(e)}</div>', status_code=500)
