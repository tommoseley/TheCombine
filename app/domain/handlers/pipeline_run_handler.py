"""
Pipeline Run Document Handler

Handles pipeline_run documents — metadata records for BCP pipeline runs.
Renders run status, stage results, and replay metadata.

WS-BCP-004.
"""

from typing import Dict, Any, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler


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
        run_id = self._escape(data.get("run_id", ""))
        status = data.get("status", "unknown")
        stage_reached = self._escape(data.get("stage_reached", ""))
        stages = data.get("stages", {})
        replay = data.get("replay_metadata", {})
        errors = data.get("errors")

        status_color = "emerald" if status == "completed" else "red"

        # Render stages
        stages_html = ""
        for name, stage in stages.items():
            s_status = stage.get("status", "unknown")
            s_color = "emerald" if s_status == "completed" else ("red" if s_status == "failed" else "gray")
            error_html = f'<span class="text-red-500 text-xs ml-2">{self._escape(stage.get("error", ""))}</span>' if stage.get("error") else ""
            stages_html += f"""
            <div class="flex items-center gap-2 mb-1">
                <span class="w-2 h-2 rounded-full bg-{s_color}-500"></span>
                <span class="text-sm font-medium">{self._escape(name)}</span>
                <span class="text-xs text-gray-500">{s_status}</span>
                {error_html}
            </div>
            """

        # Render replay metadata
        replay_html = ""
        for key, value in replay.items():
            if value:
                display = self._escape(str(value))
                if len(display) > 16:
                    display = display[:12] + "..."
                replay_html += f'<span class="text-xs font-mono">{self._escape(key)}: {display}</span><br/>'

        # Render errors
        errors_html = ""
        if errors:
            dep_errors = errors.get("dependency_errors", [])
            hier_errors = errors.get("hierarchy_errors", [])
            cycle_traces = errors.get("cycle_traces", [])
            if dep_errors:
                errors_html += f'<div class="text-sm text-red-600">Dependency errors: {len(dep_errors)}</div>'
            if hier_errors:
                errors_html += f'<div class="text-sm text-red-600">Hierarchy errors: {len(hier_errors)}</div>'
            if cycle_traces:
                errors_html += f'<div class="text-sm text-red-600">Cycles detected: {len(cycle_traces)}</div>'

        return f"""
        <div class="space-y-4">
            <div class="flex items-center gap-3">
                <span class="px-2 py-0.5 text-xs font-medium rounded bg-{status_color}-100 text-{status_color}-800">{status}</span>
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
