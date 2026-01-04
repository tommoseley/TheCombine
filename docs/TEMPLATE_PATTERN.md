# The Combine Template Pattern

## Official Pattern: Include-Based Partials

This is our standard pattern for all pages that need both full-page and HTMX partial rendering.

---

## Directory Structure

```
app/web/templates/
├── layout/
│   └── base.html                    # Site-wide layout (header, sidebar, etc.)
├── pages/
│   ├── project_detail.html          # Full page wrapper
│   ├── epic_detail.html             # Full page wrapper
│   ├── story_detail.html            # Full page wrapper
│   └── partials/
│       ├── _project_content.html    # Content only (no layout)
│       ├── _epic_content.html       # Content only (no layout)
│       └── _story_content.html      # Content only (no layout)
└── components/
    └── tree/
        ├── project_collapsed.html
        └── project_expanded.html
```

---

## Naming Conventions

### Full Page Templates
- Location: `pages/`
- Name: `{entity}_detail.html` (e.g., `project_detail.html`)
- Purpose: Wrap content with full layout
- Contains: `{% extends %}` and `{% include %}`
- Used by: Routes that serve full pages

### Partial Templates
- Location: `pages/partials/`
- Name: `_{entity}_content.html` (e.g., `_project_content.html`)
- Prefix: **Underscore `_`** (indicates partial/fragment)
- Purpose: Content only, no layout
- Contains: Pure HTML, no `{% extends %}`
- Used by: HTMX routes, or included by full page templates

### Component Templates
- Location: `components/{type}/`
- Name: Descriptive (e.g., `project_collapsed.html`)
- Purpose: Reusable UI components
- Contains: Small, focused HTML fragments

---

## The Pattern

### 1. Create the Content Partial

**File: `pages/partials/_project_content.html`**

```html
<div class="max-w-7xl mx-auto px-4 py-6">
    <!-- Breadcrumbs -->
    <nav>...</nav>
    
    <!-- Page Header -->
    <div>
        <h1>{{ project.name }}</h1>
        <p>{{ project.description }}</p>
    </div>
    
    <!-- Main Content -->
    <div>
        <!-- All your page content here -->
        <!-- Workflow controls, data tables, forms, etc. -->
    </div>
</div>
```

**Rules:**
- ❌ No `{% extends "layout/base.html" %}`
- ❌ No `{% block content %}`
- ✅ Just pure HTML content
- ✅ Can use `{% if %}`, `{% for %}`, variables
- ✅ Can include other partials/components

### 2. Create the Full Page Wrapper

**File: `pages/project_detail.html`**

```html
{% extends "layout/base.html" %}

{% block title %}{{ project.name }} - The Combine{% endblock %}

{% block content %}
    {% include "pages/partials/_project_content.html" %}
{% endblock %}
```

**That's it! Just 5 lines.**

### 3. Create Two Routes

**Full Page Route:**
```python
@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def get_project_detail(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Full page with layout - for direct navigation"""
    project = await get_project_data(project_id, db)
    
    return templates.TemplateResponse(
        "pages/project_detail.html",  # Uses wrapper → includes partial
        {
            "request": request,
            "project": project,
            # ... other data
        }
    )
```

**Partial Route:**
```python
@router.get("/projects/{project_id}/partial", response_class=HTMLResponse)
async def get_project_detail_partial(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Content only - for HTMX loading"""
    project = await get_project_data(project_id, db)
    
    return templates.TemplateResponse(
        "pages/partials/_project_content.html",  # Direct to partial
        {
            "request": request,
            "project": project,
            # ... same data as full page
        }
    )
```

**Key Points:**
- ✅ Both routes use **identical data**
- ✅ Only difference is which template they render
- ✅ Content is maintained in **one place**

---

## How It Works

### User Navigates Directly (Full Page)
```
User → /projects/123
    ↓
Route: get_project_detail()
    ↓
Render: pages/project_detail.html
    ├─ Extends: layout/base.html (header, sidebar, CSS)
    └─ Includes: pages/partials/_project_content.html
    ↓
Browser receives: Complete HTML page with layout
```

### User Clicks Sidebar Link (HTMX)
```
User → Clicks project in sidebar
    ↓
HTMX → GET /projects/123/partial
    ↓
Route: get_project_detail_partial()
    ↓
Render: pages/partials/_project_content.html
    ↓
HTMX receives: Just the content div
    ↓
HTMX replaces: #main-content with new content
    ↓
Layout stays intact (no reload)
```

---

## Benefits

### ✅ Maintainability
- **One source of truth** - Edit `_project_content.html`, both routes updated
- **No duplication** - Content defined once
- **Easy to debug** - Clear separation of concerns

### ✅ Performance
- **HTMX efficiency** - Only sends content that changes
- **No double layout** - Partial has no wrapper
- **Fast page loads** - Full page has everything

### ✅ Developer Experience
- **Clear intent** - File names tell you what they do
- **Standard pattern** - Used by Django, Rails, Phoenix, etc.
- **Easy to learn** - New devs understand immediately

### ✅ Flexibility
- **Can nest partials** - Include partials within partials
- **Can reuse** - Use same partial in different layouts
- **Can test** - Test partials independently

---

## Examples

### Example 1: Project Detail Page

```
pages/
├── project_detail.html          # Wrapper
└── partials/
    └── _project_content.html    # Content
```

Routes:
- `/projects/123` → Full page
- `/projects/123/partial` → Content only

### Example 2: Epic Detail Page

```
pages/
├── epic_detail.html             # Wrapper
└── partials/
    └── _epic_content.html       # Content
```

Routes:
- `/epics/456` → Full page
- `/epics/456/partial` → Content only

### Example 3: Nested Partials

**`_project_content.html` can include other partials:**

```html
<div class="max-w-7xl mx-auto px-4 py-6">
    <h1>{{ project.name }}</h1>
    
    <!-- Include architecture section -->
    {% if architecture %}
        {% include "pages/partials/_architecture_section.html" %}
    {% endif %}
    
    <!-- Include epics list -->
    {% include "pages/partials/_epics_list.html" %}
</div>
```

This keeps files small and focused!

---

## Migration Checklist

When converting an existing page to this pattern:

- [ ] Create `partials/` directory if needed
- [ ] Move content to `_entity_content.html` (remove `{% extends %}`)
- [ ] Create/update `entity_detail.html` wrapper (just 5 lines)
- [ ] Update full page route to use wrapper
- [ ] Update partial route to use `_content` file
- [ ] Test both routes
- [ ] Delete old template if separate

---

## Common Mistakes to Avoid

### ❌ DON'T: Put `{% extends %}` in the partial
```html
<!-- pages/partials/_project_content.html -->
{% extends "layout/base.html" %}  ← WRONG!
<div>content</div>
```

### ✅ DO: Keep partial pure
```html
<!-- pages/partials/_project_content.html -->
<div>content</div>  ← RIGHT!
```

### ❌ DON'T: Duplicate content
```html
<!-- project_detail.html -->
<div>All the content copied here</div>

<!-- partials/_project_content.html -->
<div>All the content copied here again</div>
```

### ✅ DO: Include the partial
```html
<!-- project_detail.html -->
{% extends "layout/base.html" %}
{% block content %}
    {% include "pages/partials/_project_content.html" %}
{% endblock %}
```

### ❌ DON'T: Use different data for full vs partial
```python
# Full page
return templates.TemplateResponse("...", {"project": full_data})

# Partial
return templates.TemplateResponse("...", {"project": partial_data})
```

### ✅ DO: Use identical data
```python
# Helper function
def get_project_context(project_id, db):
    return {
        "project": project,
        "epics": epics,
        # ... same for both
    }

# Both routes
return templates.TemplateResponse(template_name, get_project_context(...))
```

---

## Quick Reference

| Need | Use | Example |
|------|-----|---------|
| Full page load | `pages/{entity}_detail.html` | `pages/project_detail.html` |
| HTMX partial | `pages/partials/_{entity}_content.html` | `partials/_project_content.html` |
| Reusable component | `components/{type}/{name}.html` | `components/tree/project_collapsed.html` |
| Layout wrapper | `layout/base.html` | Base layout with header/sidebar |

---

## This Is The Way ™

Every page in The Combine follows this pattern. No exceptions. 🎯

**Questions? See examples in:**
- `pages/project_detail.html` + `partials/_project_content.html`
- (Future) `pages/epic_detail.html` + `partials/_epic_content.html`
- (Future) `pages/story_detail.html` + `partials/_story_content.html`
