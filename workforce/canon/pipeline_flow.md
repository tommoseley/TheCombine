PIPELINE_FLOW_VERSION=1.0
# Pipeline Flow — Version 1 (Canonical)

**System:** The Combine  
**Component:** Orchestrator + Mentor/Worker Pipeline  
**Status:** Canonical and Binding  
**Last Updated:** v1.0

This document defines the canonical Pipeline Flow for The Combine.  
All Orchestrator behavior must strictly comply with this specification.  
Mentors and Workers must operate within the boundaries defined here.

Markdown formatting is for human readability only.  
The **semantic text** is binding canonical instruction.

---

# 1. Overview

Pipeline Flow v1 is a structured, mentor-centric system that transforms human intent into high-quality, shippable software artifacts.

The **Orchestrator** manages the entire pipeline.  
The Orchestrator invokes **Mentors only**.  
Mentors invoke their respective **Workers** and guarantee quality before returning artifacts.

Workers never communicate with the Orchestrator directly.

The pipeline proceeds through six phases in strict order:

1. PM Phase  
2. Architect Phase  
3. BA Phase  
4. Developer Phase  
5. QA Phase  
6. Commit Phase  

No phase may be skipped, merged, reordered, or reinterpreted.

---

# 2. Phase Sequence (Strict Order)

The Orchestrator must execute phases in this exact sequence:

### 1. PM Phase  
Produces: **Epic**

### 2. Architect Phase  
Produces: **Architectural Notes**

### 3. BA Phase  
Produces: **BA Specification**

### 4. Developer Phase  
Produces: **Proposed Change Set**

### 5. QA Phase  
Produces: **Approval or Rejection**

### 6. Commit Phase  
Produces: **Git Commit**

All advancement requires Mentor certification that the phase's artifact is complete and acceptable.

---

# 3. Phase Definitions

## 3.1 PM Phase
**Input:** Human intent  
**Output:** Epic  
**Orchestrator Action:** Invoke PM Mentor

**PM Mentor must:**
- Interpret human input  
- Invoke PM Worker to form the Epic  
- Ensure business value, scope, and constraints are captured  
- Iterate Worker calls until the Epic is high quality

---

## 3.2 Architect Phase
**Input:** Epic  
**Output:** Architectural Notes  
**Orchestrator Action:** Invoke Architect Mentor

**Architect Mentor must:**
- Invoke Architect Worker to generate design notes  
- Ensure system implications, constraints, and risks are clear  
- Iterate until the notes support BA and Dev work

---

## 3.3 BA Phase
**Input:** Epic + Architectural Notes  
**Output:** BA Specification  
**Orchestrator Action:** Invoke BA Mentor

**BA Mentor must:**
- Invoke BA Worker to produce a detailed specification  
- Ensure requirements are unambiguous and implementable  
- Iterate until complete and ready for development

---

## 3.4 Developer Phase
**Input:** BA Specification + repository context  
**Output:** Proposed Change Set  
**Orchestrator Action:** Invoke Dev Mentor

**Dev Mentor must:**
- Invoke Developer Worker to implement code and tests  
- Validate alignment with the BA Specification  
- Iterate Worker calls until code quality is acceptable

---

## 3.5 QA Phase
**Input:** Proposed Change Set + BA Specification  
**Output:** Approval or Rejection  
**Orchestrator Action:** Invoke QA Mentor

**QA Mentor must:**
- Invoke QA Worker to validate correctness and coherence  
- Ensure findings align with BA Specification  
- Iterate QA Worker as needed  
- If unacceptable, signal rejection → Orchestrator returns to Developer Phase  
- If acceptable, provide explicit approval

---

## 3.6 Commit Phase
**Input:** QA Mentor approval  
**Output:** Git commit via `/workforce/commit`  
**Orchestrator Action:** Execute commit and log outcome

Deployment is always human-governed and outside the pipeline.

---

# 4. Error Handling & Recovery

- The pipeline cannot advance until a Mentor certifies the artifact for that phase.  
- If QA rejects the Change Set:
  - Orchestrator must re-invoke Dev Mentor with feedback
- If any Mentor indicates upstream ambiguity:
  - Orchestrator may re-run PM, Architect, or BA phases as needed  
- Mentors manage Worker iteration; Orchestrator does not invoke Workers directly.

---

# 5. Behavioral Rules (Binding)

1. The Orchestrator is the sole controller of phase sequencing.  
2. Orchestrator communicates **only** with Mentors.  
3. Mentors communicate with Workers, not with the Orchestrator about other roles.  
4. Workers never communicate with the Orchestrator.  
5. Phases run strictly in order.  
6. No skipping, merging, or reordering of phases is permitted.  
7. CI/CD and deploy steps are human-governed.  
8. All logs must reflect correct canonical flow.  
9. If any instruction conflicts with this document, this document takes precedence.

---

# 6. Canonical Summary Diagram (Authoritative Structure)

          Human Intent
                |
                v
          [ Orchestrator ]
                |
                v
          [ PM Mentor ]
                |
      (PM Worker loops internally)
                |
                v
             [ Epic ]
                |
                v
      [ Architect Mentor ]
                |
 (Architect Worker loops internally)
                |
                v
    [ Architectural Notes ]
                |
                v
         [ BA Mentor ]
                |
   (BA Worker loops internally)
                |
                v
         [ BA Specification ]
                |
                v
         [ Dev Mentor ]
                |
   (Dev Worker loops internally)
                |
                v
    [ Proposed Change Set ]
                |
                v
         [ QA Mentor ]
                |
   (QA Worker loops internally)
                |
       (approve / reject)
                |
                v
          [ Orchestrator ]
                |
    if approve → commit to Git
                |
                v
  [ Git → CI/CD → Human Deploy ]

This diagram is binding. All Orchestrator behavior must match it exactly.

---

# 7. Canon Enforcement

The Orchestrator must:

- Load and enforce this document at startup  
- Reload if drift is detected  
- Treat all semantic text here as canonical authority  
- Log violations and correct behavior immediately  

If unclear, the Orchestrator must choose the most literal interpretation of this document.

---

# End of `pipeline_flow_v1.md`

