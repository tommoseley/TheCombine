---
name: session-management
description: Start and close AI sessions with proper context loading and log writing. Use when beginning a new session, closing a session, or backfilling session logs from previous chats.
---

# Session Management

## How to Start a New AI Session

Before any work:

1. Read `CLAUDE.md` (this file, in Project Knowledge)
2. **Use tools to read** `docs/PROJECT_STATE.md` from filesystem
3. Scan `docs/session_logs/` for recent context
4. Scan `docs/adr/` for architectural guidance and a future vision
5. Summarize back:
   - System purpose
   - Current state
   - Active constraints (ADRs)
   - Next logical work
6. Ask for confirmation before proceeding

## How to Close a Session

When the user says **"Prepare session close"** (or similar):

1. Write session summary to `docs/session_logs/YYYY-MM-DD.md` (filesystem)
   - Use fixed template (scope, decisions, implemented, commits, open threads, risks)
   - No prose, no reflection - facts only
   - Include git commits/PRs if applicable
2. Update `docs/PROJECT_STATE.md` (filesystem)
   - Current state
   - Handoff notes for next session
3. Pause and ask: **"Ready to close, or do you want to continue?"**

Session summaries are **immutable logs**. They capture "what happened" - not decisions (ADRs) or current state (PROJECT_STATE.md).

If multiple sessions occur on the same day, use suffix: `2026-01-02.md`, `2026-01-02-2.md`

## PROJECT_STATE.md Update Rules

At session close, update `docs/PROJECT_STATE.md` with:
- Current focus (what was completed, what is in progress)
- Test suite count
- Handoff notes for next session
- Open threads and known issues

## Backfilling Session Logs (For Previous Chats)

Use this prompt in old chat sessions to generate retroactive session logs:

---

**Instruction**

You are writing a Session Summary Log for this conversation.
This log is used to restore context in future AI sessions. Accuracy and restraint are more important than completeness.

**Hard Constraints (Non-Negotiable)**

1. **No Invention**
   - Do NOT infer decisions, implementations, or intent.
   - If something was discussed but not explicitly decided or implemented, it must NOT appear under those sections.

2. **Explicit Uncertainty Handling**
   - If you are unsure whether an item qualifies, omit it.
   - Do NOT hedge or speculate.
   - Absence is preferred over incorrect inclusion.

3. **Factual Tone Only**
   - No reflection, justification, or commentary.
   - No "we learned", "this was important", or similar phrasing.
   - Use short, declarative bullets only.

4. **Scope Discipline**
   - "Decisions Made" = explicit agreements or resolutions.
   - "Implemented" = concrete artifacts created or modified.
   - "Discussed" items belong nowhere unless they resulted in a decision or implementation.

5. **No New Information**
   - Do NOT introduce new risks, interpretations, or connections.
   - Only capture what occurred in this session.

**Output Requirements**

- Use the date of the last interaction in this chat (not today) as `YYYY-MM-DD`
- Output only a single markdown document
- Filename format: `docs/session_logs/YYYY-MM-DD.md`
- Follow the template exactly
- Do not add, remove, or rename sections
- If a section has no valid entries, write `- None`

**Template (Must Be Used Verbatim)**

```
# Session Summary - YYYY-MM-DD

## Scope
-

## Decisions Made
-

## Implemented
-

## Updated or Created
-

## Commits / PRs
-

## Open Threads
-

## Known Risks / Drift Warnings
-
```

**Final Instruction**

Write the session summary now.
If you cannot confidently populate a section, leave it as `- None`.
