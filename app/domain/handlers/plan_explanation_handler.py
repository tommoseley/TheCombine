"""
Plan Explanation Document Handler

Handles plan_explanation documents — LLM-generated explanations of
mechanically derived execution plans. The LLM explains, never computes.

WS-BCP-003.
"""

from typing import Dict, Any, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler


class PlanExplanationHandler(BaseDocumentHandler):
    """
    Handler for plan_explanation document type.

    Renders the holistic explanation and per-wave summaries.
    """

    @property
    def doc_type_id(self) -> str:
        return "plan_explanation"

    def extract_title(self, data: Dict[str, Any], fallback: str = "Untitled") -> str:
        wave_count = len(data.get("wave_summaries", []))
        return f"Plan Explanation ({wave_count} waves)"

    def render(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        explanation = self._escape(data.get("explanation", ""))
        wave_summaries = data.get("wave_summaries", [])
        backlog_hash = self._escape(data.get("backlog_hash", ""))

        waves_html = ""
        for ws in wave_summaries:
            num = ws.get("wave_number", "?")
            summary = self._escape(ws.get("summary", ""))
            waves_html += f"""
            <div class="flex gap-2 mb-2">
                <span class="flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded bg-indigo-100 text-indigo-800">Wave {num}</span>
                <span class="text-sm">{summary}</span>
            </div>
            """

        return f"""
        <div class="space-y-4">
            <div>
                <h4 class="text-sm font-medium mb-2">Ordering Rationale</h4>
                <p class="text-sm whitespace-pre-wrap">{explanation}</p>
            </div>
            <div>
                <h4 class="text-sm font-medium mb-2">Wave Summaries</h4>
                {waves_html}
            </div>
            <div class="text-xs text-gray-400 font-mono">
                Explains plan: {backlog_hash}
            </div>
        </div>
        """

    def render_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        explanation = data.get("explanation", "")
        # First sentence
        first_sentence = explanation.split(". ")[0] if explanation else "Plan explanation"
        if not first_sentence.endswith("."):
            first_sentence += "."
        wave_count = len(data.get("wave_summaries", []))
        return f"{first_sentence} ({wave_count} waves)"
