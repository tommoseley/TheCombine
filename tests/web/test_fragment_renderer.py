"""
Tests for Fragment Renderer (ADR-032).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.web.bff.fragment_renderer import (
    FragmentRenderer,
    FragmentRenderError,
    NoActiveBindingError,
)


@pytest.fixture
def mock_registry():
    """Create mock fragment registry service."""
    return AsyncMock()


@pytest.fixture
def renderer(mock_registry):
    return FragmentRenderer(mock_registry)


def make_fragment(fragment_id: str, markup: str, version: str = "1.0"):
    """Create a mock fragment artifact."""
    fragment = MagicMock()
    fragment.fragment_id = fragment_id
    fragment.version = version
    fragment.fragment_markup = markup
    return fragment


# =============================================================================
# Test: Render Single Item
# =============================================================================

@pytest.mark.asyncio
async def test_render_single_item(renderer, mock_registry):
    """Render a single item with simple template."""
    markup = "<div>{{ item.text }}</div>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    result = await renderer.render("TestTypeV1", {"text": "Hello"})
    
    assert result == "<div>Hello</div>"


@pytest.mark.asyncio
async def test_render_with_conditional_content(renderer, mock_registry):
    """Render with conditional Jinja2 logic."""
    markup = """<div>{{ item.text }}{% if item.important %} (!important){% endif %}</div>"""
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    # With important=True
    result = await renderer.render("TestTypeV1", {"text": "Hello", "important": True})
    assert "(!important)" in result
    
    # Clear cache to test without important
    renderer.clear_cache()
    
    # With important=False
    result = await renderer.render("TestTypeV1", {"text": "Hello", "important": False})
    assert "(!important)" not in result


@pytest.mark.asyncio
async def test_render_with_context(renderer, mock_registry):
    """Render with additional context variables."""
    markup = "<div>{{ item.text }} - {{ extra }}</div>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    result = await renderer.render(
        "TestTypeV1",
        {"text": "Hello"},
        context={"extra": "World"}
    )
    
    assert result == "<div>Hello - World</div>"


# =============================================================================
# Test: Render List
# =============================================================================

@pytest.mark.asyncio
async def test_render_list(renderer, mock_registry):
    """Render a list of items."""
    markup = "<li>{{ item.name }}</li>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    items = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]
    result = await renderer.render_list("TestTypeV1", items)
    
    assert "<li>Alice</li>" in result
    assert "<li>Bob</li>" in result
    assert "<li>Charlie</li>" in result


@pytest.mark.asyncio
async def test_render_list_empty(renderer, mock_registry):
    """Render empty list returns empty string."""
    result = await renderer.render_list("TestTypeV1", [])
    
    assert result == ""
    mock_registry.get_active_fragment_for_type.assert_not_called()


@pytest.mark.asyncio
async def test_render_list_with_index(renderer, mock_registry):
    """Render list provides index variable."""
    markup = "<li>{{ index }}: {{ item.name }}</li>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    items = [{"name": "First"}, {"name": "Second"}]
    result = await renderer.render_list("TestTypeV1", items)
    
    assert "0: First" in result
    assert "1: Second" in result


@pytest.mark.asyncio
async def test_render_list_custom_separator(renderer, mock_registry):
    """Render list with custom separator."""
    markup = "<span>{{ item.name }}</span>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    items = [{"name": "A"}, {"name": "B"}]
    result = await renderer.render_list("TestTypeV1", items, separator=" | ")
    
    assert result == "<span>A</span> | <span>B</span>"


# =============================================================================
# Test: Error Handling
# =============================================================================

@pytest.mark.asyncio
async def test_render_missing_binding_raises(renderer, mock_registry):
    """Render with no active binding raises error."""
    mock_registry.get_active_fragment_for_type.return_value = None
    
    with pytest.raises(NoActiveBindingError) as exc:
        await renderer.render("MissingType", {"text": "test"})
    
    assert "MissingType" in str(exc.value)


@pytest.mark.asyncio
async def test_render_invalid_template_raises(renderer, mock_registry):
    """Invalid template syntax raises error."""
    markup = "<div>{{ item.text }</div>"  # Missing closing brace
    fragment = make_fragment("BadFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    with pytest.raises(FragmentRenderError):
        await renderer.render("TestTypeV1", {"text": "test"})


# =============================================================================
# Test: Caching
# =============================================================================

@pytest.mark.asyncio
async def test_render_caches_compiled_template(renderer, mock_registry):
    """Compiled templates are cached."""
    markup = "<div>{{ item.text }}</div>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    # First render
    await renderer.render("TestTypeV1", {"text": "First"})
    assert renderer.cache_size == 1
    
    # Second render should use cache
    await renderer.render("TestTypeV1", {"text": "Second"})
    assert renderer.cache_size == 1  # Still 1, not 2


@pytest.mark.asyncio
async def test_clear_cache(renderer, mock_registry):
    """Cache can be cleared."""
    markup = "<div>{{ item.text }}</div>"
    fragment = make_fragment("TestFragment", markup)
    mock_registry.get_active_fragment_for_type.return_value = fragment
    
    await renderer.render("TestTypeV1", {"text": "test"})
    assert renderer.cache_size == 1
    
    renderer.clear_cache()
    assert renderer.cache_size == 0