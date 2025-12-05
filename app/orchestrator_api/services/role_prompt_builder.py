# app/orchestrator_api/services/role_prompt_builder.py

from app.orchestrator_api.prompts import pm_prompt, architect_prompt, ba_prompt, dev_prompt, qa_prompt

ROLE_PROMPTS = {
    "pm": pm_prompt,
    "architect": architect_prompt,
    "ba": ba_prompt,
    "dev": dev_prompt,
    "qa": qa_prompt,
}

def build_role_prompt(
    role_name: str,
    epic_context: Optional[str] = None,
    pipeline_context: Optional[Dict[str, Any]] = None
) -> str:
    """Build complete role prompt with context."""
    
    prompt_module = ROLE_PROMPTS.get(role_name)
    if not prompt_module:
        raise ValueError(f"Unknown role: {role_name}")
    
    sections = [
        f"You are the **{role_name}** mentor in The Combine Workforce.",
        "",
        "# Bootstrap",
        prompt_module.BOOTSTRAP,
        "",
        "# Instructions", 
        prompt_module.INSTRUCTIONS,
    ]
    
    if hasattr(prompt_module, 'SCHEMAS'):
        schemas_json = json.dumps(prompt_module.SCHEMAS, indent=2)
        sections.extend([
            "",
            "# Schemas",
            f"```json\n{schemas_json}\n```"
        ])
    
    if epic_context:
        sections.extend([
            "",
            "# Epic Context",
            epic_context
        ])
    
    if pipeline_context:
        context_json = json.dumps(pipeline_context, indent=2)
        sections.extend([
            "",
            "# Pipeline Context",
            f"```json\n{context_json}\n```"
        ])
    
    return "\n".join(sections)
