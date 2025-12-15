"""
Shared utilities for UI routes
Template Pattern V2: HX-Request detection for full page vs partial rendering
"""

from fastapi import Request
from fastapi.templating import Jinja2Templates

# Initialize templates (shared across all route modules)
templates = Jinja2Templates(directory="app/web/templates")


# Register custom filters
def pluralize(count, singular='', plural='s'):
    """Pluralize filter: {{ count|pluralize }} returns '' if count==1 else 's'"""
    if isinstance(count, (list, tuple)):
        count = len(count)
    return singular if count == 1 else plural


templates.env.filters['pluralize'] = pluralize


def is_htmx_request(request: Request) -> bool:
    """Check if request is from HTMX (partial content needed)"""
    return request.headers.get("HX-Request") == "true"


def get_template(request: Request, wrapper: str, partial: str) -> str:
    """
    Return appropriate template based on request type.
    
    - Browser navigation (no HX-Request header) → wrapper template (extends base.html)
    - HTMX request (HX-Request: true) → partial template (content only)
    """
    return partial if is_htmx_request(request) else wrapper