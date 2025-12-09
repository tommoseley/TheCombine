# PIPELINE-175A: BA Backlog (Refined Acceptance Criteria & Test Scenarios)

**Epic:** PIPELINE-175A - Data-Described Pipeline Infrastructure  
**Phase:** Business Analysis  
**BA Mentor:** Complete  
**Version:** 1.0  
**Date:** 2025-12-04

---

## Table of Contents

1. [Story 0: RolePrompt Model and Repository](#story-0-roleprompt-model-and-repository)
2. [Story 1: PhaseConfiguration Model and Repository](#story-1-phaseconfiguration-model-and-repository)
3. [Story 2: Seed Scripts](#story-2-seed-scripts-for-role-prompts--phase-configuration)
4. [Story 3: RolePromptService](#story-3-implement-rolepromptservice)
5. [Story 4: Comprehensive Testing](#story-4-comprehensive-testing)
6. [Epic-Level Acceptance Criteria](#epic-level-acceptance-criteria)

---

## Story 0: RolePrompt Model and Repository

### AC-0.1: Database Schema Creation

#### Verification Method

| Criterion | Test Method | Pass Criteria |
|-----------|-------------|---------------|
| Tables created | Query `sqlite_master` or `information_schema.tables` | `role_prompts`, `pipeline_prompt_usage` exist |
| Indexes exist | `PRAGMA index_list('role_prompts')` (SQLite) or `pg_indexes` (PostgreSQL) | ≥3 indexes present |
| Unique constraint | Insert duplicate active prompt for same role | IntegrityError raised |
| Migration idempotent | Run migration script twice | Second run: no errors, no duplicates |

#### Test Scenarios

**Scenario 1: Fresh Database**

```python
# Start with empty database
clear_database()

# Run migration
python app/orchestrator_api/persistence/migrations/001_create_role_prompt_tables.py

# Expected Output:
✓ Created role_prompts table
✓ Created phase_configurations table
✓ Created pipeline_prompt_usage table

# Verify tables exist
session.execute("SELECT name FROM sqlite_master WHERE type='table'")
# Expected: role_prompts, phase_configurations, pipeline_prompt_usage
```

**Scenario 2: Re-run Migration (Idempotency)**

```python
# Run migration again
python app/orchestrator_api/persistence/migrations/001_create_role_prompt_tables.py

# Expected Output:
✓ Created role_prompts table
✓ Created phase_configurations table
✓ Created pipeline_prompt_usage table

# OR (if using CREATE TABLE IF NOT EXISTS):
✓ Tables already exist, skipping creation

# Verify: Still only one copy of each table, no errors
```

**Scenario 3: Unique Constraint Enforcement**

```python
repo = RolePromptRepository()

# Create first active PM prompt
repo.create("pm", "1.0", "boot", "inst", set_active=True)

# Attempt to manually create duplicate active PM prompt (bypassing repo)
session = SessionLocal()
duplicate = RolePrompt(
    id="dup_id",
    role_name="pm",
    version="2.0",
    bootstrapper="boot",
    instructions="inst",
    is_active=True  # Violates unique constraint
)
session.add(duplicate)

# Expected: IntegrityError on commit
with pytest.raises(IntegrityError):
    session.commit()
```

---

### AC-0.2: Repository CRUD Operations

#### Test Scenarios

**Scenario 1: Get Active Prompt - Exists**

```python
Given:
  - PM prompt version 1.0 exists with is_active=True

When:
  prompt = RolePromptRepository.get_active_prompt("pm")

Then:
  - prompt is not None
  - prompt.role_name == "pm"
  - prompt.version == "1.0"
  - prompt.is_active == True
```

**Scenario 2: Get Active Prompt - Doesn't Exist**

```python
When:
  prompt = RolePromptRepository.get_active_prompt("nonexistent_role")

Then:
  - prompt is None
  - No exception raised
```

**Scenario 3: List Versions**

```python
Given:
  - PM prompt version 1.0 created on 2024-01-01
  - PM prompt version 1.1 created on 2024-06-01
  - PM prompt version 2.0 created on 2025-01-01

When:
  versions = RolePromptRepository.list_versions("pm")

Then:
  - len(versions) == 3
  - versions[0].version == "2.0"  # Newest first
  - versions[1].version == "1.1"
  - versions[2].version == "1.0"
  - All have role_name == "pm"
```

**Scenario 4: Create with set_active=True**

```python
Given:
  - PM version 1.0 exists and is_active=True

When:
  repo.create("pm", "2.0", "new boot", "new inst", set_active=True)

Then:
  - v2.0 is created
  - v2.0.is_active == True
  - v1.0.is_active == False (automatically deactivated)
  
Verify:
  active = repo.get_active_prompt("pm")
  assert active.version == "2.0"
```

**Scenario 5: Create with set_active=False**

```python
Given:
  - PM version 1.0 exists and is_active=True

When:
  repo.create("pm", "2.0", "new boot", "new inst", set_active=False)

Then:
  - v2.0 is created
  - v2.0.is_active == False
  - v1.0.is_active == True (unchanged)
  
Verify:
  active = repo.get_active_prompt("pm")
  assert active.version == "1.0"  # Still v1.0
```

**Scenario 6: Set Active**

```python
Given:
  - PM v1.0 (active), v2.0 (inactive), v3.0 (inactive)

When:
  repo.set_active(v2_0_id)

Then:
  - v2.0.is_active == True
  - v1.0.is_active == False
  - v3.0.is_active == False
  
Verify:
  active = repo.get_active_prompt("pm")
  assert active.id == v2_0_id
```

#### Edge Cases

| Edge Case | Expected Behavior | Error Message |
|-----------|------------------|---------------|
| Create without bootstrapper | ValueError raised | "bootstrapper and instructions are required fields" |
| Create without instructions | ValueError raised | "bootstrapper and instructions are required fields" |
| Create with invalid JSON in working_schema | ValueError raised | "working_schema must be valid JSON or null" |
| Set active with invalid ID | ValueError raised | "Prompt not found: {prompt_id}" |
| Get active when multiple active exist (corruption) | Return first, log warning | "Data corruption: multiple active prompts for role {role}" |

---

### AC-0.3: Audit Trail Schema & Repository

**Clarification:** Runtime wiring happens in 175B. In 175A, we validate schema and repository operations only.

#### Test Scenarios

**Scenario 1: Record Usage**

```python
Given:
  - Pipeline "pip_123" exists
  - Prompt "rp_abc" exists

When:
  usage = PipelinePromptUsageRepository.record_usage(
      "pip_123", "pm", "rp_abc", "pm_phase"
  )

Then:
  - usage.id is not None
  - usage.pipeline_id == "pip_123"
  - usage.role_name == "pm"
  - usage.prompt_id == "rp_abc"
  - usage.phase_name == "pm_phase"
  - usage.used_at is datetime (recent)
```

**Scenario 2: Get by Pipeline**

```python
Given:
  - Pipeline "pip_123" used 3 prompts:
    * PM prompt at 10:00
    * Architect prompt at 10:05
    * BA prompt at 10:10

When:
  usages = PipelinePromptUsageRepository.get_by_pipeline("pip_123")

Then:
  - len(usages) == 3
  - usages[0].role_name == "pm"  # Ordered by used_at
  - usages[1].role_name == "architect"
  - usages[2].role_name == "ba"
```

**Scenario 3: Get by Prompt**

```python
Given:
  - Prompt "rp_abc" used in 5 different pipelines

When:
  usages = PipelinePromptUsageRepository.get_by_prompt("rp_abc")

Then:
  - len(usages) == 5
  - All have prompt_id == "rp_abc"
  - Ordered by used_at descending (most recent first)
```

**Scenario 4: Foreign Key Enforcement**

```python
# Test 1: Invalid pipeline_id
with pytest.raises(RepositoryError):
    PipelinePromptUsageRepository.record_usage(
        "nonexistent_pipeline", "pm", "rp_valid", "pm_phase"
    )

# Test 2: Invalid prompt_id
with pytest.raises(RepositoryError):
    PipelinePromptUsageRepository.record_usage(
        "pip_valid", "pm", "nonexistent_prompt", "pm_phase"
    )
```

#### Data Constraints

| Field | Constraint | Validation |
|-------|-----------|------------|
| pipeline_id | Must exist in pipelines table | Foreign key enforced |
| prompt_id | Must exist in role_prompts table | Foreign key enforced |
| role_name | Non-empty string, max 64 chars | Length check in repository |
| phase_name | Non-empty string, max 64 chars | Length check in repository |
| used_at | Valid datetime with timezone | Type check |

---

### AC-0.4: Data Validation

#### Test Scenarios

**Scenario 1: Missing Bootstrapper**

```python
When:
  repo.create(
      role_name="test",
      version="1.0",
      bootstrapper="",  # Empty
      instructions="valid"
  )

Then:
  ValueError raised with message: "bootstrapper and instructions are required fields"
```

**Scenario 2: Missing Instructions**

```python
When:
  repo.create(
      role_name="test",
      version="1.0",
      bootstrapper="valid",
      instructions=""  # Empty
  )

Then:
  ValueError raised with message: "bootstrapper and instructions are required fields"
```

**Scenario 3: Two Active Prompts (Database Constraint)**

```python
Given:
  - PM v1.0 exists with is_active=True

When:
  # Manually insert duplicate active (bypassing repository)
  session = SessionLocal()
  duplicate = RolePrompt(
      id="dup", role_name="pm", version="2.0",
      bootstrapper="x", instructions="x", is_active=True
  )
  session.add(duplicate)
  session.commit()

Then:
  IntegrityError raised (unique constraint violation)
```

**Scenario 4: Valid JSON in working_schema**

```python
When:
  prompt = repo.create(
      ...,
      working_schema={"Epic": {"epic_id": "string"}}
  )

Then:
  - Success
  - prompt.working_schema == {"Epic": {"epic_id": "string"}}
```

**Scenario 5: Invalid JSON in working_schema**

```python
When:
  prompt = repo.create(
      ...,
      working_schema="not a dict"  # String instead of dict
  )

Then:
  ValueError raised with message: "working_schema must be dict or None"
```

#### Validation Checklist

- [ ] bootstrapper is non-empty string
- [ ] instructions is non-empty string
- [ ] role_name matches pattern `^[a-z_]+$` (lowercase, underscores only)
- [ ] version matches semantic versioning `^\d+\.\d+$`
- [ ] working_schema is None or valid dict
- [ ] Only one active prompt per role (database enforced)

---

## Story 1: PhaseConfiguration Model and Repository

### AC-1.1: Database Schema Creation

#### Test Scenarios

**Scenario 1: Create Table**

```python
# Run migration
python migrations/001_create_role_prompt_tables.py

# Verify table exists
result = session.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='phase_configurations'")
assert result.fetchone() is not None

# Verify columns
result = session.execute("PRAGMA table_info(phase_configurations)")
columns = {row[1] for row in result.fetchall()}
assert 'phase_name' in columns
assert 'role_name' in columns
assert 'artifact_type' in columns
assert 'next_phase' in columns
```

**Scenario 2: Unique Constraint on phase_name**

```python
repo = PhaseConfigurationRepository()

# Create phase
repo.create("pm_phase", "pm", "epic")

# Attempt duplicate
with pytest.raises(IntegrityError):
    repo.create("pm_phase", "architect", "arch_notes")  # Same phase_name
```

**Scenario 3: Indexes Created**

```python
# Check indexes exist
result = session.execute("PRAGMA index_list('phase_configurations')")
indexes = [row[1] for row in result.fetchall()]

assert 'idx_phase_config_phase' in indexes
assert 'idx_phase_config_active' in indexes
```

---

### AC-1.2: Repository Operations

#### Test Scenarios

**Scenario 1: Get by Phase - Exists**

```python
Given:
  - pm_phase configured with role=pm, artifact=epic

When:
  config = PhaseConfigurationRepository.get_by_phase("pm_phase")

Then:
  - config is not None
  - config.phase_name == "pm_phase"
  - config.role_name == "pm"
  - config.artifact_type == "epic"
```

**Scenario 2: Get by Phase - Doesn't Exist**

```python
When:
  config = PhaseConfigurationRepository.get_by_phase("nonexistent_phase")

Then:
  - config is None
  - No exception raised
```

**Scenario 3: Get All Active**

```python
Given:
  - 6 phase configs, all with is_active=True

When:
  configs = PhaseConfigurationRepository.get_all_active()

Then:
  - len(configs) == 6
  - All have is_active == True
  - Ordered by phase_name alphabetically
```

**Scenario 4: Get All Active - Some Inactive**

```python
Given:
  - 6 configs total
  - 2 marked is_active=False

When:
  configs = PhaseConfigurationRepository.get_all_active()

Then:
  - len(configs) == 4
  - All returned configs have is_active == True
```

**Scenario 5: Create Phase**

```python
When:
  config = repo.create("test_phase", "test_role", "test_artifact", next_phase="next")

Then:
  - config.phase_name == "test_phase"
  - config.role_name == "test_role"
  - config.artifact_type == "test_artifact"
  - config.next_phase == "next"
  - config.is_active == True (default)
```

**Scenario 6: Update Next Phase**

```python
Given:
  - pm_phase has next_phase="arch_phase"

When:
  updated = repo.update_next_phase("pm_phase", "new_phase")

Then:
  - updated.next_phase == "new_phase"
  
Verify:
  config = repo.get_by_phase("pm_phase")
  assert config.next_phase == "new_phase"
```

---

### AC-1.3: Basic Field Validation

#### Test Scenarios

**Scenario 1: Missing phase_name**

```python
When:
  repo.create(phase_name="", role_name="pm", artifact_type="epic")

Then:
  ValueError raised: "phase_name, role_name, and artifact_type are required"
```

**Scenario 2: Missing role_name**

```python
When:
  repo.create(phase_name="test", role_name="", artifact_type="epic")

Then:
  ValueError raised: "phase_name, role_name, and artifact_type are required"
```

**Scenario 3: Missing artifact_type**

```python
When:
  repo.create(phase_name="test", role_name="pm", artifact_type="")

Then:
  ValueError raised: "phase_name, role_name, and artifact_type are required"
```

**Scenario 4: Valid with Optional Fields Null**

```python
When:
  config = repo.create("phase", "role", "artifact", next_phase=None, config=None)

Then:
  - Success
  - config.next_phase is None
  - config.config is None
```

**Scenario 5: Terminal Phase**

```python
When:
  config = repo.create("commit_phase", "commit", "commit_result", next_phase=None)

Then:
  - Success
  - config.next_phase is None (terminal phase)
```

**Scenario 6: Valid JSON Config**

```python
When:
  config = repo.create(..., config={"timeout": 30, "retries": 3})

Then:
  - Success
  - config.config == {"timeout": 30, "retries": 3}
```

#### Data Constraints

| Field | Type | Required | Constraint | Example |
|-------|------|----------|------------|---------|
| phase_name | String(64) | Yes | Unique, non-empty, `^[a-z_]+$` | "pm_phase" |
| role_name | String(64) | Yes | Non-empty, `^[a-z_]+$` | "pm" |
| artifact_type | String(64) | Yes | Non-empty, lowercase | "epic" |
| next_phase | String(64) | No | Null or valid phase_name | "arch_phase" or null |
| config | JSON | No | Null or valid JSON object | {"timeout": 30} |

---

### AC-1.4: Configuration Validation Helper

**Note:** Validation is separate from `create()` to allow flexible seed script ordering.

#### Test Scenarios

**Scenario 1: Valid Configuration Graph**

```python
Given:
  role_prompts:
    - pm (active)
    - architect (active)
    - ba (active)
    - dev (active)
    - qa (active)
    - commit (active)
  
  phase_configurations:
    - pm_phase → pm → epic → arch_phase
    - arch_phase → architect → arch_notes → ba_phase
    - ba_phase → ba → ba_spec → dev_phase
    - dev_phase → dev → proposed_change_set → qa_phase
    - qa_phase → qa → qa_result → commit_phase
    - commit_phase → commit → commit_result → null

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == True
  - result.errors == []
```

**Scenario 2: Missing Role Reference**

```python
Given:
  role_prompts: pm, architect (active)
  phase_configurations:
    - pm_phase → pm → epic → arch_phase
    - arch_phase → architect → arch_notes → ba_phase
    - ba_phase → ba → ba_spec → null  # "ba" role doesn't exist!

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == False
  - result.errors[0] == "Phase 'ba_phase' references non-existent role 'ba'. Available roles: ['architect', 'pm']"
```

**Scenario 3: Missing next_phase Reference**

```python
Given:
  phase_configurations:
    - pm_phase → pm → epic → nonexistent_phase  # Doesn't exist!

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == False
  - "Phase 'pm_phase' references non-existent next_phase 'nonexistent_phase'" in result.errors
```

**Scenario 4: Circular Reference - Simple Cycle**

```python
Given:
  phase_configurations:
    - phase_a → role1 → artifact1 → phase_b
    - phase_b → role2 → artifact2 → phase_c
    - phase_c → role3 → artifact3 → phase_a  # Circular!

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == False
  - "Circular reference detected starting at 'phase_a': phase_a → phase_b → phase_c → phase_a" in result.errors
```

**Scenario 5: Circular Reference - Self-Loop**

```python
Given:
  phase_configurations:
    - phase_a → role1 → artifact1 → phase_a  # Points to itself!

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == False
  - "Circular reference detected starting at 'phase_a': phase_a → phase_a" in result.errors
```

**Scenario 6: Chain Too Long (>20 hops)**

```python
Given:
  phase_configurations: 25 phases in sequence
    - phase_1 → phase_2 → ... → phase_25 → null

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == False
  - "Phase chain starting at 'phase_1' exceeds maximum length (20 hops)" in result.errors
```

**Scenario 7: Multiple Errors**

```python
Given:
  - phase_a references nonexistent role "missing_role"
  - phase_b references nonexistent next_phase "missing_phase"
  - phase_c → phase_d → phase_c (circular)

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == False
  - len(result.errors) == 3
  - All three error types present in errors list
```

**Scenario 8: Empty Configuration**

```python
Given:
  No phase configurations in database

When:
  result = PhaseConfigurationRepository.validate_configuration_graph()

Then:
  - result.is_valid == True
  - result.errors == []
  # Empty is technically valid (no errors to find)
```

#### Validation Algorithm Checklist

**Step 1: Load Data**
- [ ] Loads all active phase configurations
- [ ] Loads all active role prompts
- [ ] Builds set of phase_names
- [ ] Builds set of role_names

**Step 2: Check Role References**
- [ ] For each phase config
- [ ] Verify role_name exists in role_names set
- [ ] If not found, add error with available roles listed

**Step 3: Check Phase References**
- [ ] For each phase config
- [ ] If next_phase is not None
- [ ] Verify next_phase exists in phase_names set
- [ ] If not found, add error with available phases listed

**Step 4: Check Circular References**
- [ ] For each phase config (starting point)
- [ ] Initialize empty visited set
- [ ] Initialize hop counter at 0
- [ ] While current phase exists and hops < 20:
  - [ ] Check if current in visited → circular error
  - [ ] Add current to visited
  - [ ] Get next_phase from config
  - [ ] Set current = next_phase
  - [ ] Increment hop counter
- [ ] If hops >= 20 → max length error

**Step 5: Return Result**
- [ ] If errors list empty → is_valid = True
- [ ] If errors list has items → is_valid = False
- [ ] Return ValidationResult(is_valid, errors)

#### Edge Cases

| Edge Case | Expected Behavior |
|-----------|------------------|
| Validation on empty database | Returns is_valid=True (no configs) |
| Validation with only inactive configs | Returns is_valid=True (ignores inactive) |
| Two separate valid chains (disconnected) | Returns is_valid=True (both valid) |
| Terminal phase pointing to itself | Detected as circular, is_valid=False |
| Multiple phases pointing to same next_phase | Valid (convergent graph allowed) |

---

## Story 2: Seed Scripts for Role Prompts & Phase Configuration

### AC-2.1: Role Prompt Seeding

#### Test Scenarios

**Scenario 1: Seed Empty Database**

```bash
Given:
  Empty role_prompts table

When:
  python scripts/seed_role_prompts.py

Then:
  Console Output:
  ✓ Created pm prompt (version 1.0)
  ✓ Created architect prompt (version 1.0)
  ✓ Created ba prompt (version 1.0)
  ✓ Created dev prompt (version 1.0)
  ✓ Created qa prompt (version 1.0)
  ✓ Created commit prompt (version 1.0)
  
  ✓ Summary: 6 created, 0 skipped
  
  Exit Code: 0

Verify:
  SELECT COUNT(*) FROM role_prompts WHERE is_active = TRUE
  # Expected: 6
```

**Scenario 2: Re-run Seed Script (Idempotent)**

```bash
Given:
  Database already has 6 seeded prompts

When:
  python scripts/seed_role_prompts.py

Then:
  Console Output:
  ⊘ Skipped pm: already exists (version 1.0)
  ⊘ Skipped architect: already exists (version 1.0)
  ⊘ Skipped ba: already exists (version 1.0)
  ⊘ Skipped dev: already exists (version 1.0)
  ⊘ Skipped qa: already exists (version 1.0)
  ⊘ Skipped commit: already exists (version 1.0)
  
  ✓ Summary: 0 created, 6 skipped
  
  Exit Code: 0
```

**Scenario 3: Partial Seed (Some Exist)**

```bash
Given:
  Database has pm and architect prompts

When:
  python scripts/seed_role_prompts.py

Then:
  Console Output:
  ⊘ Skipped pm: already exists (version 1.0)
  ⊘ Skipped architect: already exists (version 1.0)
  ✓ Created ba prompt (version 1.0)
  ✓ Created dev prompt (version 1.0)
  ✓ Created qa prompt (version 1.0)
  ✓ Created commit prompt (version 1.0)
  
  ✓ Summary: 4 created, 2 skipped
  
  Exit Code: 0
```

**Scenario 4: Database Failure Mid-Seed**

```bash
Given:
  Database connection fails after 3 prompts created

When:
  python scripts/seed_role_prompts.py

Then:
  Console Output:
  ✓ Created pm prompt (version 1.0)
  ✓ Created architect prompt (version 1.0)
  ✓ Created ba prompt (version 1.0)
  ✗ Failed to create dev prompt: [connection error]
  ✗ Failed to create qa prompt: [connection error]
  ✗ Failed to create commit prompt: [connection error]
  
  ✓ Summary: 3 created, 0 skipped
  
  Exit Code: 0 (partial success - 3 critical prompts created)
```

#### Content Validation

For each seeded prompt:

| Role | Has bootstrapper | Has instructions | Has working_schema | Notes |
|------|-----------------|-----------------|-------------------|-------|
| pm | ✓ | ✓ | ✓ | Epic schema defined |
| architect | ✓ | ✓ | ✓ | ArchNotes schema |
| ba | ✓ | ✓ | ✓ | BASpec schema |
| dev | ✓ | ✓ | ✓ | ProposedChangeSet schema |
| qa | ✓ | ✓ | ✓ | QAResult schema |
| commit | ✓ | ✓ | ✓ | CommitResult schema (stub) |

**Commit Prompt Validation:**

```python
commit_prompt = RolePromptRepository.get_active_prompt("commit")

assert commit_prompt is not None
assert "stub" in commit_prompt.bootstrapper.lower() or "REPO-200" in commit_prompt.bootstrapper
assert "PR creation pending REPO-200" in commit_prompt.instructions
assert commit_prompt.working_schema["CommitResult"]["success"] == "boolean (required)"
assert commit_prompt.working_schema["CommitResult"]["message"] == "string (required)"
assert "Stub commit mentor" in commit_prompt.notes
```

---

### AC-2.2: Phase Configuration Seeding

#### Test Scenarios

**Scenario 1: Seed Empty Database**

```bash
Given:
  Empty phase_configurations table

When:
  python scripts/seed_phase_configuration.py

Then:
  Console Output:
  ✓ Created pm_phase → pm → epic → arch_phase
  ✓ Created arch_phase → architect → arch_notes → ba_phase
  ✓ Created ba_phase → ba → ba_spec → dev_phase
  ✓ Created dev_phase → dev → proposed_change_set → qa_phase
  ✓ Created qa_phase → qa → qa_result → commit_phase
  ✓ Created commit_phase → commit → commit_result → (terminal)
  
  Validating configuration graph...
  ✓ Configuration graph valid
  
  ✓ Summary: 6 created, 0 skipped, graph validated
  
  Exit Code: 0

Verify:
  SELECT COUNT(*) FROM phase_configurations WHERE is_active = TRUE
  # Expected: 6
```

**Scenario 2: Re-run Seed Script**

```bash
Given:
  Database already has 6 phase configs

When:
  python scripts/seed_phase_configuration.py

Then:
  Console Output:
  ⊘ Skipped pm_phase: already exists
  ⊘ Skipped arch_phase: already exists
  ⊘ Skipped ba_phase: already exists
  ⊘ Skipped dev_phase: already exists
  ⊘ Skipped qa_phase: already exists
  ⊘ Skipped commit_phase: already exists
  
  Validating configuration graph...
  ✓ Configuration graph valid
  
  ✓ Summary: 0 created, 6 skipped, graph validated
  
  Exit Code: 0
```

**Scenario 3: Validation Fails After Seeding**

```bash
Given:
  Manual database corruption (circular reference added)

When:
  python scripts/seed_phase_configuration.py

Then:
  Console Output:
  [... seeding completes ...]
  
  Validating configuration graph...
  ✗ Configuration graph has errors:
    - Circular reference detected starting at 'phase_a': phase_a → phase_b → phase_a
  
  Exception: ValueError("Configuration validation failed")
  
  Exit Code: 1
```

#### Chain Validation

Verify the seeded chain:

```
pm_phase → arch_phase → ba_phase → dev_phase → qa_phase → commit_phase → (terminal)
```

**Checklist:**
- [ ] pm_phase.next_phase == "arch_phase"
- [ ] arch_phase.next_phase == "ba_phase"
- [ ] ba_phase.next_phase == "dev_phase"
- [ ] dev_phase.next_phase == "qa_phase"
- [ ] qa_phase.next_phase == "commit_phase"
- [ ] commit_phase.next_phase == None (terminal)

#### Role Mapping Validation

| Phase | Role | Artifact Type |
|-------|------|--------------|
| pm_phase | pm | epic |
| arch_phase | architect | arch_notes |
| ba_phase | ba | ba_spec |
| dev_phase | dev | proposed_change_set |
| qa_phase | qa | qa_result |
| commit_phase | commit | commit_result |

---

### AC-2.3: Commit Stub Functional

#### Test Scenarios

**Scenario 1: Retrieve Commit Prompt**

```python
When:
  prompt = RolePromptRepository.get_active_prompt("commit")

Then:
  - prompt is not None
  - "stub" in prompt.bootstrapper.lower() or "REPO-200" in prompt.bootstrapper
  - "PR creation pending REPO-200" in prompt.instructions
```

**Scenario 2: Retrieve Commit Phase Config**

```python
When:
  config = PhaseConfigurationRepository.get_by_phase("commit_phase")

Then:
  - config is not None
  - config.role_name == "commit"
  - config.artifact_type == "commit_result"
  - config.next_phase is None  # Terminal phase
```

**Scenario 3: Validate Commit Can Be Used**

```python
Given:
  Pipeline in qa_phase

When:
  # In 175B, this will work:
  # advance_phase(pipeline_id)

Then:
  # For 175A, verify config exists:
  commit_config = PhaseConfigurationRepository.get_by_phase("commit_phase")
  assert commit_config is not None
  
  # Can build commit prompt:
  service = RolePromptService()
  prompt, prompt_id = service.build_prompt("commit", "pip_test", "commit_phase")
  assert len(prompt) > 0
```

---

### AC-2.4: Error Handling

#### Test Scenarios

**Scenario 1: Individual Prompt Creation Fails**

```python
Given:
  Database allows 5 prompts but artificially fails on 6th

When:
  python scripts/seed_role_prompts.py

Then:
  Console Output:
  ✓ Created pm prompt
  ✓ Created architect prompt
  ✓ Created ba prompt
  ✓ Created dev prompt
  ✓ Created qa prompt
  ✗ Failed to create commit prompt: [specific error]
  
  ✓ Summary: 5 created, 0 skipped
  
  Exit Code: 0 (5 critical prompts succeeded)
```

**Scenario 2: Database Connection Fails**

```python
Given:
  Database is offline

When:
  python scripts/seed_role_prompts.py

Then:
  Console Output:
  ✗ Failed to create pm prompt: connection refused
  ✗ Failed to create architect prompt: connection refused
  [... all fail with same error ...]
  
  ✓ Summary: 0 created, 0 skipped
  
  Exit Code: 1 (critical failure - no prompts seeded)
```

**Scenario 3: Validation Fails with Clear Errors**

```python
Given:
  Phase config has missing role reference

When:
  python scripts/seed_phase_configuration.py

Then:
  Console Output:
  [... seeding completes ...]
  
  Validating configuration graph...
  ✗ Configuration graph has errors:
    - Phase 'ba_phase' references non-existent role 'ba'
  
  ValueError: Configuration validation failed
  
  Exit Code: 1
```

#### Error Message Format

All error messages follow this format:

```
✗ Failed to [action] [entity]: [specific error]

Examples:
✗ Failed to create pm prompt: bootstrapper field is required
✗ Failed to create arch_phase: role 'architect' does not exist in role_prompts
✗ Configuration graph has errors:
  - Phase 'ba_phase' references non-existent role 'ba'
```

---

### AC-2.5: Database Init Integration

#### Test Scenarios

**Scenario 1: First-Time init_database()**

```python
Given:
  Empty database (never initialized)

When:
  from app.orchestrator_api.persistence.database import init_database
  init_database()

Then:
  Console Output:
  Initializing database...
  ✓ Tables created
  
  Seeding baseline data...
  ✓ Created pm prompt (version 1.0)
  [... 5 more prompts ...]
  ✓ Summary: 6 created, 0 skipped
  
  ✓ Created pm_phase → pm → epic → arch_phase
  [... 5 more phases ...]
  Validating configuration graph...
  ✓ Configuration graph valid
  ✓ Summary: 6 created, 0 skipped, graph validated
  
  ✓ Database initialization complete

Verify:
  SELECT COUNT(*) FROM role_prompts WHERE is_active = TRUE  -- 6
  SELECT COUNT(*) FROM phase_configurations WHERE is_active = TRUE  -- 6
```

**Scenario 2: Re-run init_database() (Already Initialized)**

```python
Given:
  Database already initialized (6 prompts exist)

When:
  init_database()

Then:
  Console Output:
  ✓ Seed data already exists (6 prompts found), skipping seed
  ✓ Database initialization complete
  
  # seed_role_prompts() NOT called
  # seed_phase_configuration() NOT called
  
  Exit quickly with no errors
```

**Scenario 3: init_database() with Partial Data**

```python
Given:
  Database has tables but only 3 prompts

When:
  init_database()

Then:
  Console Output:
  ✓ Seed data already exists (3 prompts found), skipping seed
  ✓ Database initialization complete
  
  Note: Sentinel check passed (3 > 0), skipped seeding
  # For partial recovery, run seed scripts manually
```

**Scenario 4: Manual Re-run of Seed Scripts**

```python
Given:
  Database initialized but admin wants to add missing prompts

When:
  python scripts/seed_role_prompts.py

Then:
  Script runs normally
  Skips existing prompts
  Creates missing prompts
  Exit Code: 0
```

#### Sentinel Check Logic

```python
# In init_database()
session = SessionLocal()
try:
    existing_prompts = session.query(RolePrompt).count()
    
    if existing_prompts > 0:
        # Seed data exists (any prompts = already seeded)
        print(f"✓ Seed data already exists ({existing_prompts} prompts found), skipping seed")
        return
finally:
    session.close()

# If count == 0, proceed with seeding
```

#### Integration Checklist

- [ ] init_database() creates tables first
- [ ] init_database() checks for existing prompts (sentinel)
- [ ] If prompts exist (count > 0), skip seeding
- [ ] If no prompts, call seed_role_prompts()
- [ ] Then call seed_phase_configuration()
- [ ] All seed output visible in console
- [ ] Final message: "✓ Database initialization complete"
- [ ] Global flag `_initialized` set to True
- [ ] Second call to init_database() exits early

---

## Story 3: Implement RolePromptService

### AC-3.1: Prompt Loading

#### Test Scenarios

**Scenario 1: Load Existing Active Prompt**

```python
Given:
  PM prompt v1.0 is active

When:
  service = RolePromptService()
  prompt_text, prompt_id = service.build_prompt("pm", "pip_123", "pm_phase")

Then:
  - prompt_text is non-empty string
  - prompt_id starts with "rp_"
  - No errors logged
  - Returns successfully
```

**Scenario 2: Load Non-Existent Prompt**

```python
Given:
  No prompt exists for "nonexistent_role"

When:
  service.build_prompt("nonexistent_role", "pip_123", "test_phase")

Then:
  ValueError raised with message:
  "No active prompt found for role: nonexistent_role"
```

**Scenario 3: Stale Prompt Warning (>1 Year Old)**

```python
Given:
  PM prompt created 400 days ago

When:
  service.build_prompt("pm", "pip_123", "pm_phase")

Then:
  - Prompt loaded successfully
  - Warning logged at WARNING level:
    "Role prompt for 'pm' is 400 days old. Consider creating new version."
  - Prompt still returned (doesn't fail)
```

**Scenario 4: Recent Prompt (No Warning)**

```python
Given:
  PM prompt created 30 days ago

When:
  service.build_prompt("pm", "pip_123", "pm_phase")

Then:
  - Prompt loaded successfully
  - No warning logged
  - Execution normal
```

#### Validation Checklist

- [ ] Queries database for active prompt by role_name
- [ ] Returns both prompt_text and prompt_id
- [ ] Raises clear error if prompt not found
- [ ] Logs warning if prompt age > 365 days
- [ ] Warning includes actual age in days
- [ ] No warning if prompt age <= 365 days

---

### AC-3.2: Section Assembly

#### Test Scenarios

**Scenario 1: Full Prompt with All Sections**

```python
Given:
  PM prompt has:
    - starting_prompt = "Welcome to PM phase"
    - bootstrapper = "You are the PM Mentor"
    - instructions = "Your job is to create epics"
    - working_schema = {"Epic": {"epic_id": "string"}}

When:
  prompt, _ = service.build_prompt("pm", "pip_123", "pm_phase")

Then:
  Prompt contains sections in order:

Welcome to PM phase

# Role Bootstrap

You are the PM Mentor

# Instructions

Your job is to create epics

# Working Schema

```json
{
  "Epic": {
    "epic_id": "string"
  }
}
```

Verify order:
  assert prompt.index("Welcome") < prompt.index("# Role Bootstrap")
  assert prompt.index("# Role Bootstrap") < prompt.index("# Instructions")
  assert prompt.index("# Instructions") < prompt.index("# Working Schema")
```

**Scenario 2: Minimal Prompt (No Optional Fields)**

```python
Given:
  Test prompt has:
    - starting_prompt = None
    - bootstrapper = "Test bootstrap"
    - instructions = "Test instructions"
    - working_schema = None

When:
  prompt, _ = service.build_prompt("test", "pip_123", "test_phase")

Then:
  Prompt contains:

# Role Bootstrap

Test bootstrap

# Instructions

Test instructions

Verify:
  assert "Welcome" not in prompt  # No starting prompt
  assert "# Working Schema" not in prompt  # No schema
  assert "# Role Bootstrap" in prompt
  assert "# Instructions" in prompt
```

#### Section Presence Checklist

For prompt with all fields populated:
- [ ] Starting prompt appears first (if present)
- [ ] Blank line after starting prompt
- [ ] "# Role Bootstrap" header present
- [ ] Bootstrapper text present
- [ ] Blank line after bootstrapper
- [ ] "# Instructions" header present
- [ ] Instructions text present
- [ ] Blank line after instructions
- [ ] "# Working Schema" header present (if schema present)
- [ ] JSON code fence with working_schema (if present)
- [ ] Blank line after schema

---

### AC-3.3: Context Injection

#### Test Scenarios

**Scenario 1: All Context Provided**

```python
When:
  prompt, _ = service.build_prompt(
      role_name="pm",
      pipeline_id="pip_123",
      phase="pm_phase",
      epic_context="Build user authentication system with OAuth2",
      pipeline_state={"epic_id": "AUTH-100", "state": "pm_phase"},
      artifacts={"previous_epic": {"epic_id": "AUTH-099", "title": "OAuth Setup"}}
  )

Then:
  Prompt includes:

# Epic Context

Build user authentication system with OAuth2

# Pipeline State

```json
{
  "epic_id": "AUTH-100",
  "state": "pm_phase"
}
```

# Previous Artifacts

```json
{
  "previous_epic": {
    "epic_id": "AUTH-099",
    "title": "OAuth Setup"
  }
}
```

Verify:
  assert "# Epic Context" in prompt
  assert "Build user authentication" in prompt
  assert "# Pipeline State" in prompt
  assert "AUTH-100" in prompt
  assert "# Previous Artifacts" in prompt
  assert "AUTH-099" in prompt
```

**Scenario 2: No Context Provided**

```python
When:
  prompt, _ = service.build_prompt(
      role_name="pm",
      pipeline_id="pip_123",
      phase="pm_phase",
      epic_context=None,
      pipeline_state=None,
      artifacts=None
  )

Then:
  Prompt does NOT include:
  - "# Epic Context" section
  - "# Pipeline State" section
  - "# Previous Artifacts" section

Verify:
  assert "# Epic Context" not in prompt
  assert "# Pipeline State" not in prompt
  assert "# Previous Artifacts" not in prompt
```

**Scenario 3: Partial Context**

```python
When:
  prompt, _ = service.build_prompt(
      role_name="pm",
      pipeline_id="pip_123",
      phase="pm_phase",
      epic_context="Build API",
      pipeline_state=None,
      artifacts={}  # Empty dict
  )

Then:
  Prompt includes:
  - "# Epic Context" (provided)
  
  Prompt does NOT include:
  - "# Pipeline State" (None)
  - "# Previous Artifacts" (empty dict omitted)

Verify:
  assert "# Epic Context" in prompt
  assert "Build API" in prompt
  assert "# Pipeline State" not in prompt
  assert "# Previous Artifacts" not in prompt
```

#### Context Formatting Validation

- [ ] Epic context is plain text (no code fence)
- [ ] Pipeline state formatted as JSON with indent=2
- [ ] Artifacts formatted as JSON with indent=2
- [ ] JSON code fences use ` ```json ` syntax
- [ ] All JSON is valid (can be parsed)
- [ ] Empty dicts ({}) omitted, not included as "{}"
- [ ] None values omitted entirely

---

### AC-3.4: Output Format Quality

#### Format Requirements

| Element | Requirement | Example |
|---------|------------|---------|
| Headers | Markdown `# ` format | `# Role Bootstrap` |
| Blank lines | Between sections | `\n\n` between sections |
| JSON fences | Triple backticks with language | ` ```json ... ``` ` |
| Indentation | 2 spaces for JSON | `"key": "value"` |
| Line endings | Unix `\n` (not `\r\n`) | Consistent throughout |
| Total length | <50KB for typical cases | Warn if >50KB |

#### Test Scenarios

**Scenario 1: Markdown Headers Correct**

```python
Then:
  assert prompt.count("# Role Bootstrap") == 1
  assert prompt.count("# Instructions") == 1
  assert prompt.count("# Epic Context") <= 1
  assert prompt.count("#") >= 2  # At least Bootstrap + Instructions
```

**Scenario 2: JSON Properly Fenced**

```python
Then:
  # Extract all JSON blocks
  import re
  json_blocks = re.findall(r'```json\n(.*?)\n```', prompt, re.DOTALL)
  
  # Verify all are parseable
  for block in json_blocks:
      parsed = json.loads(block)
      assert isinstance(parsed, (dict, list))
```

**Scenario 3: Consistent Formatting**

```python
Then:
  # Extract pipeline state JSON
  match = re.search(r'# Pipeline State\n\n```json\n(.*?)\n```', prompt, re.DOTALL)
  if match:
      state_json = match.group(1)
      parsed = json.loads(state_json)
      
      # Verify indent is 2 spaces
      lines = state_json.split('\n')
      for line in lines:
          if line.strip().startswith('"'):
              leading_spaces = len(line) - len(line.lstrip())
              assert leading_spaces % 2 == 0  # Multiple of 2
```

**Scenario 4: Reasonable Length**

```python
Given:
  Typical prompt (PM with context)

When:
  prompt, _ = service.build_prompt("pm", ...)

Then:
  assert len(prompt) < 50000  # 50KB
  
  # If > 50KB, should log warning
  if len(prompt) >= 50000:
      # Check logs for warning
      assert "Prompt length exceeds 50KB" in captured_logs
```

#### Output Validation Checklist

- [ ] All markdown headers use `# ` prefix
- [ ] Section separators are double newlines `\n\n`
- [ ] JSON blocks enclosed in ` ```json\n...\n``` `
- [ ] JSON is valid (parseable)
- [ ] JSON indentation is 2 spaces
- [ ] No trailing whitespace on lines
- [ ] Unix line endings throughout
- [ ] Total prompt length logged (for monitoring)

---

### AC-3.5: No Hardcoded Prompts

#### Validation Method

```bash
# Grep for hardcoded prompt content
grep -r "You are the PM Mentor" app/orchestrator_api/services/
# Expected: 0 results (except in test fixtures)

grep -r "Your role is to" app/orchestrator_api/services/
# Expected: 0 results (except in test fixtures)

grep -r "produce an Epic" app/orchestrator_api/services/
# Expected: 0 results (except in seed scripts and test fixtures)
```

#### Test Scenarios

**Scenario 1: All Content from Database**

```python
Given:
  PM prompt in database with bootstrapper "Database Version 1"

When:
  prompt, _ = service.build_prompt("pm", ...)

Then:
  assert "Database Version 1" in prompt
  # Content came from database, not hardcoded
```

**Scenario 2: Service Code Has No Role-Specific Content**

```python
When:
  # Review RolePromptService source code

Then:
  # No strings like:
  assert "You are the PM Mentor" not in service_source_code
  assert "create an Epic" not in service_source_code
  
  # Only assembly logic present
  assert "# Role Bootstrap" in service_source_code  # Section headers OK
  assert "json.dumps" in service_source_code  # Assembly logic OK
```

**Scenario 3: Changing Database Changes Output**

```python
Given:
  PM prompt v1.0 with bootstrapper "Version 1"

When:
  prompt1, _ = service.build_prompt("pm", ...)

Then:
  assert "Version 1" in prompt1

Given:
  Update PM prompt to v2.0 with bootstrapper "Version 2"
  Set v2.0 as active

When:
  prompt2, _ = service.build_prompt("pm", ...)

Then:
  assert "Version 2" in prompt2
  assert "Version 1" not in prompt2
  # Proves content comes from database
```

#### Code Review Checklist

- [ ] `RolePromptService` contains zero prompt content strings
- [ ] Service only contains section assembly logic
- [ ] All prompt content loaded via `RolePromptRepository`
- [ ] No role-specific conditionals (no `if role_name == "pm"`)
- [ ] Service is generic and role-agnostic

---

## Story 4: Comprehensive Testing

### AC-4.1: Repository Tests

#### Coverage Requirements

| Repository | Methods to Test | Coverage Target |
|------------|----------------|----------------|
| RolePromptRepository | create, get_active_prompt, get_by_id, list_versions, set_active | 100% line, 100% branch |
| PhaseConfigurationRepository | create, get_by_phase, get_all_active, update_next_phase, validate_configuration_graph | 100% line, 100% branch |
| PipelinePromptUsageRepository | record_usage, get_by_pipeline, get_by_prompt | 100% line, 100% branch |

#### Test Scenarios Summary

**RolePromptRepository (17 tests):**
- Happy path: 8 tests (create, get, list, set_active)
- Edge cases: 6 tests (not found, empty results, missing fields)
- Constraints: 3 tests (unique active, foreign keys, invalid JSON)

**PhaseConfigurationRepository (17 tests):**
- Happy path: 6 tests (create, get, list, update, validate)
- Validation: 8 tests (missing refs, circular, too long, multiple errors)
- Edge cases: 3 tests (not found, terminal phase, empty DB)

**PipelinePromptUsageRepository (6 tests):**
- Happy path: 3 tests (record, get by pipeline, get by prompt)
- Constraints: 3 tests (foreign key enforcement)

#### Coverage Verification

```bash
# Run tests with coverage
pytest tests/test_orchestrator_api/test_repositories.py \
  --cov=app/orchestrator_api/persistence/repositories \
  --cov-report=html \
  --cov-report=term

# Expected output:
Name                                         Stmts   Miss  Cover
----------------------------------------------------------------
repositories.py                                250      0   100%
----------------------------------------------------------------
TOTAL                                          250      0   100%

# Check HTML report
open htmlcov/index.html
```

---

### AC-4.2: Service Tests

#### Test Scenarios Summary

**RolePromptService (15 tests):**
- Happy path: 5 tests (all sections, minimal, contexts, prompt_id)
- Error handling: 3 tests (role not found, stale warning, no warning)
- Format validation: 4 tests (headers, JSON, order, spacing)
- Context injection: 3 tests (none, partial, full)

**Example Test:**

```python
def test_build_prompt_output_parseable():
    """Test that generated prompt JSON sections are parseable."""
    service = RolePromptService()
    
    # Create test prompt
    RolePromptRepository().create(
        "test", "1.0", "boot", "inst",
        working_schema={"test": "schema"}
    )
    
    # Build with contexts
    prompt, _ = service.build_prompt(
        "test", "pip_123", "test_phase",
        pipeline_state={"key": "value"},
        artifacts={"artifact": {"data": "test"}}
    )
    
    # Extract JSON blocks
    import re
    json_blocks = re.findall(r'```json\n(.*?)\n```', prompt, re.DOTALL)
    
    # Verify all JSON blocks are parseable
    for block in json_blocks:
        parsed = json.loads(block)
        assert isinstance(parsed, (dict, list))


def test_build_prompt_no_hardcoded_content():
    """Test that prompt content comes from database, not hardcoded."""
    service = RolePromptService()
    
    # Create test prompt with unique text
    unique_text = f"UNIQUE_TEST_TEXT_{uuid.uuid4().hex}"
    RolePromptRepository().create(
        role_name="test_unique",
        version="1.0",
        bootstrapper=unique_text,
        instructions="Test"
    )
    
    prompt, _ = service.build_prompt("test_unique", "pip", "phase")
    
    # Verify unique text appears (proves it came from database)
    assert unique_text in prompt
```

---

### AC-4.3: Seed Script Tests

#### Test Scenarios

**Idempotency Tests:**
```python
test_seed_prompts_empty_database()      # 6 created, 0 skipped
test_seed_prompts_idempotent()          # 0 created, 6 skipped
test_seed_configs_empty_database()      # 6 created, validation passes
test_seed_configs_idempotent()          # 0 skipped, validation passes
```

**Error Handling Tests:**
```python
test_seed_prompts_continues_on_error()  # One fails, others succeed
test_seed_configs_validation_fails()    # Raises ValueError
```

**Content Validation Tests:**
```python
test_seed_prompts_all_have_required_fields()  # bootstrapper, instructions
test_seed_prompts_commit_is_stub()            # Contains REPO-200 reference
test_seed_configs_correct_chain()             # pm → arch → ba → dev → qa → commit → null
test_seed_configs_validation_passes()         # No graph errors
```

---

### AC-4.4: Integration Tests

#### End-to-End Workflow Test

```python
def test_integration_end_to_end():
    """
    Test complete workflow from seed to prompt building.
    
    Steps:
    1. Initialize database (triggers seeding)
    2. Verify all role prompts exist
    3. Verify all phase configs exist
    4. Build prompt for each role
    5. Verify prompts contain expected sections
    """
    # 1. Initialize
    init_database()
    
    # 2. Verify prompts
    roles = ["pm", "architect", "ba", "dev", "qa", "commit"]
    for role in roles:
        prompt = RolePromptRepository().get_active_prompt(role)
        assert prompt is not None, f"Missing prompt for {role}"
        assert prompt.bootstrapper, f"Missing bootstrapper for {role}"
        assert prompt.instructions, f"Missing instructions for {role}"
    
    # 3. Verify configs
    phases = ["pm_phase", "arch_phase", "ba_phase", "dev_phase", "qa_phase", "commit_phase"]
    for phase in phases:
        config = PhaseConfigurationRepository().get_by_phase(phase)
        assert config is not None, f"Missing config for {phase}"
    
    # 4. Build prompts
    service = RolePromptService()
    for role, phase in zip(roles, phases):
        prompt, prompt_id = service.build_prompt(
            role, f"pip_test_{role}", phase,
            epic_context="Test epic",
            pipeline_state={"state": phase}
        )
        
        # 5. Verify prompt quality
        assert len(prompt) > 100, f"Prompt too short for {role}"
        assert "# Role Bootstrap" in prompt
        assert "# Instructions" in prompt
        assert "# Epic Context" in prompt
        assert prompt_id is not None
```

#### Database Constraints Test

```python
def test_integration_database_constraints():
    """Test that database constraints work end-to-end."""
    init_database()
    
    # Test foreign key: pipeline_prompt_usage → role_prompts
    with pytest.raises(RepositoryError):
        PipelinePromptUsageRepository().record_usage(
            "pip_test", "pm", "nonexistent_prompt_id", "pm_phase"
        )
    
    # Test unique constraint: only one active prompt per role
    repo = RolePromptRepository()
    repo.create("test", "1.0", "boot", "inst", set_active=True)
    
    # Manually try to create another active (bypassing repo logic)
    session = SessionLocal()
    try:
        duplicate = RolePrompt(
            id="test_duplicate",
            role_name="test",
            version="2.0",
            bootstrapper="boot",
            instructions="inst",
            is_active=True
        )
        session.add(duplicate)
        session.commit()  # Should fail
        assert False, "Should have raised IntegrityError"
    except IntegrityError:
        pass  # Expected
    finally:
        session.close()
```

---

### AC-4.5: Performance Validation

#### Performance Test Suite

```python
def test_performance_prompt_building():
    """Test prompt building meets <100ms p95 target."""
    init_database()
    service = RolePromptService()
    
    durations = []
    for _ in range(1000):
        start = time.perf_counter()
        service.build_prompt(
            "pm", "pip_test", "pm_phase",
            epic_context="Test",
            pipeline_state={"state": "test"},
            artifacts={"test": {"data": "value"}}
        )
        duration = (time.perf_counter() - start) * 1000
        durations.append(duration)
    
    # Calculate percentiles
    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    p99 = durations[int(len(durations) * 0.99)]
    
    print(f"Prompt building: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms")
    
    # Assertions
    assert p95 < 100, f"p95 latency {p95:.2f}ms exceeds target of 100ms"
    assert p50 < 50, f"p50 latency {p50:.2f}ms exceeds expected 50ms"


def test_performance_config_lookup():
    """Test config lookup meets <10ms p95 target."""
    init_database()
    repo = PhaseConfigurationRepository()
    
    durations = []
    for _ in range(1000):
        start = time.perf_counter()
        repo.get_by_phase("pm_phase")
        duration = (time.perf_counter() - start) * 1000
        durations.append(duration)
    
    durations.sort()
    p95 = durations[int(len(durations) * 0.95)]
    
    print(f"Config lookup: p95={p95:.2f}ms")
    assert p95 < 10, f"p95 latency {p95:.2f}ms exceeds target of 10ms"
```

#### Performance Benchmarks

| Operation | Target (p95) | Measurement Method | Pass Criteria |
|-----------|--------------|-------------------|---------------|
| get_active_prompt() | <10ms | 1000 iterations | p95 < 10ms |
| get_by_phase() | <10ms | 1000 iterations | p95 < 10ms |
| build_prompt() (full context) | <100ms | 1000 iterations | p95 < 100ms |
| build_prompt() (no context) | <50ms | 1000 iterations | p95 < 50ms |
| validate_configuration_graph() | <50ms | 100 iterations | p95 < 50ms |

---

## Epic-Level Acceptance Criteria

### AC-E1: Complete Data Layer Functional

#### Validation Steps

1. **Start with empty database**
   ```bash
   rm orchestrator.db  # SQLite
   # OR
   psql -c "DROP DATABASE combine; CREATE DATABASE combine;"  # PostgreSQL
   ```

2. **Run init_database()**
   ```python
   from app.orchestrator_api.persistence.database import init_database
   init_database()
   ```

3. **Verify role_prompts table**
   ```sql
   SELECT COUNT(*) FROM role_prompts WHERE is_active = TRUE;
   -- Expected: 6
   
   SELECT role_name, version FROM role_prompts WHERE is_active = TRUE ORDER BY role_name;
   -- Expected:
   -- architect | 1.0
   -- ba        | 1.0
   -- commit    | 1.0
   -- dev       | 1.0
   -- pm        | 1.0
   -- qa        | 1.0
   ```

4. **Verify phase_configurations table**
   ```sql
   SELECT COUNT(*) FROM phase_configurations WHERE is_active = TRUE;
   -- Expected: 6
   
   SELECT phase_name, role_name, next_phase 
   FROM phase_configurations 
   WHERE is_active = TRUE 
   ORDER BY phase_name;
   -- Expected: See table below
   ```

   | phase_name | role_name | next_phase |
   |------------|-----------|------------|
   | arch_phase | architect | ba_phase |
   | ba_phase | ba | dev_phase |
   | commit_phase | commit | NULL |
   | dev_phase | dev | qa_phase |
   | pm_phase | pm | arch_phase |
   | qa_phase | qa | commit_phase |

5. **Verify foreign key relationships**
   ```python
   # Try to create usage record with invalid references
   try:
       PipelinePromptUsageRepository().record_usage(
           "nonexistent_pipeline", "pm", "nonexistent_prompt", "pm_phase"
       )
       assert False, "Should have raised error"
   except Exception as e:
       assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
   ```

#### Pass Criteria
- ✅ 6 role prompts with is_active=TRUE
- ✅ 6 phase configs with is_active=TRUE
- ✅ All foreign keys enforced
- ✅ Can query each role by name successfully
- ✅ Can query each phase by name successfully

---

### AC-E2: Prompt Building Works End-to-End

#### Validation Steps

1. **Seed database**
   ```python
   init_database()
   ```

2. **Build prompt with full context**
   ```python
   service = RolePromptService()
   
   prompt, prompt_id = service.build_prompt(
       role_name="pm",
       pipeline_id="pip_test_e2",
       phase="pm_phase",
       epic_context="Build REST API for user authentication with OAuth2 support",
       pipeline_state={
           "pipeline_id": "pip_test_e2",
           "epic_id": "AUTH-100",
           "state": "pm_phase",
           "created_at": "2025-01-01T00:00:00Z"
       },
       artifacts={}
   )
   ```

3. **Verify prompt structure**
   ```python
   assert "# Role Bootstrap" in prompt
   assert "PM Mentor" in prompt or "pm" in prompt.lower()
   assert "# Instructions" in prompt
   assert "# Epic Context" in prompt
   assert "Build REST API" in prompt
   assert "# Pipeline State" in prompt
   assert "AUTH-100" in prompt
   ```

4. **Verify prompt ID**
   ```python
   assert prompt_id is not None
   assert prompt_id.startswith("rp_")
   
   # Verify ID matches database
   db_prompt = RolePromptRepository().get_by_id(prompt_id)
   assert db_prompt.role_name == "pm"
   ```

5. **Verify execution time**
   ```python
   import time
   start = time.perf_counter()
   prompt, _ = service.build_prompt("pm", "pip", "pm_phase")
   duration = (time.perf_counter() - start) * 1000
   assert duration < 100, f"Took {duration}ms (target: <100ms)"
   ```

#### Pass Criteria
- ✅ Prompt generated successfully
- ✅ All sections present in correct order
- ✅ Context injected correctly
- ✅ Prompt ID returned and matches database
- ✅ Execution time <100ms

---

### AC-E3: Zero Impact on Existing Pipelines

#### Validation Steps

1. **Run PIPELINE-150 test suite**
   ```bash
   pytest tests/test_orchestrator_api/ -v
   ```

2. **Expected results**
   ```
   tests/test_orchestrator_api/test_pipelines.py::test_create_pipeline PASSED
   tests/test_orchestrator_api/test_pipelines.py::test_advance_phase PASSED
   tests/test_orchestrator_api/test_artifacts.py::test_submit_artifact PASSED
   [... 17 more tests ...]
   
   ==================== 20 passed in 0.38s ====================
   ```

3. **Verify API responses unchanged**
   ```python
   # Create pipeline via API
   response = client.post("/pipelines", json={"epic_id": "TEST-001"})
   
   assert response.status_code == 200
   assert "pipeline_id" in response.json()
   assert "state" in response.json()
   assert response.json()["state"] == "pm_phase"
   
   # Response format identical to PIPELINE-150
   ```

4. **Performance comparison**
   ```python
   # If PIPELINE-150 baseline available:
   # Expected: Within 5% variance
   ```

#### Pass Criteria
- ✅ All 20 PIPELINE-150 tests pass (100%)
- ✅ No test modifications required
- ✅ API response schemas unchanged
- ✅ Performance within 5% of baseline

---

### AC-E4: Audit Trail Foundation Ready

#### Validation Steps

1. **Verify table structure**
   ```sql
   -- SQLite
   PRAGMA table_info(pipeline_prompt_usage);
   
   -- PostgreSQL
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'pipeline_prompt_usage';
   ```

2. **Test foreign keys**
   ```python
   # Valid insertion
   usage = PipelinePromptUsageRepository().record_usage(
       pipeline_id="pip_test",  # Must exist
       role_name="pm",
       prompt_id="rp_valid",    # Must exist
       phase_name="pm_phase"
   )
   assert usage.id is not None
   
   # Invalid insertion (should fail)
   with pytest.raises(Exception):
       PipelinePromptUsageRepository().record_usage(
           pipeline_id="nonexistent",
           role_name="pm",
           prompt_id="rp_valid",
           phase_name="pm_phase"
       )
   ```

3. **Test query methods**
   ```python
   # Insert test records
   for i in range(3):
       PipelinePromptUsageRepository().record_usage(
           f"pip_{i}", "pm", "rp_test", f"phase_{i}"
       )
   
   # Query by pipeline
   usages = PipelinePromptUsageRepository().get_by_pipeline("pip_0")
   assert len(usages) == 1
   
   # Query by prompt
   usages = PipelinePromptUsageRepository().get_by_prompt("rp_test")
   assert len(usages) == 3
   ```

4. **Verify index performance**
   ```python
   # Insert 1000 usage records
   for i in range(1000):
       PipelinePromptUsageRepository().record_usage(
           f"pip_{i}", "pm", "rp_test", "pm_phase"
       )
   
   # Query should be fast
   import time
   start = time.perf_counter()
   usages = PipelinePromptUsageRepository().get_by_pipeline("pip_500")
   duration = (time.perf_counter() - start) * 1000
   assert duration < 10, f"Query took {duration}ms"
   ```

#### Pass Criteria
- ✅ Table exists with correct schema
- ✅ Foreign keys enforced
- ✅ Can insert valid records
- ✅ Can query by pipeline_id
- ✅ Can query by prompt_id
- ✅ Queries fast (<10ms with indexes)

---

### AC-E5: Documentation Complete

#### Documentation Deliverables

1. **Database Schema Documentation** (`docs/175a-database-schema.md`)
   - [ ] ERD diagram (mermaid or image)
   - [ ] Table descriptions
   - [ ] Field descriptions
   - [ ] Constraint documentation
   - [ ] Example queries

2. **Seed Script Documentation** (`docs/175a-seeding.md`)
   - [ ] How to run manually
   - [ ] What data gets seeded
   - [ ] Verification steps
   - [ ] Troubleshooting
   - [ ] How to add new roles/phases

3. **RolePromptService API** (`docs/175a-role-prompt-service.md`)
   - [ ] Method signature
   - [ ] Parameter descriptions
   - [ ] Return value format
   - [ ] Example usage
   - [ ] Error handling

4. **Migration Notes** (`docs/175a-migration.md`)
   - [ ] Changes from PIPELINE-150
   - [ ] Testing checklist
   - [ ] Rollback procedure

#### Verification

```bash
# Check docs exist
ls docs/175a-*.md
# Expected: 4 files

# Check minimum length
wc -l docs/175a-*.md
# Expected: Each >50 lines

# Check ERD exists
grep -l "```mermaid" docs/175a-database-schema.md
# OR
ls docs/images/175a-erd.png
```

#### Pass Criteria
- ✅ All 4 documentation files exist
- ✅ Each contains required sections
- ✅ ERD diagram included
- ✅ Example code snippets included
- ✅ No broken links/references

---

## BA Deliverables Summary

### ✅ Refined Acceptance Criteria
- All 4 stories have detailed, testable ACs
- 60+ specific test scenarios
- Edge cases documented

### ✅ Test Scenarios
- Happy path scenarios
- Error cases
- Edge cases
- Performance scenarios

### ✅ Validation Checklists
- Step-by-step verification
- Clear pass/fail criteria
- Expected outputs

### ✅ Error Messages
- User-friendly text
- Context included
- Actionable guidance

### ✅ Data Constraints
- Field types documented
- Valid ranges specified
- Constraint enforcement

### ✅ Integration Points
- init_database() workflow
- Seed script execution
- Foreign key relationships

---

**BA Phase Complete**  
**Next Phase:** Dev - Implementation of all stories  
**Document Version:** 1.0  
**Last Updated:** 2025-12-04
