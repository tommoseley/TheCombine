# Glossary

**Ticket**  
A unit of work, such as `AUTH-100`. Contains a problem statement, scope, and acceptance criteria.

**Workbench**  
The overall system that hosts the Workforce, orchestrates roles, and owns integration with GitHub.

**Workforce**  
The collection of AI roles (PM, BA, Architect, Dev, Lead Dev, Mentors) working together on a ticket.

**Orchestrator**  
The controlling component that:
- Loads role instructions from git.
- Spins up the Workforce roles for a ticket.
- Routes messages and artifacts between roles.
- Dispatches final code changes to the Workforce git module.

**Mentor**  
A role focused on review, critique, and improvement. Mentors do not own final delivery; they help others do better work.

**Artifact**  
Any structured output from a role: requirements, designs, code proposals, tests, review notes, etc.

**Canonical**  
The official, accepted version of an artifact or file at a point in time (e.g., the version Lead Dev will commit).

**Workforce Git Module**  
Backend module that handles repo operations (`clone`, `checkout`, `commit`, `push`) via `/workforce/commit`. This is the only path to GitHub.
