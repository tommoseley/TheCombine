# Derived Fields in Views (Frozen)

| | |
|---|---|
| **Status** | Frozen |
| **Effective** | 2026-01-08 |
| **Governing ADR** | ADR-034 |

> ⚠️ **Governance Requirement**
>
> Derivation rules are mechanical, deterministic, and frozen.
> Changes require explicit governance approval.

---

## Purpose

View docdefs (e.g., `EpicSummaryView`) may include derived fields computed from canonical data. These derivations must be:

- **Deterministic** — same input always produces same output
- **Bounded** — limited scope, no complex logic
- **Documented** — rules explicitly stated
- **Test-covered** — unit tests validate behavior

---

## Frozen Derivation Rules

### `derive_risk_level(risks: List[RiskV1]) -> "low" | "medium" | "high"`

**Location:** `app/domain/services/render_model_builder.py`

**Rule:**
1. If any risk has `likelihood="high"` → return `"high"`
2. Else if any risk has `likelihood="medium"` → return `"medium"`
3. Else → return `"low"`

**Edge cases:**
- Empty list → `"low"`
- Missing `likelihood` field → treated as `"low"`
- Non-dict items → skipped

**Tests:** `tests/domain/test_derived_fields.py`

---

### `derive_integration_surface(obj: Dict) -> "external" | "none"`

**Location:** `app/domain/services/render_model_builder.py`

**Rule:**
1. If `external_integrations` count > 0 → return `"external"`
2. Else → return `"none"`

**Edge cases:**
- Missing field → `"none"`
- Container form `{"items": [...]}` → handled
- Empty list → `"none"`

**Tests:** `tests/domain/test_derived_fields.py`

---

### `derive_complexity_level(obj: Dict) -> "low" | "medium" | "high"`

**Location:** `app/domain/services/render_model_builder.py`

**Canonical field names (frozen):**
- `systems_touched` — array of strings
- `key_interfaces` — array of strings
- `dependencies` — array of DependencyV1 items (NOT block-wrapped)
- `external_integrations` — array of strings

**Rule:**
```
total = |systems_touched| + |key_interfaces| + |dependencies| + |external_integrations|
```
- 0-3 → `"low"`
- 4-7 → `"medium"`
- 8+ → `"high"`

**Edge cases:**
- Missing fields → count as 0
- Container form `{"items": [...]}` → handled
- Empty object → `"low"`

**Tests:** `tests/domain/test_derived_fields.py`

---

## Anti-Patterns

- ❌ Complex scoring algorithms
- ❌ Weighted averages
- ❌ Machine learning inference
- ❌ External service calls
- ❌ Configuration-driven rules

Derivations should be explainable in one sentence.

---

## Adding New Derivations

1. Document the rule in this file
2. Implement as a pure function in `render_model_builder.py`
3. Add unit tests
4. Get governance approval before merge

---

*Last updated: 2026-01-08*


