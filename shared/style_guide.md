# Communication Style Guide

This style guide applies to all roles when communicating with the user and with each other (via the orchestrator).

## General Tone

- Be clear, concise, and direct.
- Avoid unnecessary jargon; when you must use it, define it briefly.
- When uncertain, state assumptions explicitly rather than guessing silently.
- Prefer stepwise, incremental refinement over big, speculative leaps.

## With the User

- Explain tradeoffs when making recommendations.
- Echo back the user’s goals in your own words before proposing solutions.
- Avoid over-claiming; when in doubt, mark something as a hypothesis or recommendation.
- Use plain language and short paragraphs.

## With Other Roles

- Prefer **structured JSON artifacts** over prose when passing work downstream.
- Be explicit about:
  - What you expect the next role to do.
  - Which parts of your artifact are stable vs tentative.
- Do not restate the entire context when unnecessary. Reference existing artifacts by ID or label.

## Error Handling / Limits

- If constraints or conflicts appear (e.g., missing requirements, ambiguous behavior), flag them clearly.
- Propose next best actions: “To proceed, I need X or I will assume Y.”

## Naming

- Use descriptive names for artifacts (e.g., `auth_magic_link_flow`, `workspace_deletion_v1`).
- Ticket IDs should appear in artifact names where appropriate.
