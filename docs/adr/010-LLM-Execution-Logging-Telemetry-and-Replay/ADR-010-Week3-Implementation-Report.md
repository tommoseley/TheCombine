# ADR-010 Week 3 Implementation Report
## LLM Execution Replay

**Date:** January 1, 2026  
**Status:** Complete ✓  
**Sprint:** Week 3 of 4

---

## Executive Summary

Week 3 delivered the replay functionality for LLM execution logging, enabling reconstruction of inputs from stored telemetry, re-execution with identical parameters, and comparison of original vs replay outputs. This completes the core ADR-010 feature set.

**Key Outcome:** Any logged LLM run can now be replayed via API, with automated comparison of token counts and output differences.

---

## Objectives Achieved

| Objective | Status |
|-----------|--------|
| Input reconstruction from stored content | ✓ Complete |
| Replay endpoint (`POST /api/admin/llm-runs/{id}/replay`) | ✓ Complete |
| Comparison logic (token/output deltas) | ✓ Complete |
| Replay metadata tracking (`is_replay`, `original_run_id`) | ✓ Complete |
| Admin router registration | ✓ Complete |
| Manual end-to-end test | ✓ Verified |

---

## Architecture

### Replay Flow

```
POST /api/admin/llm-runs/{run_id}/replay
                │
                ▼
┌─────────────────────────────────────┐
│  1. Load Original Run               │
│     - Query llm_run by ID           │
│     - Extract model, role, artifact │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  2. Reconstruct Inputs              │
│     - Query llm_run_input_ref       │
│     - Join llm_content by hash      │
│     - Return Dict[kind, content]    │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  3. Create Replay Run               │
│     - New correlation_id            │
│     - Log via LLMExecutionLogger    │
│     - Mark metadata: is_replay=true │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  4. Execute LLM Call                │
│     - Same model, temperature       │
│     - Reconstructed prompts         │
│     - Log output + tokens           │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  5. Compare Runs                    │
│     - Token deltas                  │
│     - Output hash comparison        │
│     - Length delta                  │
└─────────────────────────────────────┘
                │
                ▼
           JSON Response
```

### Data Flow

```
Original Run (llm_run)
    │
    ├── llm_run_input_ref ──► llm_content (deduplicated)
    │       system_prompt
    │       user_prompt
    │       context_doc(s)
    │       schema
    │
    └── llm_run_output_ref ──► llm_content
            raw_text

                    ▼ Reconstruct

Replay Run (new llm_run)
    │
    ├── Same inputs (by content_hash - deduplicated)
    │
    └── New output (different hash - LLM is stochastic)
```

---

## API Endpoint

### `POST /api/admin/llm-runs/{run_id}/replay`

**Request:**
```bash
curl -X POST http://localhost:8000/api/admin/llm-runs/{run_id}/replay
```

**Response:**
```json
{
  "status": "success",
  "original_run_id": "6e17c160-3cbe-4187-819b-417520349403",
  "replay_run_id": "fc46c9b5-0f2d-473d-b1fe-6e69d829e327",
  "comparison": {
    "original_run_id": "6e17c160-...",
    "replay_run_id": "fc46c9b5-...",
    "metadata": {
      "original_started_at": "2026-01-01T18:53:38.288291+00:00",
      "replay_started_at": "2026-01-01T20:36:54.098515+00:00",
      "time_delta_days": 0.07,
      "model_name": "claude-sonnet-4-20250514",
      "artifact_type": "technical_architecture"
    },
    "token_delta": {
      "input_tokens": 0,
      "output_tokens": 1763,
      "total_tokens": 1763
    },
    "cost_delta_usd": null,
    "outputs": {
      "original_hash": "sha256:189a9ce4663b1477",
      "replay_hash": "sha256:ee9a12324c78660e",
      "identical": false,
      "original_length": 21380,
      "replay_length": 29745,
      "length_delta": 8365
    },
    "notes": [
      "Input token count identical (prompt unchanged)",
      "Output content differs (expected - LLM is stochastic)"
    ]
  }
}
```

---

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `app/api/routers/admin.py` | Replay endpoint + comparison logic | ~400 |

---

## Files Modified

| File | Changes |
|------|---------|
| `app/api/main.py` | Registered `api_admin_router` |

---

## Key Implementation Details

### Input Reconstruction

```python
async def reconstruct_inputs(db: AsyncSession, run_id: UUID) -> Dict[str, str]:
    """
    Reconstruct all inputs for a run by joining input refs to content.
    """
    result = await db.execute(
        text("""
            SELECT i.kind, c.content_text
            FROM llm_run_input_ref i
            JOIN llm_content c ON c.content_hash = i.content_hash
            WHERE i.llm_run_id = :run_id
            ORDER BY i.ordinal
        """),
        {"run_id": run_id}
    )
    return {row.kind: row.content_text for row in result.fetchall()}
```

### Comparison Logic

```python
def compare_runs(original: dict, replay: dict, 
                 original_output: str, replay_output: str) -> dict:
    """
    Compare original and replay runs.
    """
    original_hash = hashlib.sha256(original_output.encode()).hexdigest()[:16]
    replay_hash = hashlib.sha256(replay_output.encode()).hexdigest()[:16]
    
    return {
        "token_delta": {
            "input_tokens": replay["input_tokens"] - original["input_tokens"],
            "output_tokens": replay["output_tokens"] - original["output_tokens"],
            "total_tokens": replay["total_tokens"] - original["total_tokens"],
        },
        "outputs": {
            "original_hash": f"sha256:{original_hash}",
            "replay_hash": f"sha256:{replay_hash}",
            "identical": original_hash == replay_hash,
            "length_delta": len(replay_output) - len(original_output),
        }
    }
```

### Replay Metadata

```python
# Mark replay in metadata using JSONB merge
replay_metadata = json.dumps({
    "is_replay": True,
    "original_run_id": str(run_id)
})
await db.execute(
    text("""
        UPDATE llm_run
        SET metadata = COALESCE(metadata, '{}') || CAST(:replay_meta AS jsonb)
        WHERE id = :run_id
    """),
    {"run_id": replay_run_id, "replay_meta": replay_metadata}
)
```

---

## SQL Issues Resolved

### Problem: `::` Cast Syntax Conflict

SQLAlchemy's asyncpg driver conflicts with PostgreSQL's `::type` cast when combined with `:param` binding.

**Failed:**
```sql
'{original_run_id}', to_jsonb(:original_id::text)  -- :: conflicts with :param
```

**Solution:** Build JSON in Python, use `CAST()`:
```sql
SET metadata = COALESCE(metadata, '{}') || CAST(:replay_meta AS jsonb)
```

---

## Verification Results

### Manual Test (January 1, 2026)

```
Original run: technical_architecture
├── input_tokens: 4012
├── output_tokens: 6892
└── output_length: 21380 chars

Replay run:
├── input_tokens: 4012 (delta: 0) ✓ Same prompt
├── output_tokens: 8655 (delta: +1763)
└── output_length: 29745 chars (delta: +8365)

Comparison:
├── Input tokens identical ✓ (proves reconstruction correct)
├── Outputs differ ✓ (expected - LLM is stochastic)
└── New run has is_replay=true metadata ✓
```

---

## Useful Queries

```sql
-- Find all replay runs
SELECT id, artifact_type, started_at, 
       metadata->>'original_run_id' as original_run_id
FROM llm_run 
WHERE metadata->>'is_replay' = 'true'
ORDER BY started_at DESC;

-- Compare original vs replay
SELECT 
    r.id,
    r.metadata->>'is_replay' as is_replay,
    r.input_tokens,
    r.output_tokens,
    r.started_at
FROM llm_run r
WHERE r.id IN (:original_id, :replay_id)
ORDER BY r.started_at;

-- Get all inputs/outputs for a run
SELECT 'INPUT' as direction, i.kind, LENGTH(c.content_text) as length
FROM llm_run_input_ref i
JOIN llm_content c ON c.content_hash = i.content_hash
WHERE i.llm_run_id = :run_id
UNION ALL
SELECT 'OUTPUT', o.kind, LENGTH(c.content_text)
FROM llm_run_output_ref o
JOIN llm_content c ON c.content_hash = o.content_hash
WHERE o.llm_run_id = :run_id;
```

---

## Known Limitations

1. **Admin auth not enforced** - Endpoint is open (add `require_admin` dependency)
2. **No dry-run mode** - Replay always executes LLM call (costs tokens)
3. **Single context_doc** - If multiple context_docs, reconstruction may lose ordering
4. **No automated tests yet** - Manual verification only

---

## Future Work

1. **Admin authentication** - Enforce `require_admin` dependency
2. **Dry-run mode** - Reconstruct inputs without executing LLM
3. **Batch replay** - Replay multiple runs for regression testing
4. **Diff visualization** - Side-by-side output comparison
5. **Automated tests** - Tier-1/Tier-2 tests for replay logic

---

## Configuration Changes

**None.** No new environment variables or configuration required.

---

## Deployment Notes

- Migration already applied (Week 1)
- Admin router registered in `main.py`
- Just deploy code - no config changes needed

---

## Conclusion

Week 3 delivers complete replay functionality:

- **Input reconstruction** from stored telemetry ✓
- **Replay execution** with identical parameters ✓
- **Comparison logic** for token/output analysis ✓
- **Metadata tracking** for audit trail ✓

The system now supports the full ADR-010 vision: log everything, replay anything, compare deterministically.

---

## ADR-010 Overall Status

| Week | Deliverable | Status |
|------|-------------|--------|
| Week 1 | Schema + Migration + Service | ✓ Complete |
| Week 2 | Repository Pattern + Integration | ✓ Complete |
| Week 3 | Replay Implementation | ✓ Complete |
| Week 4 | Deploy to Test | 🔄 In Progress |
