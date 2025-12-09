# Backlog Overview

The Workbench uses a hierarchical backlog:

- **Epics** – large bodies of work that describe a business capability or major feature.  
  - Stored as JSON/Markdown under: `workbench/epics/` (e.g., `AUTH-100`, `AUTH-101`).
  - Each Epic includes an orchestration plan describing which roles to involve and in what order.

- **Tickets** – smaller units of work associated with an Epic (stories, tasks, bugs).
  - Ticket context is provided to Workforce roles as part of the prompt (ticket_id, title, summary, acceptance criteria, etc.).

Backlog artifacts are the *source of truth* for:

- Scope and acceptance criteria
- Role orchestration plans
- Relationships between Epics and tickets

Workforce roles should:
- Treat the backlog as the canonical place for “what” and “why”
- Avoid expanding scope beyond what’s defined in the Epic/ticket without explicitly calling it out as follow-up work
