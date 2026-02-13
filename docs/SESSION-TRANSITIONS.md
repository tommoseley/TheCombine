# Session Transition Protocol

**Purpose:** Ensure continuity when closing one Claude session and starting another.

---

## Before Ending a Session

### 1. Verify All Files Written

Ask Claude to confirm all discussed files are saved to disk:

```
Please verify all files we created this session are written to Windows.
```

### 2. Update ADR Inventory

If any ADR status changed, ensure `docs/adr/ADR-INVENTORY.md` reflects current state.

### 3. Request Session Summary

Ask for a compact summary suitable for the next session:

```
Please provide a session summary for continuity.
```

The summary should capture:
- Decisions made
- Files created/modified
- ADR status changes
- Open questions
- Next steps

---

## Starting a New Session

### 1. Provide Context

Begin with a brief orientation:

```
Continuing work on The Combine. Last session we [brief summary].
Next priority: [specific task].
```

### 2. Reference Project Knowledge

Claude has access to project files. Point to specific documents if needed:

```
Please review docs/MVP-ROADMAP.md for current phase.
```

### 3. Check Transcript

If details are needed from a prior session, the transcript is available:

```
/mnt/transcripts/[timestamp]-[topic].txt
```

---

## What Gets Preserved

| Artifact | Location | Survives Sessions |
|----------|----------|-------------------|
| ADRs | `docs/adr/` | ✅ Yes |
| Roadmap | `docs/MVP-ROADMAP.md` | ✅ Yes |
| Implementation Model | `docs/adr/027-workflow-definition/` | ✅ Yes |
| Session Transcripts | `/mnt/transcripts/` | ✅ Yes |
| Memory | Claude's memory system | ✅ Yes |
| Unsaved work | Claude's container | ❌ No |

---

## Session Naming Convention

Transcripts follow: `YYYY-MM-DD-HH-MM-SS-[topic].txt`

Examples:
- `2026-01-02-15-30-00-adr-012-acceptance.txt`
- `2026-01-03-09-00-00-phase0-validator.txt`

---

## Quick Checklist

**End of session:**
- [ ] All files written to Windows
- [ ] ADR Inventory updated
- [ ] Summary captured (in transcript or explicitly)

**Start of session:**
- [ ] State current priority
- [ ] Reference relevant docs
- [ ] Confirm starting point
