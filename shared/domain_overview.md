# Workbench Domain Overview

The Workbench is an AI-enabled development environment that coordinates a **Workforce** of specialized AI roles
(Product Manager, BA, Architect, Developers, Mentors, etc.) to deliver working software.

Key ideas:

- The Workbench manages **tickets** (e.g., `AUTH-100`) that represent coherent units of work.
- For each ticket, the **orchestrator** spins up a set of Workforce roles with well-defined responsibilities.
- The Workforce produces:
  - Requirements (PM, BA)
  - Designs (Architect)
  - Code and tests (Developers, Lead Dev)
  - Reviews and improvements (Mentors)
- Only the Workbench backend (via the Workforce git module) interacts with GitHub and the repository.

Branches:

- `main` – production-quality, canonical source of truth.
- `workforce-sandbox` – branch where Workforce-driven changes are committed before review/merge.

Workflow at a high level:

1. Ticket is defined or selected.
2. PM/BA clarify and structure the work.
3. Architect designs the approach.
4. Devs implement code and tests.
5. Lead Dev integrates proposals and commits via `/workforce/commit`.
6. Tests run, work is reviewed, and then merged into `main`.
