"""
Intent Packet Document Handler

Handles intent_packet documents — raw user intent persisted by mechanical intake.
No LLM involvement. No child documents. Minimal handler.
"""

from typing import Dict, Any, Optional
from app.domain.handlers.base_handler import BaseDocumentHandler


class IntentPacketHandler(BaseDocumentHandler):
    """
    Handler for intent_packet document type.

    IntentPackets are created by mechanical intake (POST /api/v1/intents),
    not by LLM generation. This handler provides rendering only.
    """

    @property
    def doc_type_id(self) -> str:
        return "intent_packet"

    def extract_title(self, data: Dict[str, Any], fallback: str = "Untitled") -> str:
        raw = data.get("raw_intent", "")
        if raw:
            return f"Intent: {raw[:80]}"
        return fallback

    def render(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        raw = self._escape(data.get("raw_intent", ""))
        constraints = self._escape(data.get("constraints") or "None")
        criteria = self._escape(data.get("success_criteria") or "None")
        ctx = self._escape(data.get("context") or "None")

        return f"""
        <div class="space-y-4">
            <div>
                <h3 class="font-semibold text-sm text-gray-500">Raw Intent</h3>
                <p class="mt-1 whitespace-pre-wrap">{raw}</p>
            </div>
            <div>
                <h3 class="font-semibold text-sm text-gray-500">Constraints</h3>
                <p class="mt-1 whitespace-pre-wrap">{constraints}</p>
            </div>
            <div>
                <h3 class="font-semibold text-sm text-gray-500">Success Criteria</h3>
                <p class="mt-1 whitespace-pre-wrap">{criteria}</p>
            </div>
            <div>
                <h3 class="font-semibold text-sm text-gray-500">Context</h3>
                <p class="mt-1 whitespace-pre-wrap">{ctx}</p>
            </div>
        </div>
        """

    def render_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        raw = self._escape(data.get("raw_intent", ""))
        truncated = raw[:120] + "..." if len(raw) > 120 else raw
        return f"Intent: {truncated}"
