# Template Pattern V2 Implementation

## New Folder Structure

### Routes (Modular)
```
app/web/routes/
├── __init__.py              # Main router - combines all modules
├── shared.py                # Template utilities, HX-Request detection
├── home_routes.py           # Home page
├── project_routes.py        # Project CRUD, tree navigation
├── architecture_routes.py   # Architecture views, architect mentor
├── epic_routes.py           # Epic details, stories list
├── story_routes.py          # Story details, code views
├── search_routes.py         # Global search
├── mentor_routes.py         # AI mentor forms
└── debug_routes.py          # Test/debug endpoints
```

### Templates
```
app/web/templates/
├── layout/
│   └── base.html                          # Main layout (unchanged)
├── components/
│   ├── sidebar.html                       # Sidebar (unchanged)
│   ├── code_file.html                     # Code viewer component
│   ├── search_results.html                # Search results dropdown
│   ├── alerts/
│   │   ├── success.html                   # Success alert component
│   │   └── error.html                     # Error alert component
│   └── tree/
│       ├── project_list.html
│       ├── project_collapsed.html
│       ├── project_expanded.html
│       ├── epic_collapsed.html
│       └── epic_expanded.html
└── pages/
    ├── home.html                          # Wrapper (5 lines)
    ├── project_detail.html                # Wrapper
    ├── project_new.html                   # Wrapper
    ├── architecture_view.html             # Wrapper
    ├── epic_detail.html                   # Wrapper
    ├── epic_stories.html                  # Wrapper
    ├── story_detail.html                  # Wrapper
    ├── story_code.html                    # Wrapper
    └── partials/
        ├── _home_content.html             # Content
        ├── _project_detail_content.html   # Content
        ├── _project_new_content.html      # Content
        ├── _architecture_view_content.html
        ├── _epic_detail_content.html
        ├── _epic_stories_content.html
        ├── _story_detail_content.html
        └── _story_code_content.html
```

## How It Works

### HX-Request Detection (shared.py)
```python
def get_template(request: Request, wrapper: str, partial: str) -> str:
    """Return appropriate template based on request type"""
    is_htmx = request.headers.get("HX-Request") == "true"
    return partial if is_htmx else wrapper
```

### Route Example
```python
@router.get("/{project_id}", response_class=HTMLResponse)
async def get_project_detail(request: Request, project_id: str, db: AsyncSession):
    project = await get_project(project_id, db)
    
    template = get_template(
        request,
        wrapper="pages/project_detail.html",        # Full page with base.html
        partial="pages/partials/_project_detail_content.html"  # Content only
    )
    
    return templates.TemplateResponse(template, {"request": request, "project": project})
```

## Installation Steps

1. **Backup existing files**
   ```bash
   cp -r app/web/routes app/web/routes.bak
   cp -r app/web/templates app/web/templates.bak
   ```

2. **Copy routes folder**
   - Copy `routes/` folder to `app/web/routes/`

3. **Copy template files**
   - Copy `pages/` to `app/web/templates/pages/`
   - Copy `components/alerts/` to `app/web/templates/components/alerts/`

4. **Update main.py**
   ```python
   # Change from:
   from app.web.routes import router as ui_router
   
   # To:
   from app.web.routes import router as ui_router
   ```

5. **Restart server and test**
   - Direct navigation: `http://localhost:8000/ui/projects/new`
   - HTMX click: Click "New Project" in sidebar

## Key Benefits

| Before | After |
|--------|-------|
| Single 850+ line routes.py | 8 focused route modules |
| Duplicate routes for full/partial | Single route with HX-Request detection |
| Hard to find specific routes | Clear domain separation |
| Monolithic templates | Wrapper + partial pattern |
