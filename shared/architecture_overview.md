# Architecture Overview

The Workbench is a web application with:

- A FastAPI backend (Python).
- A frontend (HTML/HTMX or similar).
- A Workforce module that enables AI-driven changes to the codebase through a safe gateway.

Key backend concepts:

- **Auth**: Magic-link based login, session model, and rate-limited email delivery.
- **Workforce Git Module**: Provides `/workforce/commit`, which:
  - Reads a set of file changes (`path`, `content`).
  - Writes them into a local clone.
  - Commits and pushes to `workforce-sandbox`.

Design constraints:

- Only the backend talks to GitHub.
- AI roles do not directly read from or write to the filesystem.
- The Lead Dev is responsible for the code-level integrity of changes.

Future extensions:

- Role-based bootstrap configuration.
- Ticket orchestration with multiple roles running in sequence or in parallel.
- CI/CD integration triggered from `workforce-sandbox`.
