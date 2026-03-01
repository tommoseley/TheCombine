"""
Pipeline Run Document Handler

Handles pipeline_run documents — metadata records for BCP pipeline runs.
Renders run status, stage results, and replay metadata.

WS-BCP-004.
"""

from typing import Any, Dict, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def _html_escape(text: Any) -> str:
    """HTML escape a string."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def status_color(status: str) -> str:
    """Derive CSS color name from pipeline status.

    Pure function — no I/O, no side effects.
    """
    return "emerald" if status == "completed" else "red"


def stage_color(stage_status: str) -> str:
    """Derive CSS color name from stage status.

    Pure function — no I/O, no side effects.
    """
    if stage_status == "completed":
        return "emerald"
    elif stage_status == "failed":
        return "red"
    return "gray"


def render_stages_html(stages: Dict[str, dict]) -> str:
    """Render HTML for pipeline stages.

    Pure function — no I/O, no side effects.

    Args:
        stages: Dict of stage_name -> stage_data

    Returns:
        HTML string for stages section
    """
    html = ""
    for name, stage_data in stages.items():
        s_status = stage_data.get("status", "unknown")
        s_color = stage_color(s_status)
        error_html = (
            f'<span class="text-red-500 text-xs ml-2">'
            f'{_html_escape(stage_data.get("error", ""))}</span>'
            if stage_data.get("error") else ""
        )
        html += f"""
            <div class="flex items-center gap-2 mb-1">
                <span class="w-2 h-2 rounded-full bg-{s_color}-500"></span>
                <span class="text-sm font-medium">{_html_escape(name)}</span>
                <span class="text-xs text-gray-500">{s_status}</span>
                {error_html}
            </div>
            """
    return html


def render_replay_html(replay: Dict[str, Any]) -> str:
    """Render HTML for replay metadata.

    Pure function — no I/O, no side effects.
    """
    html = ""
    for key, value in replay.items():
        if value:
            display = _html_escape(str(value))
            if len(display) > 16:
                display = display[:12] + "..."
            html += f'<span class="text-xs font-mono">{_html_escape(key)}: {display}</span><br/>'
    return html


def render_errors_html(errors: Optional[dict]) -> str:
    """Render HTML for error summaries.

    Pure function — no I/O, no side effects.
    """
    if not errors:
        return ""

    html = ""
    dep_errors = errors.get("dependency_errors", [])
    hier_errors = errors.get("hierarchy_errors", [])
    cycle_traces = errors.get("cycle_traces", [])
    if dep_errors:
        html += f'<div class="text-sm text-red-600">Dependency errors: {len(dep_errors)}</div>'
    if hier_errors:
        html += f'<div class="text-sm text-red-600">Hierarchy errors: {len(hier_errors)}</div>'
    if cycle_traces:
        html += f'<div class="text-sm text-red-600">Cycles detected: {len(cycle_traces)}</div>'
    return html


class PipelineRunHandler(BaseDocumentHandler):
    """
    Handler for pipeline_run document type.

    Renders pipeline run metadata including stages and replay hashes.
    """

    @property
    def doc_type_id(self) -> str:
        return "pipeline_run"

    def extract_title(self, data: Dict[str, Any], fallback: str = "Untitled") -> str:
        run_id = data.get("run_id", "unknown")
        status = data.get("status", "unknown")
        return f"Pipeline Run {run_id} ({status})"

    def render(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        run_id = _html_escape(data.get("run_id", ""))
        run_status = data.get("status", "unknown")
        stage_reached = _html_escape(data.get("stage_reached", ""))

        sc = status_color(run_status)
        stages_html = render_stages_html(data.get("stages", {}))
        replay_html = render_replay_html(data.get("replay_metadata", {}))
        errors_html = render_errors_html(data.get("errors"))

        return f"""
        <div class="space-y-4">
            <div class="flex items-center gap-3">
                <span class="px-2 py-0.5 text-xs font-medium rounded bg-{sc}-100 text-{sc}-800">{run_status}</span>
                <span class="font-mono text-sm">{run_id}</span>
                <span class="text-xs text-gray-500">Stage: {stage_reached}</span>
            </div>
            <div>
                <h4 class="text-sm font-medium mb-2">Stages</h4>
                {stages_html}
            </div>
            {f'<div><h4 class="text-sm font-medium mb-1">Errors</h4>{errors_html}</div>' if errors_html else ''}
            <div>
                <h4 class="text-sm font-medium mb-1">Replay Metadata</h4>
                {replay_html}
            </div>
        </div>
        """

    def render_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        run_id = data.get("run_id", "unknown")
        status = data.get("status", "unknown")
        stage = data.get("stage_reached", "")
        return f"Run {run_id}: {status} (stage: {stage})"
