from experience.app.orchestrator.roles import build_role_registry, build_role_prompt

ticket_context = """
Ticket: AUTH-101
Title: Add /auth/me endpoint for current user

Summary:
- Implement a new GET /auth/me endpoint.
- When a valid session exists, return 200 and JSON containing at least the user's email (and any other relevant session fields).
- When no valid session exists or the session is expired, return 401 (or 403 if that better matches existing patterns).

Constraints:
- Reuse the existing auth/session model and get_current_user helper from AUTH-100.
- Do not change the login flow or magic-link validation behavior.
- Keep changes minimal and localized to the auth module and its tests.

Acceptance Criteria:
- GET /auth/me with a valid session returns 200 and JSON with the user's email.
- GET /auth/me with no session or an expired session returns 401.
- New tests cover both success and failure cases.
- Existing auth tests continue to pass."""


registry = build_role_registry()
print("Roles found:", list(registry.keys()))
pm_prompt = build_role_prompt("orchestrator", ticket_context, registry)
print(pm_prompt)
