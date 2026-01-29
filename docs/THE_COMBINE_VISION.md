# The Combine - Product Vision

Created: 2026-01-27
Context: Session discussion about the end-state vision for The Combine

## The Name

The Combine. Named for the agricultural combine harvester.

Before the combine: Hundreds of workers, weeks of labor, manual reaping,
threshing, winnowing.

After the combine: One machine, one operator, does it all. Not replacing
the farmer - amplifying them.

The farmer still decides what to plant, when to harvest, which fields need
attention. The combine just does the repetitive, backbreaking work at scale.

## What The Combine Is

The Combine is a document factory. Not a chatbot. Not an assistant. A machine.

The workflow is universal:

```
INPUT: "I want [thing]"
           |
    [Concierge: What kind of thing? What constraints?]
           |
    [Discovery: Understand the domain, goals, scope]
           |
    [Architecture: Structure the solution]
           |
    [Breakdown: Epics/Sections/Phases]
           |
    [Details: Stories/Items/Steps]
           |
OUTPUT: Complete, verified, structured deliverable
```

The only thing that changes is the prompt templates:

| Domain | Discovery | Architecture | Breakdown |
|--------|-----------|--------------|-----------|
| Software | Analyze requirements | Design system | Define epics/stories |
| Business Plan | Analyze market | Structure model | Define sections |
| Party Planning | Understand occasion | Plan logistics | Define tasks |
| Garden Design | Assess space | Design layout | Define phases |

Same stations: PGC, ASM, QA, REM, DONE
Same subway map visualization
Same quality gates
Same operator model

Add a new prompt pack, you get a new factory line.

## The User Experience

```
User: "I want a math testing app for 5-8 year olds"

Concierge: "What math operations? Add/subtract/multiply?"
           "Timed or untimed?"
           "Progress tracking for parents?"
           "Fun theme? Animals? Space? Pirates?"

User: [answers questions]

User: [clicks GENERATE ALL]

[Subway map lights up, station by station]
[Documents flow through the factory]
[User watches the assembly line run]
[Intervenes only when needed - operator model]

Output: Complete software specification with:
  - Discovery document
  - Technical architecture
  - Epic backlog
  - Story backlog with implementation prompts
  - Test specifications
  - Deployment runbooks
```

One sentence in. A few clarifying questions. Then watch the product materialize.

## Beyond Software

Software is just the first workflow. The Combine produces any document type:

- Business strategy documents
- Business plans
- Party planning documents
- Garden plans
- Project proposals
- Research reports
- Training curricula
- Anything that can be structured

Its ALL about the prompts, and those are templatized.

## Parallel Execution with Selective Blocking

When a step gets stuck (QA failure, needs user input), only that downstream
branch stops. The rest of the factory keeps running.

```
epic_backlog                      tech_arch
*--*--*--@--o                    *--*--*--*--*
       QA STUCK!                   STABILIZED
       |                              |
    [WAITING]                    [CAN PROCEED]
```

The operator handles exceptions. The factory keeps producing.

## Self-Improving Factory

When AIs write and tune the prompts:

```
[User runs workflow]
        |
[Documents produced]
        |
[QA failures logged]
[User corrections logged]
[Remediation patterns logged]
        |
[PROMPT OPTIMIZATION AI]
        |
"QA fails 40% on financial projections.
 Users always add 5-year runway in remediation."
        |
--> Update prompt to ask about runway in PGC
        |
[New prompt version]
[A/B test]
[Promote or rollback]
```

The factory optimizes itself.

## The Endgame

Feed The Combine a target document. Let it figure out how to configure
the factory and tune it for an outcome as close to deterministic as AI can get.

```
INPUT: [Example document you love]

        "Heres a business plan that got us $10M funding"
        "Heres a software spec that shipped on time"

[FACTORY CONFIGURATION AI]
  1. Analyze document structure
  2. Infer workflow stages
  3. Generate prompt templates
  4. Define QA criteria
  5. Build PGC questions
  6. Configure dependency graph

[Run against test inputs]
[Compare output to target]
[Tune until output matches]

OUTPUT: [CERTIFIED WORKFLOW]
        "This factory produces documents like your example, reliably."
```

You dont configure the factory. You show it what good looks like.

"Make me more of these."

## Factory Principles

Because its a factory, we apply manufacturing wisdom:

### 1. Eliminate Constraints (Theory of Constraints)
```
Find the bottleneck --> Fix it --> Find the next one

- QA failing too often? --> Improve prompts upstream
- PGC taking too long? --> Better default answers
- Users confused? --> Clearer questions
```

### 2. Reduce Retooling Time (SMED)
```
Switching from "software spec" to "business plan" should be:

NOT: Rewrite everything, new code, weeks of work
BUT: Load different prompt pack, same factory, same stations

- Prompts are data, not code
- Workflows are configuration, not implementation
- QA rules are templates, not hardcoded
```

### 3. Continuous Flow
```
No batching. No waiting. Documents flow the moment dependencies are met.

Epic 1 doesnt wait for Epic 3.
Story 2 flows while Story 1 is in QA.
The line never stops unless it HAS to.
```

### 4. Built-in Quality (Jidoka)
```
Stop and fix, dont pass defects downstream.

QA gates arent optional.
Drift detection catches violations.
Bad output halts THAT track, not the whole factory.
```

## The Challenge

This is scary to sell.

To individuals: "Wait, AI can do my job?"
To companies: "Trust AI for strategy docs?"
To industries: "Automate... thinking?"

But the same fear existed for:
- Assembly lines ("craftsmen obsolete")
- Spreadsheets ("accountants replaced")
- CAD software ("draftsmen gone")
- Compilers ("programmers disappear")

What actually happened: the work changed, the output multiplied.

## The Real Sell

Not "replace humans." Instead:

"Your experts are stuck writing the same documents over and over.
 What if they designed factories instead, and those factories
 produced documents at scale, with their expertise baked in?"

The business plan expert doesnt write 50 plans a year.
They design the business plan factory, tune it, certify it -
and it produces 500.

Expertise becomes infrastructure.

Thats not scary. Thats leverage.

## Summary

The Combine is:
- A document factory, not a chatbot
- Universal workflow, domain-specific prompts
- Visual production line (Subway Map)
- Parallel execution with selective blocking
- Self-improving through logged feedback
- Configured by example, not by hand
- Industrial manufacturing principles applied to knowledge work

One expert. One factory. Hundreds of outputs.

Thats Industrial AI.

---

IF we do it right.
