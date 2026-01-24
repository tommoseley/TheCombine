# Work Statement Inventory

_Last updated: 2026-01-22_

This document provides a complete inventory of Work Statements for The Combine.

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **Draft** | Work defined but not yet started or accepted |
| **Accepted** | Approved for implementation |
| **In Progress** | Currently being implemented |
| **Complete** | Implemented and verified |
| **Superseded** | Replaced by different approach |
| **Abandoned** | Intentionally not pursued |

---

## Concierge & Intake System

| WS | Title | Status | Date | Notes |
|----|-------|--------|------|-------|
| WS-CONCIERGE-001 | Concierge Project Ingestion | **Superseded** | 2026-01-22 | Replaced by mechanical sufficiency approach |
| WS-INTAKE-001 | Interpretation Panel | **Complete** | 2026-01-22 | Review & Lock checkpoint |
| WS-ADR-025-INTAKE-GATE | Intake Gate Implementation | **Complete** | 2026-01-22 | Simplified from original spec |
| WS-INTAKE-ENGINE-001 | Document Workflow Engine | **Complete** | 2026-01-22 | Phases 1-5 implemented |
| WS-INTAKE-WORKFLOW-001 | Workflow Plan | **Complete** | 2026-01-22 | concierge_intake.v1.json |

---

## Pre-Generation Clarification (ADR-012)

| WS | Title | Status | Date | Notes |
|----|-------|--------|------|-------|
| WS-PGC-001 | PGC Gate Implementation | Draft | 2026-01-22 | 6 phases, ~20 hours |

---
## Document System (ADR-034)

| WS | Title | Status | Date | Notes |
|----|-------|--------|------|-------|
| WS-ADR-034-POC | Proof of Concept | **Complete** | - | Initial validation |
| WS-ADR-034-EXP | Experiment 1 | **Complete** | - | - |
| WS-ADR-034-EXP2 | Experiment 2 | **Complete** | - | - |
| WS-ADR-034-EXP3 | Experiment 3 | **Complete** | - | - |
| WS-ADR-034-DISCOVERY | Discovery Document | **Complete** | - | - |
| WS-ADR-034-EPIC-DETAIL | Epic Detail | **Complete** | - | - |

---

## BFF & Schema Infrastructure

| WS | Title | Status | Date | Notes |
|----|-------|--------|------|-------|
| WS-001 | Epic Backlog BFF Refactor | **Complete** | - | - |
| WS-002 | Schema Registry Implementation | **Complete** | - | - |
| WS-003 | Fragment Registry Implementation | **Complete** | - | - |
| WS-004 | Remove HTML From BFF | **Complete** | - | - |

---

## Story Backlog

| WS | Title | Status | Date | Notes |
|----|-------|--------|------|-------|
| WS-STORY-BACKLOG-VIEW | Story Backlog View | Draft | - | Not started |
| WS-STORY-BACKLOG-COMMANDS-SLICE-1 | Commands Slice 1 | Draft | - | Not started |
| WS-STORY-BACKLOG-COMMANDS-SLICE-2 | Commands Slice 2 | Draft | - | Not started |

---

## Infrastructure

| WS | Title | Status | Date | Notes |
|----|-------|--------|------|-------|
| WS-ADR-035-Durable-LLM-Queue | Durable LLM Queue | Draft | - | Thread infrastructure exists; full queue deferred |
| WS-DOCUMENT-SYSTEM-CLEANUP | Document System Cleanup | Draft | - | - |
| WS-DOCUMENT-VIEWER-TABS | Document Viewer Tabs | Draft | - | - |

---

## Maintenance Notes

- Update this document when Work Statement status changes
- Work Statements are append-only; superseded ones remain for history
- Group related Work Statements by feature area
- Include completion date when marking Complete

---

## WS-ADR-041-001: Prompt Template Include System Implementation

**Status:** Accepted  
**ADR:** ADR-041 (Accepted)  
**Scope:** Multi-commit  
**Estimate:** 13 hours  

**Phases:**
1. Core Data Structures (AssembledPrompt, error types)
2. Token Scanner (regex patterns)
3. File Loading (UTF-8, LF normalization)
4. Token Resolution (Workflow Tokens, Template Includes)
5. Assembly and Hashing (SHA-256)
6. Test Fixtures
7. Golden Tests (7 test cases)
8. Audit Logging Integration
9. CI Prompt Compile Job
10. PGC Prompt Migration

**Key Deliverable:** `PromptAssembler` class producing deterministic, hashable prompts.