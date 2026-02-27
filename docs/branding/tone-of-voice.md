# Tone of Voice

## Source Documents

- [Design Manifesto](../archive/the-combine-design-manifesto.md) -- "Calm Authority" and "Boring Buttons"
- [UX Reference](../project/THE_COMBINE_UX_REFERENCE.md) -- status communication and button enablement
- [Lobby Spec](../design/lobby-spec.md) -- marketing-adjacent language for logged-out experience
- [Branding Instructions](../branding_instructions.md) -- factory metaphor hierarchy

---

## Core Tone

The Combine UI must feel:

- **Calm** -- no urgency theater
- **Precise** -- no ambiguity
- **Intentional** -- every word earns its place
- **Serious** -- this is enterprise infrastructure

It must NOT feel:

- Friendly
- Playful
- Decorative
- Trend-driven

**If a copy choice makes the UI feel "nice" but less clear, it is wrong.**

---

## Button Labels

Buttons use explicit verbs that answer "what happens when I click this?"

| Good | Bad | Why |
|------|-----|-----|
| View Document | Open | "Open" is vague -- open where? how? |
| Start Production | Go | "Go" has no semantic content |
| Answer Questions | Continue | "Continue" does not describe the action |
| Generate | Create Now! | No exclamation marks, no urgency |
| Approve | Looks Good | No conversational tone |
| Delete | Remove This | Keep it terse |

Rules:
- One or two words preferred
- Verb-first (imperative mood)
- No personality, no hedging
- No confirmation phrasing ("Yes, delete" is acceptable in confirmation dialogs only)

---

## Status Text

Status messages are factual, never emotional.

| Good | Bad | Why |
|------|-----|-----|
| Stabilized | Done! | No exclamation marks |
| In Progress | Working on it... | No conversational tone |
| Blocked | Oops! Something went wrong | No personality |
| Ready | Ready to go! | No enthusiasm |
| Waiting for: Technical Architecture | Hmm, looks like we need the TA first | No hedging or "we" |
| Inputs changed -- review recommended | Heads up! Things may have changed | No casual alerts |
| Disconnected | Uh oh, connection lost | No personality |

---

## Error Messages

Errors state what happened and what the user can do. Nothing more.

| Good | Bad |
|------|-----|
| Failed to save. Check connection and retry. | We're sorry, something went wrong! Please try again later. |
| Missing required input: project name | Please make sure you've filled in all the required fields |
| Cannot delete: project must be archived first | Whoops! You need to archive this project before deleting it |

Rules:
- State the problem factually
- State the remedy if one exists
- No apologies ("We're sorry")
- No hedging ("Something may have gone wrong")
- No exclamation marks

---

## The Industrial Vocabulary

Use the factory metaphor consistently in all user-facing text:

| Term | Meaning | Do NOT Use |
|------|---------|-----------|
| Production Line | The workflow view | Dashboard, workspace, board |
| Project | A workpiece being processed | Job, task, ticket |
| Document | A governed artifact | File, page, record |
| Station | A processing step | Step, stage, phase |
| Stabilized | Complete and immutable | Done, finished, approved |
| Quality Gate | Verification checkpoint | Review, check |

---

## Lobby Language (Logged Out)

The lobby is marketing-adjacent but product-owned. It bridges the gap between public-facing and production-facing language.

Principles:
- Emphasize **discipline over speed**
- Emphasize **traceability over creativity**
- Emphasize **production over prompting**
- No feature lists
- No technical jargon
- No competitor comparisons

The tagline is: **"Industrial AI for Knowledge Work"**

---

## Labels and Captions

### Uppercase Labels
Category labels (DOCUMENT, WORK PACKAGE, STATE) are always uppercase with letter-spacing. They name what something IS, not what it does.

### Descriptions
Descriptions under node names are factual summaries. One line. No marketing.

| Good | Bad |
|------|-----|
| Initial project intake and requirements | Your first step to an amazing project! |
| System architecture and technical decisions | Where the magic happens |
| Phased implementation roadmap | Let's plan the work |

---

## Anti-Patterns

Never use in the production interface:

- First-person AI voice ("I think...", "I found...", "Let me...")
- Emoji in status text (reserved for streaming build progress only)
- Marketing language ("Powerful", "Seamless", "Revolutionary")
- Hedging ("Maybe", "Perhaps", "Might")
- Excitement ("Amazing!", "Wow!", "Great job!")
- Informal contractions in labels ("Can't" -- use "Cannot")
- Questions as headings ("Ready to get started?")
- Ellipsis for suspense ("Loading..." is acceptable; "Almost there..." is not)
