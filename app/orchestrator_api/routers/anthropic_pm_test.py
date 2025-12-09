"""
Direct Anthropic PM Test Router (PIPELINE-X01)

Ultra-minimal endpoint to validate Anthropic API integration
outside the full pipeline system.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic
import os

router = APIRouter()

# Initialize Anthropic client
client = Anthropic(api_key=os.getenv("WORKBENCH_ANTHROPIC_API_KEY"))


class PMTestRequest(BaseModel):
    """Request schema for PM test endpoint."""
    epic_description: str


class PMTestResponse(BaseModel):
    """Response schema with PM output and usage metrics."""
    pm_output: str
    input_tokens: int
    output_tokens: int
    model: str
    full_prompt_sent: str


# PM Mentor Prompt Template
PM_MENTOR_PROMPT = """You are the PM Mentor in the Workbench Workforce.

Your job is to analyze the Epic description, identify risks, clarify ambiguous requirements, 
and deliver a structured, actionable Epic definition including:

- Refined Epic summary
- Key outcomes
- Primary constraints
- Acceptance criteria
- Known unknowns
- Open questions

Response is to be sent in JSON. There shall be no conversational text outside the JSON.

Epic Description:
---
{epic}
---

Respond with your improved Epic definition."""


@router.post("/anthropic/pm-test", response_model=PMTestResponse)
async def anthropic_pm_test(req: PMTestRequest):
    """
    Test PM Mentor prompt directly via Anthropic API.
    
    This endpoint:
    1. Wraps the epic description in the PM Mentor prompt
    2. Sends to Anthropic (Claude Sonnet 4.5)
    3. Returns the PM output with token usage metrics
    
    No database writes, no pipeline execution - pure API validation.
    """
    # Build full prompt
    full_prompt = PM_MENTOR_PROMPT.format(epic=req.epic_description)
    
    try:
        # Call Anthropic API
        completion = client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Sonnet 4.5
            max_tokens=4000,
            messages=[{"role": "user", "content": full_prompt}]
        )
        
        # Extract response text
        pm_output = completion.content[0].text
        
        # Return structured response
        return PMTestResponse(
            pm_output=pm_output,
            input_tokens=completion.usage.input_tokens,
            output_tokens=completion.usage.output_tokens,
            model=completion.model,
            full_prompt_sent=full_prompt
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Anthropic API error: {str(e)}"
        )






