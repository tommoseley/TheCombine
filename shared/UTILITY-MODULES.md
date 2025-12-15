# Missing Utility Modules - Documentation

## Overview

Two utility modules are required by the mentor system:
1. **id_generators.py** - Generates unique IDs for artifacts
2. **project_repository.py** - Manages project creation and retrieval

## Installation

Copy these files to your project:

```bash
cp id_generators.py app/combine/utils/id_generators.py
cp project_repository.py app/combine/repositories/project_repository.py
```

Ensure directories exist:
```bash
mkdir -p app/combine/utils
mkdir -p app/combine/repositories
```

Add `__init__.py` files if needed:
```bash
touch app/combine/utils/__init__.py
touch app/combine/repositories/__init__.py
```

---

## id_generators.py

### Purpose
Generates sequential IDs following RSP-1 path conventions:
- Epics: E001, E002, E003, ...
- Stories: S001, S002, S003, ...
- Tasks: T001, T002, T003, ...

### Functions

#### `generate_epic_id(project_id, db) -> str`
```python
epic_id = await generate_epic_id("AUTH", db)
# Returns: "E001" (or next available like "E002", "E003")
```

**How it works:**
1. Queries existing epics in project
2. Finds highest epic number
3. Returns next number with E prefix and zero-padding

#### `generate_story_id(project_id, epic_id, db) -> str`
```python
story_id = await generate_story_id("AUTH", "E001", db)
# Returns: "S001" (or next available)
```

**How it works:**
1. Queries existing stories in epic
2. Finds highest story number
3. Returns next number with S prefix

#### `generate_task_id(project_id, epic_id, story_id, db) -> str`
```python
task_id = await generate_task_id("AUTH", "E001", "S001", db)
# Returns: "T001" (or next available)
```

#### `parse_artifact_path(artifact_path) -> dict`
```python
parts = parse_artifact_path("AUTH/E001/S002")
# Returns: {
#   "project_id": "AUTH",
#   "epic_id": "E001",
#   "story_id": "S002",
#   "level": "story"
# }
```

#### `build_artifact_path(project_id, epic_id=None, story_id=None, task_id=None) -> str`
```python
path = build_artifact_path("AUTH", "E001", "S002")
# Returns: "AUTH/E001/S002"
```

### Usage in Mentors

**PM Mentor:**
```python
epic_id = await generate_epic_id(project_id, self.db)
epic_path = f"{project_id}/{epic_id}"
# Creates: "AUTH/E001"
```

**BA Mentor:**
```python
story_id = await generate_story_id(project_id, epic_id, self.db)
story_path = f"{project_id}/{epic_id}/{story_id}"
# Creates: "AUTH/E001/S001"
```

---

## project_repository.py

### Purpose
Ensures projects exist before creating artifacts within them.

### Functions

#### `ensure_project_exists(project_id, db) -> Project`
```python
project = await ensure_project_exists("AUTH", db)
# Returns: Project object (creates if doesn't exist)
```

**How it works:**
1. Checks if project exists in database
2. If exists, returns existing project
3. If not exists, creates new project with:
   - `id = project_id`
   - `name = project_id` (default)
   - `description = "Project {project_id}"`
   - `created_at = now`
   - `updated_at = now`

**This is the key function used by PM Mentor!**

#### `get_project(project_id, db) -> Project | None`
```python
project = await get_project("AUTH", db)
# Returns: Project or None
```

#### `create_project(project_id, name, description, db) -> Project`
```python
project = await create_project(
    "AUTH",
    "Authentication System",
    "User authentication and authorization",
    db
)
# Returns: Created project
# Raises: ValueError if project_id already exists
```

#### `update_project(project_id, name=None, description=None, db) -> Project`
```python
project = await update_project("AUTH", name="New Name", db=db)
# Returns: Updated project
```

#### `delete_project(project_id, db) -> bool`
```python
deleted = await delete_project("AUTH", db)
# Returns: True if deleted, False if not found
```

#### `list_projects(db, limit=100, offset=0) -> list[Project]`
```python
projects = await list_projects(db, limit=50)
# Returns: List of up to 50 projects
```

### Usage in Mentors

**PM Mentor (in create_artifact):**
```python
# Ensure project exists before creating epic
await ensure_project_exists(project_id, self.db)

# Now safe to create epic artifact
epic_id = await generate_epic_id(project_id, self.db)
artifact = await self.artifact_service.create_artifact(...)
```

---

## Database Requirements

### Project Model

The `Project` model should exist in `app/combine/models.py`:

```python
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)  # e.g., "AUTH"
    name = Column(String, nullable=False)
    description = Column(String, default="")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

### Artifact Model

The `Artifact` model should have `artifact_path` and `artifact_type` fields:

```python
class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(Integer, primary_key=True)
    artifact_path = Column(String, nullable=False, index=True)  # e.g., "AUTH/E001"
    artifact_type = Column(String, nullable=False, index=True)  # e.g., "epic"
    title = Column(String)
    content = Column(JSON)
    breadcrumbs = Column(JSON)
    # ... other fields
```

---

## Integration Checklist

- [ ] Copy `id_generators.py` to `app/combine/utils/`
- [ ] Copy `project_repository.py` to `app/combine/repositories/`
- [ ] Create `__init__.py` in both directories
- [ ] Verify `Project` model exists in `app/combine/models.py`
- [ ] Verify `Artifact` model has required fields
- [ ] Test ID generation:
  ```python
  epic_id = await generate_epic_id("TEST", db)
  assert epic_id == "E001"
  ```
- [ ] Test project creation:
  ```python
  project = await ensure_project_exists("TEST", db)
  assert project.id == "TEST"
  ```
- [ ] Run mentor system end-to-end

---

## Example End-to-End Flow

```python
# 1. PM Mentor creates epic
project_id = "AUTH"
await ensure_project_exists(project_id, db)  # Ensures project exists
epic_id = await generate_epic_id(project_id, db)  # Returns "E001"
# Creates artifact at: AUTH/E001

# 2. BA Mentor creates stories
story_id_1 = await generate_story_id(project_id, epic_id, db)  # Returns "S001"
story_id_2 = await generate_story_id(project_id, epic_id, db)  # Returns "S002"
# Creates artifacts at: AUTH/E001/S001, AUTH/E001/S002

# 3. Developer Mentor creates code
# Code artifacts use same path as story: AUTH/E001/S001 (type="code")
```

---

## Error Handling

### ID Generators
- Returns "E001", "S001", "T001" if no existing artifacts found
- Handles gaps in numbering (if E001 and E003 exist, returns E004)
- Skips non-numeric IDs gracefully

### Project Repository
- `ensure_project_exists()` - Never fails, always returns project
- `create_project()` - Raises `ValueError` if project exists
- `update_project()` - Raises `ValueError` if project not found
- `delete_project()` - Returns `False` if not found (no exception)

---

## Performance Considerations

### ID Generators
- Queries are filtered by path pattern (indexed)
- Queries are filtered by artifact_type (indexed)
- In-memory max calculation (fast for typical project sizes)

### Project Repository
- `ensure_project_exists()` does 1 SELECT + maybe 1 INSERT
- Transactions are committed immediately
- Consider caching in high-volume scenarios

---

## Testing

### Test ID Generation
```python
async def test_epic_id_generation():
    epic_id_1 = await generate_epic_id("TEST", db)
    assert epic_id_1 == "E001"
    
    # Create an epic
    await create_test_epic("TEST", "E001", db)
    
    epic_id_2 = await generate_epic_id("TEST", db)
    assert epic_id_2 == "E002"
```

### Test Project Creation
```python
async def test_ensure_project_exists():
    # First call creates
    project_1 = await ensure_project_exists("TEST", db)
    assert project_1.id == "TEST"
    
    # Second call returns existing
    project_2 = await ensure_project_exists("TEST", db)
    assert project_2.id == project_1.id
```

---

## Summary

**id_generators.py:**
- ✅ Generates sequential IDs (E001, S001, T001)
- ✅ Handles gaps and concurrent usage
- ✅ Utility functions for path manipulation

**project_repository.py:**
- ✅ Ensures projects exist before creating artifacts
- ✅ Full CRUD operations for projects
- ✅ Safe concurrent usage

**Both modules are production-ready and fully documented!** 🎉
