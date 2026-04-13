# WS-CLEANUP-002: Auth Stack Unification

## Status: Draft

## Governing References

- Codex Code Review (2026-03-27) — High finding: auth dual service stack
- ADR-008 (Authentication)

## Verification Mode: A

## Allowed Paths

- app/auth/
- tests/auth/
- tests/

---

## Objective

Eliminate the dead `SessionService`/`UserService` abstraction in `app/auth/services.py` and the unused `AuthMiddleware` class in `app/auth/middleware.py`. The live auth path uses `AuthService` (service.py) via FastAPI dependency injection (dependencies.py). The legacy code is unreferenced in production and creates confusion.

---

## Preconditions

- 4857 tests passing
- Confirmed: `SessionService` is only imported by `middleware.py` (AuthMiddleware class) and `tests/auth/test_session.py`
- Confirmed: `AuthMiddleware` class is never registered in `main.py`
- Confirmed: All routes and dependencies use `AuthService` from `service.py`

---

## Scope

### In Scope

1. Delete `app/auth/services.py` — contains `SessionService` and `UserService` (dead code)
2. Remove the `AuthMiddleware` class from `app/auth/middleware.py` — never registered, depends on deleted `SessionService`. Keep the decorator functions (`require_auth`, `require_permission`) if they exist and are used.
3. Update `app/auth/__init__.py` — remove exports of `SessionService`, `UserService`, and any repository classes that were only used by `services.py`
4. Delete or update `tests/auth/test_session.py` — tests for dead code

### Out of Scope

- Modifying `AuthService` (service.py) — working correctly
- Modifying `dependencies.py` — working correctly
- Modifying `routes.py` — working correctly
- Adding new auth features
- Changing session duration, token format, or any auth behavior

---

## Prohibited Actions

- Do not modify `AuthService` in `service.py`
- Do not modify the working auth dependency injection in `dependencies.py`
- Do not modify OAuth routes in `routes.py`
- Do not change any auth behavior — this is dead code removal only

---

## Procedure

### Phase 1: Verify Assumptions

1. Grep for all imports of `SessionService` across the codebase — confirm only in `middleware.py` and `test_session.py`
2. Grep for all imports of `UserService` — confirm no production usage
3. Grep for `AuthMiddleware` usage in `main.py` or any app startup — confirm it is never registered
4. Check `app/auth/middleware.py` for decorator functions that may be used elsewhere

### Phase 2: Remove Dead Code

5. Delete `app/auth/services.py`
6. Remove the `AuthMiddleware` class from `app/auth/middleware.py` (keep file if decorators remain; delete file if empty after removal)
7. Update `app/auth/__init__.py` to remove dead exports (`SessionService`, `UserService`, related repositories)
8. Delete `tests/auth/test_session.py` (tests dead SessionService)

### Phase 3: Verify

9. Run `python -m pytest tests/ -x -q` — all tests must pass
10. Run Tier 0

---

## Verification Checklist

- [ ] `app/auth/services.py` deleted
- [ ] `AuthMiddleware` class removed from `middleware.py`
- [ ] `__init__.py` no longer exports dead classes
- [ ] No remaining imports of `SessionService` or `UserService` in production code
- [ ] `test_session.py` deleted or updated
- [ ] All tests pass
- [ ] Tier 0 passes

## Definition of Done

Single auth path: `AuthService` via dependency injection. No dead `SessionService`/`UserService`/`AuthMiddleware` code remains. All tests pass.
