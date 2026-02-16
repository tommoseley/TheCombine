"""
Execution Plan Document Handler

Handles execution_plan documents — deterministically derived,
never LLM-authored. Renders ordered backlog and wave grouping.

WS-BCP-002.
"""

from typing import Dict, Any, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler


class ExecutionPlanHandler(BaseDocumentHandler):
    """
    Handler for execution_plan document type.

    ExecutionPlans are mechanically derived — no parse/validate/transform needed.
    This handler provides rendering only.
    """

    @property
    def doc_type_id(self) -> str:
        return "execution_plan"

    def extract_title(self, data: Dict[str, Any], fallback: str = "Untitled") -> str:
        ordered = data.get("ordered_backlog_ids", [])
        waves = data.get("waves", [])
        return f"Execution Plan: {len(ordered)} items, {len(waves)} waves"

    def render(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        ordered = data.get("ordered_backlog_ids", [])
        waves = data.get("waves", [])
        backlog_hash = self._escape(data.get("backlog_hash", ""))
        version = self._escape(data.get("generator_version", ""))

        # Render waves
        waves_html = ""
        for i, wave in enumerate(waves):
            items_html = ", ".join(self._escape(item_id) for item_id in wave)
            waves_html += f"""
            <div class="mb-2">
                <span class="text-xs font-medium text-gray-500">Wave {i + 1}</span>
                <span class="ml-2 text-sm font-mono">{items_html}</span>
            </div>
            """

        # Render total order
        order_html = " &rarr; ".join(
            f'<span class="font-mono text-sm">{self._escape(item_id)}</span>'
            for item_id in ordered
        )

        return f"""
        <div class="space-y-4">
            <div class="flex gap-4 text-sm text-gray-500">
                <span>Items: <strong>{len(ordered)}</strong></span>
                <span>Waves: <strong>{len(waves)}</strong></span>
                <span>Version: <strong>{version}</strong></span>
            </div>
            <div>
                <h4 class="text-sm font-medium mb-2">Wave Grouping</h4>
                {waves_html}
            </div>
            <div>
                <h4 class="text-sm font-medium mb-2">Total Order (Authoritative)</h4>
                <div class="text-sm">{order_html}</div>
            </div>
            <div class="text-xs text-gray-400 font-mono">
                Hash: {backlog_hash}
            </div>
        </div>
        """

    def render_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        ordered = data.get("ordered_backlog_ids", [])
        waves = data.get("waves", [])
        return f"Execution Plan: {len(ordered)} items in {len(waves)} waves"
