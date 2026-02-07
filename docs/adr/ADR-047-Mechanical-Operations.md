# ADR-047 -- Mechanical Operations: Non-LLM Building Blocks

**Status:** Accepted
**Date:** 2026-02-06
**Accepted:** 2026-02-06
**Decision Type:** Architectural / Ontological

**Related ADRs:**
- ADR-045 -- System Ontology: Primitives, Composites, and Configuration Taxonomy
- ADR-041 -- Prompt Template Include System
- ADR-039 -- Document Interaction Workflow Model
- ADR-012 -- Interaction Model

---

## 1. Context

ADR-045 established the system ontology: Prompt Fragments shape behavior, Schemas define acceptability, and Interaction Passes bind and execute both. This model assumes every DCW node involves an LLM invocation.

However, production workflows frequently require operations that are:
- Deterministic (no LLM reasoning required)
- Structural (transform, merge, extract, validate data)
- Fast (sub-millisecond vs. multi-second LLM calls)
- Auditable (deterministic behavior is easier to verify)

Examples from current implementation needs:
- **Extracting** structured fields from a document to feed into another node
- **Merging** clarification answers with an intake summary (structural, not synthesis)
- **Validating** schema compliance before proceeding (without LLM interpretation)
- **Transforming** document format (e.g., flattening nested structures)
- **Selecting** which downstream path based on field values

Currently, these operations are either:
1. Embedded in Python handler code (not configurable, not visible in workflow editor)
2. Performed by unnecessary LLM calls (wasteful, slow, non-deterministic)
3. Not possible within the workflow graph (requiring external orchestration)

The Admin Workbench needs a way to represent, configure, and visualize these non-LLM operations as first-class workflow nodes.

Additionally, this ADR completes the primitive taxonomy by formally recognizing **Interaction Template** as a primitive (the ADR-041 `$TOKEN` assembly mechanism) and introducing **Interaction Definition** as a composite that bundles the per-node configuration.

---

## 2. Decision

The Combine:

1. Introduces **Mechanical Operations** as a new primitive type alongside Prompt Fragments and Schemas
2. Formalizes **Interaction Template** as a primitive (the ADR-041 `$TOKEN` assembly mechanism)
3. Introduces **Interaction Definition** as a composite that bundles per-node configuration
4. Introduces **Gate** as a composite node containing multiple Interaction Definitions
5. Clarifies that Gates (like PGC) use gate-specific schemas, not document output schemas

This enables DCW nodes that perform deterministic data transformations without LLM invocation, while completing the taxonomy for all node internal types.

---

## 3. Mechanical Operation Primitive

A Mechanical Operation is a typed, configurable, deterministic function that transforms inputs to outputs without LLM invocation.

**Properties:**
- Versioned, governed (like Prompt Fragments and Schemas)
- Deterministic -- same inputs always produce same outputs
- Fast -- no LLM latency
- Typed -- explicit input/output contracts
- Composable -- can be chained in workflow graphs

**Governing principle:** Mechanical Operations transform data; Prompt Fragments shape behavior; Schemas define acceptability.

---

## 4. Mechanical Operation Types

### 4.1 Extractor

Extracts structured fields from a document.

**Use case:** Pull specific fields from a stabilized document to feed as inputs to another node.

**Configuration:**
- `source_type`: Document type to extract from
- `field_paths`: JSON paths to extract (e.g., `$.summary`, `$.constraints[*].name`)
- `output_shape`: Schema defining the extracted structure

**Example:**
```yaml
type: extractor
source_type: project_intake
field_paths:
  - path: $.project_summary
    as: summary
  - path: $.identified_constraints
    as: constraints
output_shape: extracted_intake_context
```

### 4.2 Merger

Combines multiple inputs into a single structured output.

**Use case:** Merge clarification answers with original intake summary before generation.

**Configuration:**
- `inputs`: List of input references with merge keys
- `merge_strategy`: deep_merge | shallow_merge | concatenate
- `output_shape`: Schema defining the merged structure

**Example:**
```yaml
type: merger
inputs:
  - ref: intake_summary
    key: base
  - ref: clarification_answers
    key: clarifications
merge_strategy: deep_merge
output_shape: enriched_intake
```

### 4.3 Validator

Validates data against a schema and routes based on result.

**Use case:** Pre-validate document structure before expensive LLM QA pass.

**Configuration:**
- `input`: Reference to data to validate
- `schema_ref`: Schema to validate against
- `on_pass`: Outcome when valid
- `on_fail`: Outcome when invalid (includes validation errors)

**Example:**
```yaml
type: validator
input: generated_document
schema_ref: project_discovery.output
on_pass: success
on_fail: structural_failure
```

### 4.4 Transformer

Applies deterministic transformations to data structure.

**Use case:** Flatten nested structures, rename fields, apply formatting rules.

**Configuration:**
- `input`: Reference to input data
- `transform_rules`: List of transformation operations
- `output_shape`: Schema defining the transformed structure

**Example:**
```yaml
type: transformer
input: raw_requirements
transform_rules:
  - flatten: $.nested.requirements
    to: $.requirements
  - rename: $.old_field
    to: $.new_field
  - format: $.dates[*]
    pattern: ISO8601
output_shape: normalized_requirements
```

### 4.5 Selector

Routes workflow based on field values (deterministic branching).

**Use case:** Route to different downstream nodes based on document classification.

**Configuration:**
- `input`: Reference to data containing selector field
- `field_path`: Path to the field determining the route
- `routes`: Map of field values to outcomes

**Example:**
```yaml
type: selector
input: intake_classification
field_path: $.category
routes:
  new_feature: route_to_feature_discovery
  bug_fix: route_to_bug_triage
  enhancement: route_to_enhancement_scoping
  default: route_to_general_intake
```

---

## 5. Node Internal Types

DCW nodes now have an **internal type** that determines their execution model:

| Internal Type | Description | Execution Model |
|---------------|-------------|-----------------|
| `LLM` | Interaction Pass | Prompt assembly -> LLM invocation -> Schema validation |
| `MECH` | Mechanical Operation | Deterministic transformation -> Schema validation |
| `UI` | Operator Entry | Wait for user input -> Schema validation |

**Current PGC Gate internal structure example:**
- Pass A: Question Generation → `LLM` (Interaction Pass)
- Entry: Operator Answers → `UI` (Operator Entry)
- Pass B: Clarification Merge → `MECH` (Merger) or `LLM` (if synthesis required)

**Implications:**
- Workflow editor displays node internal type as a badge
- Execution engine dispatches to appropriate handler based on internal type
- Logging distinguishes LLM vs MECH invocations for cost/performance tracking

---

## 6. Taxonomy Update

This ADR extends ADR-045's taxonomy with the complete primitive and composite hierarchy.

### Primitives (independently authored, versioned, reusable)

"Worked occasionally, then plugged in everywhere."

| Primitive | Nature | Purpose |
|-----------|--------|---------|
| Prompt Fragment | Textual, composable | Shape LLM behavior (role, task, QA, PGC context, guards) |
| Schema | Structural, JSON | Define acceptable output for LLM passes, MECH ops, UI entry |
| Interaction Template | Text + token contract | ADR-041 `$TOKEN` assembly mechanism |
| **Mechanical Operation** | **Typed, deterministic** | **Transform data without LLM** |

**Note:** Prompt Fragments are typed by usage (role, task, QA, PGC, etc.), not by storage location.

### Composites (assembled from primitives)

| Composite | Assembled From | Purpose |
|-----------|---------------|---------|
| **Interaction Definition** | internal_type + template_ref + includes + schema + op_config | Per-node configuration bundle |
| **Gate** | Multiple Interaction Definitions (internals) | Composite node with multiple passes (e.g., PGC) |
| Role | Prompt Fragment(s) + metadata | Behavioral posture for LLM |
| Task | Prompt Fragment(s) + metadata | Desired outcome function |
| DCW | Gates + Nodes + Edges | Produce one stabilized document |
| POW | DCW references + gates | Sequence document production |

### Interaction Definition (new composite)

The **Interaction Definition** is the bundle configured in the node properties panel:

```yaml
# LLM internal
internal_type: LLM
template_ref: prompt:template:project_discovery_gen:1.0.0
includes:
  - prompt:role:business_analyst:1.0.0
  - prompt:task:discovery_generation:1.0.0
output_schema: schema:project_discovery:1.0.0

# MECH internal
internal_type: MECH
op_ref: mech:merger:clarification_merge:1.0.0
op_config:
  merge_strategy: deep_merge
output_schema: schema:pgc_clarifications:1.0.0

# UI internal
internal_type: UI
ui_contract:
  entry_prompt: "Please answer the clarification questions"
  input_schema: schema:operator_answers:1.0.0
output_schema: schema:operator_answers:1.0.0
```

### Gate (composite node with internals)

A **Gate** is a composite node containing multiple Interaction Definitions that execute as a unit.

**Example: PGC Gate**

| Internal | Type | Schema |
|----------|------|--------|
| Pass A | LLM (question generation) | `clarification_question_set.v2` |
| Entry | UI (operator answers) | `operator_answers` (if formalized) |
| Pass B | MECH merger (preferred) or LLM (if synthesis required) | `pgc_clarifications.v1` |

**Key insight:** PGC does NOT use the document output schema. It uses gate-specific schemas:
- Pass A output: `clarification_question_set.v2` (questions only)
- Pass B output: `pgc_clarifications.v1` (merged Q+A with binding)

Only use LLM for Pass B if you truly need synthesis beyond structural merge.

### Composition hierarchy (updated)

```
POW
  -> DCW (one per step)
       -> Gate (composite node)
            -> Interaction Definition (Pass A) [LLM]
            -> Interaction Definition (Entry)  [UI]
            -> Interaction Definition (Pass B) [MECH or LLM]
       -> Node (simple node)
            -> Interaction Definition [LLM | MECH | UI]
                 [LLM]
                 -> Interaction Template
                 -> Prompt Fragments (role + task + context + guards)
                 -> Schema (output contract)
                 => Outcome Artifact

                 [MECH]
                 -> Mechanical Operation
                 -> Schema (output contract)
                 => Outcome Artifact

                 [UI]
                 -> UI Contract (entry prompt + input schema)
                 -> Schema (output contract)
                 => Outcome Artifact
```

---

## 7. Admin Workbench Implications

### UX Pattern

The workbench maintains the factory-floor mental model:

- **Left rail**: POWs + DCWs only (primary navigation -- what I'm assembling)
- **Canvas**: Editing the selected POW/DCW
- **Right panel**: Properties for selected node, one expanded internal at a time
- **Building Blocks palette**: Slide-out drawer for selection, not browsing

Building Blocks are ingredients, not the work surface.

### Building Blocks Organization

Building Blocks use **tags/facets** for filtering, not separate top-level categories:

| Facet | Values |
|-------|--------|
| `template_kind` | generation, pgc_questions, pgc_merge, qa, remediation, intake |
| `scope` | shared, package_local |
| `assurance` | draft, certified |

This avoids recreating the junk drawer with more drawers.

**Palette structure:**
```
Building Blocks (slide-out tray)
├── Interactions      [filtered by template_kind]
├── Mechanical Ops    [type registry + instances, see §8.3]
├── Schemas           [filtered by scope]
└── Templates         [filtered by template_kind]
```

The Mechanical Ops tab is backed by the Operation Type Registry (§8), which provides:
- Type definitions with config schemas
- Input/output contracts
- UI hints for field rendering
- Categories for organization

### Node Properties Panel Update

When a node is selected in the workflow editor, the properties panel shows:

1. **Internal Type selector**: LLM | MECH | UI
2. **Type-specific configuration**:
   - LLM: Interaction Template dropdown (not raw string), role/task includes, output schema
   - MECH: Mechanical Operation dropdown, operation-specific config, output schema
   - UI: Entry prompt, input schema

**Task Ref → Interaction Template**: The node config references `prompt:template:<id>@<version>` and the editor surfaces this as a dropdown selection.

### Workflow Canvas Visualization

Nodes display their internal type as a visual indicator:
- LLM nodes: Brain icon or similar
- MECH nodes: Gear/cog icon
- UI nodes: User/person icon

---

## 8. Mechanical Operation Registry

The Building Blocks tray needs a toolbox of Mechanical Operations. This requires two layers:

1. **Operation Type Registry** - System-level catalog of operation types (Extractor, Merger, etc.) with their schemas
2. **Operation Instances** - User-authored operations built from types

### 8.1 Operation Type Registry

Located at `combine-config/mechanical_ops/_registry/types.yaml`:

```yaml
$schema: https://thecombine.ai/schemas/mech-op-registry.v1.json

types:
  extractor:
    name: "Extractor"
    description: "Extracts structured fields from a document"
    icon: "scissors"  # or icon ref
    category: "data_access"
    config_schema:
      type: object
      required: [source_type, field_paths, output_shape]
      properties:
        source_type:
          type: string
          description: "Document type to extract from"
          ui_hint: "dropdown:document_types"
        field_paths:
          type: array
          description: "JSON paths to extract"
          items:
            type: object
            properties:
              path: { type: string, description: "JSONPath expression" }
              as: { type: string, description: "Output field name" }
        output_shape:
          type: string
          description: "Schema for extracted structure"
          ui_hint: "dropdown:schemas"
    inputs:
      - name: "source_document"
        type: "document"
        description: "The document to extract from"
    outputs:
      - name: "extracted"
        type: "object"
        description: "Extracted fields matching output_shape"

  merger:
    name: "Merger"
    description: "Combines multiple inputs into a single structured output"
    icon: "merge"
    category: "composition"
    config_schema:
      type: object
      required: [inputs, merge_strategy, output_shape]
      properties:
        inputs:
          type: array
          description: "Input references with merge keys"
          items:
            type: object
            properties:
              ref: { type: string, description: "Input reference" }
              key: { type: string, description: "Merge key in output" }
        merge_strategy:
          type: string
          enum: [deep_merge, shallow_merge, concatenate]
          description: "How to combine inputs"
        output_shape:
          type: string
          description: "Schema for merged output"
          ui_hint: "dropdown:schemas"
    inputs:
      - name: "inputs"
        type: "array"
        description: "Multiple inputs to merge"
    outputs:
      - name: "merged"
        type: "object"
        description: "Combined output matching output_shape"

  validator:
    name: "Validator"
    description: "Validates data against a schema and routes based on result"
    icon: "check-circle"
    category: "quality"
    config_schema:
      type: object
      required: [input, schema_ref]
      properties:
        input:
          type: string
          description: "Reference to data to validate"
        schema_ref:
          type: string
          description: "Schema to validate against"
          ui_hint: "dropdown:schemas"
        on_pass:
          type: string
          default: "success"
          description: "Outcome when valid"
        on_fail:
          type: string
          default: "failed"
          description: "Outcome when invalid"
    inputs:
      - name: "data"
        type: "any"
        description: "Data to validate"
    outputs:
      - name: "result"
        type: "object"
        properties:
          valid: { type: boolean }
          errors: { type: array, items: { type: string } }

  transformer:
    name: "Transformer"
    description: "Applies deterministic transformations to data structure"
    icon: "shuffle"
    category: "data_transform"
    config_schema:
      type: object
      required: [input, transform_rules, output_shape]
      properties:
        input:
          type: string
          description: "Reference to input data"
        transform_rules:
          type: array
          description: "Transformation operations"
          items:
            type: object
            # Polymorphic: flatten, rename, format, etc.
        output_shape:
          type: string
          description: "Schema for transformed output"
          ui_hint: "dropdown:schemas"
    inputs:
      - name: "source"
        type: "object"
        description: "Data to transform"
    outputs:
      - name: "transformed"
        type: "object"
        description: "Transformed data matching output_shape"

  selector:
    name: "Selector"
    description: "Routes workflow based on field values (deterministic branching)"
    icon: "git-branch"
    category: "flow_control"
    config_schema:
      type: object
      required: [input, field_path, routes]
      properties:
        input:
          type: string
          description: "Reference to data containing selector field"
        field_path:
          type: string
          description: "JSONPath to the routing field"
        routes:
          type: object
          description: "Map of field values to outcomes"
          additionalProperties:
            type: string
        default:
          type: string
          description: "Fallback outcome if no route matches"
    inputs:
      - name: "data"
        type: "object"
        description: "Data containing the routing field"
    outputs:
      - name: "selected_route"
        type: "string"
        description: "The outcome name for the matched route"

categories:
  data_access:
    name: "Data Access"
    description: "Operations that read/extract from documents"
  composition:
    name: "Composition"
    description: "Operations that combine multiple inputs"
  quality:
    name: "Quality"
    description: "Operations that validate or check data"
  data_transform:
    name: "Data Transform"
    description: "Operations that reshape data structures"
  flow_control:
    name: "Flow Control"
    description: "Operations that determine workflow routing"
```

### 8.2 Operation Instances

User-authored operations stored in:

```
combine-config/
  mechanical_ops/
    _registry/
      types.yaml              # Operation type definitions (system)
    {op_id}/
      releases/
        {version}/
          operation.yaml      # Instance definition
          schema.json         # Optional: custom output schema
```

**operation.yaml structure (instance):**
```yaml
$schema: https://thecombine.ai/schemas/mechanical-operation.v1.json
id: extract_intake_context
version: "1.0.0"
type: extractor                    # References type from registry
name: "Extract Intake Context"
description: "Extracts summary and constraints from intake document"

config:
  source_type: project_intake
  field_paths:
    - path: $.project_summary
      as: summary
    - path: $.identified_constraints
      as: constraints
  output_shape: extracted_intake_context

metadata:
  created_date: "2026-02-06"
  author: "system"
  tags:
    - intake
    - extraction
```

### 8.3 Building Blocks Tray Integration

The Mechanical Ops tab in the Building Blocks tray shows:

```
Mechanical Ops
├── [+ New Operation]           # Creates from type template
├── ── By Type ──
│   ├── Extractors (2)
│   │   ├── extract_intake_context
│   │   └── extract_discovery_summary
│   ├── Mergers (1)
│   │   └── pgc_clarification_merge
│   └── Validators (0)
└── ── By Category ──
    ├── Data Access (2)
    ├── Composition (1)
    └── Quality (0)
```

**"+ New Operation" flow:**
1. Select operation type from dropdown (Extractor, Merger, etc.)
2. Panel shows type-specific config fields based on `config_schema`
3. `ui_hint` values drive field rendering (dropdowns for schemas, document types, etc.)
4. Save creates new operation instance in `mechanical_ops/{id}/`

### 8.4 Node Properties Panel Integration

When a MECH node is selected:

1. **Operation dropdown**: Lists all operation instances, grouped by type
2. **Config preview**: Shows the operation's config (read-only or editable based on context)
3. **Input/Output contract**: Displays from type registry metadata
4. **Override fields**: For instance-level config that can be overridden per-node

---

## 9. Execution Model

### MECH Node Execution

1. **Input Resolution**: Resolve input references from workflow context
2. **Operation Dispatch**: Route to appropriate handler based on operation type
3. **Transformation**: Execute deterministic transformation
4. **Validation**: Validate output against schema
5. **State Update**: Store result as Outcome Artifact, advance workflow

### Error Handling

Mechanical Operations have explicit failure modes:
- `input_missing`: Required input not available in context
- `schema_violation`: Output doesn't match declared schema
- `transform_error`: Transformation logic failed (e.g., invalid path)
- `routing_unmatched`: Selector found no matching route and no default

Failures route to appropriate edges based on workflow definition.

---

## 10. Benefits

### Performance
- MECH nodes execute in milliseconds vs. seconds for LLM
- No API costs for deterministic operations
- Parallelizable where dependencies allow

### Reliability
- Deterministic behavior is easier to test and debug
- No prompt drift or model behavior changes
- Exact reproducibility for audit

### Clarity
- Workflow graph shows what is LLM-powered vs. mechanical
- Clear separation of concerns: LLM for reasoning, MECH for data plumbing
- Easier to identify optimization opportunities

### Cost
- Reduced LLM invocations for operations that don't require reasoning
- Pre-validation catches errors before expensive LLM calls
- Extractors minimize context size passed to LLM

---

## 11. Relationship to Existing Concepts

### Interaction Pass (ADR-045)
Interaction Pass remains the ontological term for LLM execution events. It is "configured implicitly" inside DCWs -- users don't author Interaction Passes as separate entities. MECH nodes do not have Interaction Passes; they have Mechanical Executions.

### PGC Gates (2-artifact gates)
PGC is NOT "one schema." It's a 2-artifact gate with its own schemas:

| Internal | Type | Output Schema |
|----------|------|---------------|
| Pass A | LLM (question generation) | `clarification_question_set.v2` (questions only) |
| Entry | UI (operator answers) | `operator_answers` (if formalized) |
| Pass B | MECH merger (preferred) | `pgc_clarifications.v1` (merged Q+A with binding) |

**Key insight:** PGC does NOT use the document output schema. The document output schema belongs to the Generation node.

Pass B should be MECH (Merger) unless synthesis is truly required -- structural merge of questions + answers doesn't need LLM reasoning.

### Validation Rule `SCHEMA_REQUIRED`
Applies equally to LLM and MECH nodes -- all nodes producing Outcome Artifacts must have a schema contract.

### Interaction Template vs Task Ref
"Task Ref" in the node panel should be an Interaction Template selection (dropdown), not a raw string. The reference format is `prompt:template:<id>@<version>`.

---

## 12. Migration Path

### Phase 1: Foundation
- Define `mechanical-operation.v1.json` schema
- Implement base execution handler for MECH nodes
- Add internal_type field to workflow node definitions

### Phase 2: Core Operations
- Implement Extractor and Merger
- Update workflow editor with MECH node support
- Create first mechanical operations for existing workflows

### Phase 3: Extended Operations
- Implement Validator, Transformer, Selector
- Build operation library for common patterns
- Add operation testing/preview capability

### Phase 4: Optimization
- Identify LLM nodes that can be converted to MECH
- Measure performance/cost improvements
- Document best practices

---

## 13. Non-Goals

This ADR does NOT:
- Replace LLM nodes for operations requiring reasoning
- Create a general-purpose programming language within workflows
- Support arbitrary code execution (operations are typed and constrained)
- Change existing LLM execution mechanics (ADR-012)
- Modify schema governance (ADR-031)

---

## 14. Acceptance Criteria

ADR-047 is considered satisfied when:

1. Mechanical Operation primitive is defined with schema and governance rules
2. Operation Type Registry exists at `mechanical_ops/_registry/types.yaml` with all 5 types
3. At least Extractor and Merger operation types are implemented with execution handlers
4. Interaction Definition composite is implemented as the per-node configuration bundle
5. Workflow editor supports LLM/MECH/UI internal types with appropriate visualization
6. Node properties panel shows Interaction Template as dropdown (not raw string)
7. Building Blocks tray has Mechanical Ops tab with type registry integration
8. "New Operation" flow creates instances from type templates with config_schema-driven UI
9. At least one existing workflow uses a MECH node (e.g., PGC Pass B merger)
10. Execution engine dispatches correctly based on node internal type
11. Building Blocks palette uses facet filtering (template_kind, scope, assurance)
12. PGC gates correctly use `clarification_question_set.v2` (Pass A) and `pgc_clarifications.v1` (Pass B)

---

## 15. Drift Risks

| Risk | Mitigation |
|------|------------|
| Scope creep toward general programming | Strict operation type taxonomy; no custom code blocks |
| Confusion between MECH validation and QA | Clear naming: MECH validators check structure, QA nodes check quality |
| Over-engineering simple extractions | Start with common patterns; defer complex transformations |
| Mixing LLM and MECH concerns in single node | Node internal type is singular; composite gates have explicit internals |

---

## Addendum A: Entry Operations (UI Mechanical Ops)

**Added:** 2026-02-06

### A.1 Rationale

ADR-047 §5 defines three internal types: LLM, MECH, and UI. The Operation Type Registry (§8.1) defines five code-based operation types (Extractor, Merger, Validator, Transformer, Selector). This addendum extends the registry with **Entry** operations for UI internal types.

Entry operations follow the same contract structure as code-based mechanical ops:
- Typed inputs (what to render)
- Typed outputs (structured user response)
- Schema-validated
- Versioned and governed

The difference is the executor: a React component instead of Python code.

### A.2 Entry Operation Type

Add to `combine-config/mechanical_ops/_registry/types.yaml`:

```yaml
entry:
  name: "Entry"
  description: "Captures structured input from an operator via UI"
  icon: "user-edit"
  category: "human_input"
  config_schema:
    type: object
    required: [renders, captures]
    properties:
      renders:
        type: string
        description: "Schema defining what to display to operator"
        ui_hint: "dropdown:schemas"
      captures:
        type: string
        description: "Schema defining expected operator response"
        ui_hint: "dropdown:schemas"
      entry_prompt:
        type: string
        description: "Instructions shown to operator"
      layout:
        type: string
        enum: [form, wizard, review]
        default: form
        description: "UI layout hint"
      validation_mode:
        type: string
        enum: [strict, lenient]
        default: strict
        description: "How strictly to enforce captures schema"
  inputs:
    - name: "context"
      type: "object"
      description: "Data to render for operator review/action"
  outputs:
    - name: "response"
      type: "object"
      description: "Structured operator input matching captures schema"

categories:
  # ... existing categories ...
  human_input:
    name: "Human Input"
    description: "Operations that capture structured input from operators"
```

### A.3 Entry Operation Instances

**concierge_entry** - Intake confirmation UI:
```yaml
$schema: https://thecombine.ai/schemas/mechanical-operation.v1.json
op_id: concierge_entry
version: "1.0.0"
type: entry
name: "Concierge Entry"
description: "Operator confirms or corrects intake classification"

config:
  renders: intake_classification.v1
  captures: intake_confirmation.v1
  entry_prompt: "Review the intake classification. Confirm or correct as needed."
  layout: review

metadata:
  created_date: "2026-02-06"
  author: "system"
  tags:
    - intake
    - confirmation
```

**pgc_operator_answers** - PGC answer collection UI:
```yaml
$schema: https://thecombine.ai/schemas/mechanical-operation.v1.json
op_id: pgc_operator_answers
version: "1.0.0"
type: entry
name: "PGC Operator Answers"
description: "Operator provides answers to generated clarification questions"

config:
  renders: clarification_question_set.v2
  captures: operator_answers.v1
  entry_prompt: "Please answer the clarification questions below."
  layout: form

metadata:
  created_date: "2026-02-06"
  author: "system"
  tags:
    - pgc
    - clarification
```

### A.4 Execution Model

Entry operations execute differently from code-based mechanical ops:

1. **Render**: React component receives `renders` data from workflow context
2. **Wait**: Execution pauses until operator submits response
3. **Capture**: Response validated against `captures` schema
4. **Resume**: Workflow advances with validated response as output

The workflow engine treats Entry nodes as blocking until operator action completes.

### A.5 React Component Contract

Entry operation instances map to React components via a registry:

```typescript
// Entry component receives:
interface EntryComponentProps {
  operation: MechanicalOperation;  // Full operation definition
  context: object;                  // Data matching renders schema
  onSubmit: (response: object) => void;  // Must match captures schema
  onCancel?: () => void;
}

// Component registry
const entryComponents: Record<string, React.FC<EntryComponentProps>> = {
  'concierge_entry': ConciergeEntryForm,
  'pgc_operator_answers': PGCAnswerForm,
  // Generic fallback for unknown ops
  '_default': GenericEntryForm,
};
```

### A.6 Building Blocks Integration

Entry operations appear in the Mechanical Ops tab alongside code-based ops:

```
Mechanical Ops
├── ── By Type ──
│   ├── Extractors (2)
│   ├── Mergers (1)
│   ├── Entry (2)           # <-- New
│   │   ├── concierge_entry
│   │   └── pgc_operator_answers
│   └── ...
└── ── By Category ──
    ├── Human Input (2)     # <-- New category
    └── ...
```

### A.7 Updated Acceptance Criteria

Add to §14:

13. Entry operation type is defined in the Operation Type Registry
14. At least two Entry operation instances exist (concierge_entry, pgc_operator_answers)
15. React component contract is implemented for Entry operations
16. Workflow engine handles Entry node blocking/resume correctly

---

## Addendum B: Implementation Report

**Updated:** 2026-02-07

### B.1 Implementation Status

| Component | Status | Work Statement |
|-----------|--------|----------------|
| Operation Type Registry | Complete | WS-ADR-047-001 |
| Base Handler Framework | Complete | WS-ADR-047-001 |
| Extractor Handler | Complete | WS-ADR-047-001 |
| Merger Handler | Complete | WS-ADR-047-001 |
| Entry Handler | Complete | WS-ADR-047-002 |
| Clarification Merger Handler | Complete | WS-ADR-047-004 |
| Invariant Pinner Handler | Complete | WS-ADR-047-004 |
| Exclusion Filter Handler | Complete | WS-ADR-047-004 |
| plan_executor.py refactoring | Complete | WS-ADR-047-004 |

### B.2 Handler Registry

All handlers are registered via `@register_handler` decorator in `app/api/services/mech_handlers/`:

| Handler Class | Operation Type | File |
|---------------|----------------|------|
| ExtractorHandler | extractor | extractor.py |
| MergerHandler | merger | merger.py |
| EntryHandler | entry | entry.py |
| ClarificationMergerHandler | clarification_merger | clarification_merger.py |
| InvariantPinnerHandler | invariant_pinner | invariant_pinner.py |
| ExclusionFilterHandler | exclusion_filter | exclusion_filter.py |

### B.3 Operation Instances

Active operation instances in `combine-config/mechanical_ops/`:

| Operation ID | Type | Purpose |
|--------------|------|---------|
| pgc_clarification_merge | merger | Merges Q+A (legacy) |
| concierge_entry | entry | Intake confirmation UI |
| pgc_operator_answers | entry | PGC answer collection |
| intake_context_extractor | extractor | Extract intake context |
| discovery_context_extractor | extractor | Extract discovery context |
| qa_feedback_merger | merger | Merge QA feedback |
| pgc_clarification_processor | clarification_merger | Merge Q+A with invariant extraction |
| discovery_invariant_pinner | invariant_pinner | Pin invariants to known_constraints |
| discovery_exclusion_filter | exclusion_filter | Filter excluded topics |

### B.4 Remaining Work

Per ADR-047 §14 Acceptance Criteria:

- [x] 1. Mechanical Operation primitive defined
- [x] 2. Operation Type Registry exists with types
- [x] 3. Extractor and Merger implemented
- [ ] 4. Interaction Definition composite as formal UI bundle (low priority)
- [x] 5. Workflow editor supports LLM/MECH/UI internal types
- [x] 6. Node properties panel shows operation dropdown for MECH nodes
- [x] 7. Building Blocks tray has Mechanical Ops tab
- [ ] 8. "New Operation" creation flow (future enhancement)
- [x] 9. At least one workflow uses MECH node (project_discovery PGC)
- [x] 10. Execution engine dispatches correctly
- [ ] 11. Building Blocks facet filtering (future enhancement)
- [x] 12. PGC gates use correct schemas

### B.5 Future Enhancements (Phase 3-4)

Per ADR-047 §12 Migration Path:

| Phase | Item | Status |
|-------|------|--------|
| Phase 3 | Validator operation type | Not started |
| Phase 3 | Transformer operation type | Not started |
| Phase 3 | Selector operation type | Not started |
| Phase 3 | Operation testing/preview | Not started |
| Phase 4 | Convert LLM nodes to MECH | Not started |
| Phase 4 | Performance/cost measurement | Not started |

These are optimization phases, not required for core functionality.

---

_End of ADR-047_
