# The Combine Template Pattern (Updated)

## Official Pattern: Include-Based Partials with Single Route

This is our standard pattern for all pages that need both full-page and HTMX partial rendering.

**Key Innovation:** One route handles both cases by detecting the `HX-Request` header.

---

## The Pattern (Simplified)

### 1. Template Structure (Unchanged)

```
pages/
├── project_detail.html          # Wrapper: {% extends %} + {% include %}
└── partials/
    └── _project_content.html    # Content only (no layout)
```

**`pages/project_detail.html`** (5 lines):
```html
{% extends "layout/base.html" %}
{% block title %}{{ project.name }} - The Combine{% endblock %}
{% block content %}
    {% include "pages/partials/_project_content.html" %}
{% endblock %}
```

**`pages/partials/_project_content.html`** (200+ lines):
```html
<div class="max-w-7xl mx-auto px-4 py-6">
    <!-- All your content here -->
</div>
```

### 2. Single Route (New!)

```python
@router.get("/projects/{project_id}")
async def get_project_detail(request: Request, project_id: str, db: AsyncSession):
    """
    Single route handles both:
    - Browser navigation → Full page with layout
    - HTMX request → Content only
    """
    # Get project data (once)
    project = await get_project_data(project_id, db)
    
    context = {
        "request": request,
        "project": project,
        # ... other data
    }
    
    # Detect HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"
    
    # Return appropriate template
    template = "pages/partials/_project_content.html" if is_htmx else "pages/project_detail.html"
    
    return templates.TemplateResponse(template, context)
```

**That's it!**

---

## How It Works

### Browser Navigation (Full Page)
```
User → /projects/123
    ↓
Headers: (no HX-Request)
    ↓
is_htmx = False
    ↓
template = "pages/project_detail.html"
    ↓
Returns: Full page with layout
```

### HTMX Click (Partial)
```
User → Clicks project in sidebar
    ↓
HTMX → GET /projects/123
    ↓
Headers: HX-Request: true
    ↓
is_htmx = True
    ↓
template = "pages/partials/_project_content.html"
    ↓
Returns: Content only (no layout)
```

---

## Advantages Over Two-Route Approach

| Aspect | Two Routes | Single Route ✅ |
|--------|-----------|-----------------|
| **Routes** | `/projects/123` + `/projects/123/partial` | Just `/projects/123` |
| **Code duplication** | High (duplicate logic) | None (shared logic) |
| **Surface area** | 2× routes to maintain | 1× route to maintain |
| **URL simplicity** | Two URLs for same resource | One canonical URL |
| **Testing** | Test 2 routes | Test 1 route, 2 headers |
| **Maintainability** | Update in 2 places | Update in 1 place |

---

## Template Benefits (Unchanged)

✅ **One source of truth** - Edit `_project_content.html`, both full and partial use it  
✅ **No duplication** - Content defined once  
✅ **Clear separation** - Layout vs content  
✅ **Standard pattern** - Partial prefix with `_`  

---

## Complete Example

### Directory Structure
```
app/web/templates/
├── layout/
│   └── base.html
├── pages/
│   ├── project_detail.html          # 5 lines: extends + include
│   └── partials/
│       └── _project_content.html    # 200+ lines: actual content
```

### Route (routes.py)
```python
@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def get_project_detail(
    request: Request,
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Get data
    project = await project_service.get_project(project_id, db)
    
    context = {
        "request": request,
        "project": project,
        "epics": [],
        # ... other data
    }
    
    # Detect HTMX
    is_htmx = request.headers.get("HX-Request") == "true"
    
    # Choose template
    template = (
        "pages/partials/_project_content.html" if is_htmx 
        else "pages/project_detail.html"
    )
    
    return templates.TemplateResponse(template, context)
```

### HTMX Link (in sidebar)
```html
<a 
    href="/ui/projects/{{ project.id }}"
    hx-get="/ui/projects/{{ project.id }}"
    hx-target="#main-content"
    hx-push-url="true">
    {{ project.name }}
</a>
```

**HTMX automatically adds `HX-Request: true` header - you don't need to do anything!**

---

## Migration Checklist

For each page:

- [ ] Create `pages/partials/_entity_content.html` (content only)
- [ ] Create/update `pages/entity_detail.html` (wrapper with include)
- [ ] Create/update **single** route with HX-Request detection
- [ ] Delete old `/partial` route if it exists
- [ ] Update HTMX links (ensure `hx-get` points to main route)
- [ ] Test both: direct navigation + HTMX click

---

## Common Patterns

### Helper Function (Recommended for Complex Pages)
```python
async def get_project_context(project_id: str, db: AsyncSession) -> dict:
    """Build context once, use for both full and partial"""
    project = await project_service.get_project(project_id, db)
    epics = await epic_service.get_epics(project_id, db)
    
    return {
        "project": project,
        "epics": epics,
        # ... other data
    }

@router.get("/projects/{project_id}")
async def get_project_detail(request: Request, project_id: str, db: AsyncSession):
    context = await get_project_context(project_id, db)
    context["request"] = request
    
    is_htmx = request.headers.get("HX-Request") == "true"
    template = "pages/partials/_project_content.html" if is_htmx else "pages/project_detail.html"
    
    return templates.TemplateResponse(template, context)
```

### Ternary for Template Selection
```python
template = (
    "pages/partials/_project_content.html" if is_htmx 
    else "pages/project_detail.html"
)
```

### Error Handling (Return Appropriate Format)
```python
except Exception as e:
    error_html = f"<div>Error: {str(e)}</div>"
    
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return HTMLResponse(error_html)  # Partial error
    else:
        return full_error_page(error_html)  # Full page error
```

---

## Why This Is Better

### Before (Two Routes):
```python
# Route 1: Full page
@router.get("/projects/{id}")
async def get_project_detail(...):
    project = await get_project(...)  # ← Duplicate
    context = {...}                    # ← Duplicate
    return templates.TemplateResponse("pages/project_detail.html", context)

# Route 2: Partial
@router.get("/projects/{id}/partial")
async def get_project_detail_partial(...):
    project = await get_project(...)  # ← Duplicate
    context = {...}                    # ← Duplicate
    return templates.TemplateResponse("pages/partials/_project_content.html", context)
```
**Problems:** Duplicate code, two URLs, more maintenance

### After (Single Route):
```python
@router.get("/projects/{id}")
async def get_project_detail(...):
    project = await get_project(...)  # ← Once
    context = {...}                    # ← Once
    
    template = "_project_content.html" if is_htmx else "project_detail.html"
    return templates.TemplateResponse(template, context)
```
**Benefits:** DRY, one URL, less maintenance

---

## The Official Pattern

**Every page in The Combine follows this:**

1. **One route** per resource (`/projects/{id}`)
2. **Two templates** (wrapper + partial)
3. **HX-Request detection** (automatic from HTMX)
4. **Include pattern** (wrapper includes partial)

**No exceptions.** 🎯

---

## Quick Reference

| Element | Location | Purpose |
|---------|----------|---------|
| Full wrapper | `pages/entity_detail.html` | 5 lines: extends + include |
| Content partial | `pages/partials/_entity_content.html` | All the actual content |
| Route | One route with HX-Request check | Returns appropriate template |
| HTMX link | `hx-get="/ui/entity/{id}"` | Automatically sets HX-Request |

---

**This is The Way.** ™
