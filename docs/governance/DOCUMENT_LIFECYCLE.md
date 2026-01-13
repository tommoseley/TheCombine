# Document Lifecycle Contract v1.0

> **Frozen**: This contract defines document states and transitions per ADR-036.

## Philosophy

> **"Partial is not broken. Partial is honest."**

Documents have explicit lifecycle states. Partial documents are valid documents that show what's available. Staleness is informational, not destructive.

## The Five States

| State | Description | User Experience |
|-------|-------------|-----------------|
| `missing` | Document does not exist | "Build" CTA only |
| `generating` | LLM actively producing content | Skeleton UI with progress |
| `partial` | Some sections complete, others pending | Available sections + "Continue" CTA |
| `complete` | All sections populated | Full document |
| `stale` | Upstream dependency changed | Full document + amber indicator |

## State Transitions

```
missing ──────────► generating
                        │
                        ├──► partial ◄──┐
                        │       │       │
                        │       ▼       │
                        └──► complete ──┘
                                │
                                ▼
                             stale
                                │
                                ▼
                           generating
```

### Valid Transitions

| From | To | Trigger |
|------|-----|---------|
| `missing` | `generating` | `generate` command |
| `generating` | `partial` | First section completes |
| `generating` | `complete` | All sections complete |
| `partial` | `generating` | `generate section` command |
| `partial` | `complete` | All sections complete |
| `partial` | `stale` | Upstream change |
| `complete` | `stale` | Upstream change or `mark-stale` command |
| `stale` | `generating` | `regenerate` command |

### Invalid Transitions

| From | To | Why Invalid |
|------|-----|-------------|
| `complete` | `generating` | Must go through `stale` first |
| `stale` | `complete` | Must regenerate, not just clear flag |
| `missing` | `complete` | Must go through generation |

## Staleness Propagation

When a document becomes stale, its downstream dependents are automatically marked stale.

| When This Changes | These Become Stale |
|-------------------|-------------------|
| Project Discovery | Epic Backlog |
| Epic Backlog | Story Backlog, Technical Architecture |
| Individual Epic | Story Details for that epic |
| Technical Architecture | Story Details |

## Rendering by State

| State | Rendering |
|-------|-----------|
| `missing` | Empty state with "Build" CTA |
| `generating` | Skeleton placeholders, progress indicator |
| `partial` | Completed sections rendered, pending sections show placeholder |
| `complete` | Full document rendered |
| `stale` | Full document + amber "stale" badge, "Regenerate" CTA |

## Invariants

1. **Partial documents are valid** - They render what's available
2. **Stale documents remain viewable** - Staleness is a flag, not a block
3. **State transitions are atomic** - No intermediate states
4. **Staleness propagates downstream only** - Never upstream
5. **Regeneration is always explicit** - Never automatic

## Database Schema

```sql
-- documents table
lifecycle_state ENUM('missing', 'generating', 'partial', 'complete', 'stale')
state_changed_at TIMESTAMP WITH TIME ZONE
is_stale BOOLEAN  -- Legacy compatibility, synced with lifecycle_state
```

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Change badge colors | No |
| Change CTA labels | No |
| Add new lifecycle state | Yes |
| Change transition rules | Yes |
| Change propagation rules | Yes |

---

_Frozen: 2026-01-12 (ADR-036, WS-DOCUMENT-SYSTEM-CLEANUP Phase 3)_