"""Intent-first tests for Admin Executions List UX (WS-ADMIN-EXEC-UI-001).

Testing approach: Source-level structural inspection of ExecutionList.jsx.
No React test harness is configured; these are bootstrap proxies for
behavioral verification.

MODE B DEBT: When a React test harness is established, upgrade these to
render-level behavioral assertions (sort order, filter reduction, empty state).

Criteria:
C1: Full execution ID display (no ellipsis)
C2: Project code column with UUID-to-code resolution
C3: Sortable column headers with direction indicator
C4: Document type filter control
C5: Search input with empty-state handling
"""

import os
import re

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXEC_LIST_PATH = os.path.join(
    REPO_ROOT, "spa", "src", "components", "admin", "ExecutionList.jsx"
)


@pytest.fixture
def source():
    """Read ExecutionList.jsx source code."""
    with open(EXEC_LIST_PATH) as f:
        return f.read()


# ---------------------------------------------------------------------------
# C1: Full Execution ID Display
# ---------------------------------------------------------------------------
class TestC1FullExecutionId:
    """Execution ID must be shown in full — no truncation, no ellipsis."""

    def test_no_substring_truncation(self, source):
        """Source must not truncate execution ID via substring/slice."""
        # The original code used: exec.id?.substring(0, 8) + '...'
        assert "substring(0, 8)" not in source, (
            "ExecutionList still truncates execution ID to 8 chars"
        )

    def test_no_ellipsis_in_id_rendering(self, source):
        """Rendered ID cell must not append literal '...' or ellipsis character."""
        # Look for patterns like: {exec.id}... or + '...' near the id cell
        # The old code had: {exec.id?.substring(0, 8)}...
        has_ellipsis_after_id = bool(
            re.search(r"exec\.id.*?\.\.\.", source)
        )
        assert not has_ellipsis_after_id, (
            "ExecutionList renders ellipsis after execution ID"
        )


# ---------------------------------------------------------------------------
# C2: Project Code Column
# ---------------------------------------------------------------------------
class TestC2ProjectCodeColumn:
    """A Project column must display human-readable codes (e.g. LIR-001)."""

    def test_project_column_header_exists(self, source):
        """Table must have a 'Project' column header."""
        # Component may use data-driven columns: { label: 'Project' }
        # or literal JSX: >Project<
        has_header = bool(
            re.search(r">\s*Project\s*<|label:\s*['\"]Project['\"]", source)
        )
        assert has_header, (
            "ExecutionList has no 'Project' column header"
        )

    def test_project_lookup_from_api(self, source):
        """Component must call api.getProjects() to build UUID-to-code map."""
        assert "getProjects" in source, (
            "ExecutionList does not call api.getProjects() for project code resolution"
        )

    def test_fallback_for_unresolved_project(self, source):
        """Unresolved project UUIDs must display '--' as fallback."""
        assert "'--'" in source or '"--"' in source, (
            "ExecutionList has no '--' fallback for unresolved project codes"
        )


# ---------------------------------------------------------------------------
# C3: Sortable Column Headers
# ---------------------------------------------------------------------------
class TestC3SortableHeaders:
    """Clicking column headers must sort rows with a direction indicator."""

    def test_sort_state_exists(self, source):
        """Component must track sort key and direction in state."""
        has_sort_key = bool(re.search(r"sortKey|sortColumn|sortField", source))
        has_sort_dir = bool(
            re.search(r"sortDir|sortDirection|sortOrder|sortAsc", source)
        )
        assert has_sort_key and has_sort_dir, (
            "ExecutionList has no sort state (need sortKey + sortDirection)"
        )

    def test_header_click_handler(self, source):
        """Column headers must have onClick handlers that trigger sorting."""
        # Look for onClick on <th> or a header element that calls a sort function
        has_header_click = bool(
            re.search(r"onClick.*sort|sort.*onClick", source, re.IGNORECASE)
        )
        assert has_header_click, (
            "ExecutionList column headers have no onClick sort handler"
        )

    def test_sort_direction_indicator(self, source):
        """An arrow or triangle indicator must show sort direction."""
        # Look for directional indicators: arrows, triangles, or asc/desc symbols
        has_indicator = bool(
            re.search(
                r"\\u25B2|\\u25BC|\\u2191|\\u2193|\u25B2|\u25BC|\u2191|\u2193|sortDir|sortAsc|arrow|Arrow|chevron|Chevron",
                source,
            )
        )
        assert has_indicator, (
            "ExecutionList has no sort direction indicator (arrow/triangle)"
        )


# ---------------------------------------------------------------------------
# C4: Document Type Filter
# ---------------------------------------------------------------------------
class TestC4DocumentTypeFilter:
    """A filter control must exist for Workflow/Document Type."""

    def test_document_type_filter_exists(self, source):
        """A filter for document type or workflow type must be present."""
        # Look for a select/dropdown that filters by documentType or document_type
        has_doc_filter = bool(
            re.search(
                r"documentType|document_type|docTypeFilter|typeFilter|workflowFilter",
                source,
                re.IGNORECASE,
            )
        )
        assert has_doc_filter, (
            "ExecutionList has no document type / workflow filter control"
        )

    def test_filter_has_all_option(self, source):
        """Filter must have an 'All' option to clear the filter."""
        # The existing sourceFilter already has 'All'; we need a doc-type one
        # Count how many filter selects with 'all' option exist
        all_options = re.findall(r'value=["\']all["\']', source, re.IGNORECASE)
        # Need at least 3: status filter, source filter, and doc-type filter
        assert len(all_options) >= 3, (
            f"Expected at least 3 filter 'all' options (status, source, doc-type), "
            f"found {len(all_options)}"
        )


# ---------------------------------------------------------------------------
# C5: Search Input
# ---------------------------------------------------------------------------
class TestC5SearchInput:
    """A search input must filter by project code or execution ID."""

    def test_search_input_exists(self, source):
        """Component must have a text input for search."""
        has_search = bool(
            re.search(
                r'type=["\']text["\'].*search|search.*<input|searchQuery|searchTerm',
                source,
                re.IGNORECASE,
            )
        )
        assert has_search, (
            "ExecutionList has no search text input"
        )

    def test_search_filters_by_id_and_project(self, source):
        """Search logic must match against both execution ID and project code."""
        # Look for filter logic that checks both id and project code
        # Component may use e.id, exec.id, or item.id — and projectCode or project
        has_id_match = bool(
            re.search(r"\.id\??\.(toLowerCase|includes)|matchesId", source, re.IGNORECASE)
        )
        has_project_match = bool(
            re.search(r"project.*\.(toLowerCase|includes)|matchesProject", source, re.IGNORECASE)
        )
        assert has_id_match and has_project_match, (
            "Search must filter by both execution ID and project code"
        )

    def test_empty_state_message(self, source):
        """When search matches nothing, an empty-state message must appear."""
        # Look for a "no results" / "no executions" / "no matches" message
        # that's conditional on filtered results being empty
        has_empty_state = bool(
            re.search(
                r"No executions|No results|No matches|nothing found",
                source,
                re.IGNORECASE,
            )
        )
        assert has_empty_state, (
            "ExecutionList has no empty-state message for zero search results"
        )
