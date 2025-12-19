"""
Epic Backlog Handler - Handler for epic_backlog document type.

This document captures the set of epics decomposed from project discovery.
It defines the major work streams for the project.

Canonical Schema:
- epics[]: name, intent, epic_id, in_scope, mvp_phase, dependencies, 
           out_of_scope, business_value, open_questions, primary_outcomes,
           notes_for_architecture, related_discovery_items
- project_name
- risks_overview[]
- epic_set_summary: out_of_scope, mvp_definition, overall_intent, key_constraints
- recommendations_for_architecture[]
"""

from typing import Dict, Any, List, Optional, Tuple
import logging

from app.domain.handlers.base_handler import BaseDocumentHandler

logger = logging.getLogger(__name__)


class EpicBacklogHandler(BaseDocumentHandler):
    """
    Handler for Epic Backlog documents.
    
    Epic Backlog captures:
    - Epics with name, intent, scope, and outcomes
    - MVP phasing (mvp vs later-phase)
    - Dependencies between epics
    - Business value and open questions
    - Links to discovery items (risks, unknowns, decisions)
    - Overall summary and architecture recommendations
    """
    
    @property
    def doc_type_id(self) -> str:
        return "epic_backlog"
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def validate(
        self, 
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate epic backlog content.
        
        Required:
        - epics (array with at least one epic)
        - Each epic must have name and intent
        """
        errors = []
        
        # Check epics array
        if "epics" not in data:
            errors.append("Missing required field: 'epics'")
        elif not isinstance(data["epics"], list):
            errors.append("'epics' must be an array")
        elif len(data["epics"]) == 0:
            errors.append("'epics' array cannot be empty")
        else:
            for i, epic in enumerate(data["epics"]):
                if not isinstance(epic, dict):
                    errors.append(f"Epic {i+1} must be an object")
                    continue
                # Accept name OR title
                if not (epic.get("name") or epic.get("title")):
                    errors.append(f"Epic {i+1} missing required field: 'name'")
        
        return len(errors) == 0, errors
    
    # =========================================================================
    # TRANSFORMATION
    # =========================================================================
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform epic backlog data to canonical format.
        """
        epics = data.get("epics", [])
        
        for i, epic in enumerate(epics):
            # Normalize name (accept title as fallback)
            if not epic.get("name"):
                epic["name"] = epic.get("title", f"Epic {i+1}")
            
            # Generate epic_id if missing
            if not epic.get("epic_id"):
                epic["epic_id"] = f"EPIC-{i+1:03d}"
            
            # Ensure all array fields exist
            for field in ["in_scope", "out_of_scope", "primary_outcomes", 
                         "architecture_attention_points"]:
                if field not in epic:
                    epic[field] = []
            
            # Handle notes_for_architecture -> architecture_attention_points migration
            if "notes_for_architecture" in epic and not epic.get("architecture_attention_points"):
                epic["architecture_attention_points"] = epic.pop("notes_for_architecture")
            
            # Ensure dependencies array exists
            if "dependencies" not in epic:
                epic["dependencies"] = []
            
            # Ensure open_questions is array of objects
            if "open_questions" not in epic:
                epic["open_questions"] = []
            else:
                # Normalize string questions to objects
                normalized = []
                for q in epic["open_questions"]:
                    if isinstance(q, str):
                        normalized.append({
                            "question": q,
                            "blocking_for_epic": False,
                            "directed_to": "product"
                        })
                    else:
                        normalized.append(q)
                epic["open_questions"] = normalized
            
            # Ensure related_discovery_items exists
            if "related_discovery_items" not in epic:
                epic["related_discovery_items"] = {
                    "risks": [],
                    "unknowns": [],
                    "early_decision_points": []
                }
            
            # Default mvp_phase
            if "mvp_phase" not in epic:
                epic["mvp_phase"] = "mvp"
            
            # Default intent and business_value
            if "intent" not in epic:
                epic["intent"] = ""
            if "business_value" not in epic:
                epic["business_value"] = ""
        
        # Ensure top-level fields exist
        if "project_name" not in data:
            data["project_name"] = ""
        if "risks_overview" not in data:
            data["risks_overview"] = []
        if "recommendations_for_architecture" not in data:
            data["recommendations_for_architecture"] = []
        
        # Ensure epic_set_summary exists
        if "epic_set_summary" not in data:
            data["epic_set_summary"] = {
                "overall_intent": "",
                "mvp_definition": "",
                "key_constraints": [],
                "out_of_scope": []
            }
        
        return data
    
    # =========================================================================
    # TITLE EXTRACTION
    # =========================================================================
    
    def extract_title(
        self, 
        data: Dict[str, Any],
        fallback: str = "Epic Backlog"
    ) -> str:
        """Extract title from project_name and epic count."""
        project_name = data.get("project_name", "")
        epics = data.get("epics", [])
        count = len(epics)
        
        if project_name:
            return f"{project_name} - Epic Backlog ({count} epic{'s' if count != 1 else ''})"
        return f"Epic Backlog ({count} epic{'s' if count != 1 else ''})"
    
    # =========================================================================
    # RENDERING
    # =========================================================================
    
    def render(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render full epic backlog document.
        """
        context = context or {}
        epics = data.get("epics", [])
        project_name = data.get("project_name", "Project")
        summary = data.get("epic_set_summary", {})
        risks_overview = data.get("risks_overview", [])
        arch_recommendations = data.get("recommendations_for_architecture", [])
        
        # Count MVP vs later-phase
        mvp_epics = [e for e in epics if e.get("mvp_phase") == "mvp"]
        later_epics = [e for e in epics if e.get("mvp_phase") == "later-phase"]
        
        html_parts = []
        
        # Header
        html_parts.append(f'''
        <div class="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center">
                    <i data-lucide="layers" class="w-6 h-6 mr-3 text-purple-600"></i>
                    <div>
                        <h2 class="text-2xl font-bold text-gray-900">Epic Backlog</h2>
                        <p class="text-gray-500">{self._escape(project_name)}</p>
                    </div>
                </div>
                <div class="flex gap-2">
                    <span class="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                        {len(mvp_epics)} MVP
                    </span>
                    <span class="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
                        {len(later_epics)} Later
                    </span>
                </div>
            </div>
        ''')
        
        # Epic Set Summary
        if summary:
            html_parts.append(self._render_summary(summary))
        
        html_parts.append('</div>')
        
        # MVP Epics
        if mvp_epics:
            html_parts.append('''
            <div class="mb-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <i data-lucide="rocket" class="w-5 h-5 mr-2 text-purple-500"></i>
                    MVP Epics
                </h3>
                <div class="space-y-4">
            ''')
            for epic in mvp_epics:
                html_parts.append(self._render_epic_card(epic))
            html_parts.append('</div></div>')
        
        # Later Phase Epics
        if later_epics:
            html_parts.append('''
            <div class="mb-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <i data-lucide="calendar" class="w-5 h-5 mr-2 text-gray-500"></i>
                    Later Phase Epics
                </h3>
                <div class="space-y-4">
            ''')
            for epic in later_epics:
                html_parts.append(self._render_epic_card(epic, is_later=True))
            html_parts.append('</div></div>')
        
        # Risks Overview
        if risks_overview:
            html_parts.append(self._render_risks_overview(risks_overview))
        
        # Architecture Recommendations
        if arch_recommendations:
            html_parts.append(self._render_arch_recommendations(arch_recommendations))
        
        return '\n'.join(html_parts)
    
    def _render_summary(self, summary: Dict[str, Any]) -> str:
        """Render epic set summary."""
        html = '<div class="space-y-4">'
        
        if summary.get("overall_intent"):
            html += f'''
            <div class="p-4 bg-purple-50 rounded-lg">
                <h4 class="text-sm font-medium text-purple-800 uppercase mb-2">Overall Intent</h4>
                <p class="text-purple-900">{self._escape(summary["overall_intent"])}</p>
            </div>
            '''
        
        if summary.get("mvp_definition"):
            html += f'''
            <div class="p-4 bg-blue-50 rounded-lg">
                <h4 class="text-sm font-medium text-blue-800 uppercase mb-2">MVP Definition</h4>
                <p class="text-blue-900">{self._escape(summary["mvp_definition"])}</p>
            </div>
            '''
        
        if summary.get("key_constraints"):
            html += '''
            <div class="p-4 bg-amber-50 rounded-lg">
                <h4 class="text-sm font-medium text-amber-800 uppercase mb-2">Key Constraints</h4>
                <ul class="space-y-1">
            '''
            for constraint in summary["key_constraints"]:
                html += f'<li class="text-amber-900 text-sm">• {self._escape(constraint)}</li>'
            html += '</ul></div>'
        
        if summary.get("out_of_scope"):
            html += '''
            <div class="p-4 bg-gray-50 rounded-lg">
                <h4 class="text-sm font-medium text-gray-600 uppercase mb-2">Out of Scope</h4>
                <ul class="space-y-1">
            '''
            for item in summary["out_of_scope"]:
                html += f'<li class="text-gray-700 text-sm">• {self._escape(item)}</li>'
            html += '</ul></div>'
        
        html += '</div>'
        return html
    
    def _render_epic_card(self, epic: Dict[str, Any], is_later: bool = False) -> str:
        """Render a single epic card."""
        epic_id = epic.get("epic_id", "")
        name = epic.get("name", "Untitled Epic")
        intent = epic.get("intent", "")
        business_value = epic.get("business_value", "")
        in_scope = epic.get("in_scope", [])
        out_of_scope = epic.get("out_of_scope", [])
        primary_outcomes = epic.get("primary_outcomes", [])
        open_questions = epic.get("open_questions", [])
        dependencies = epic.get("dependencies", [])
        arch_attention = epic.get("architecture_attention_points", [])
        related = epic.get("related_discovery_items", {})
        
        border_class = "border-gray-200" if is_later else "border-purple-200"
        
        html = f'''
        <div class="bg-white rounded-lg border {border_class} p-6 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between mb-4">
                <div class="flex-1">
                    <div class="flex items-center mb-2">
                        <span class="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-mono mr-3">
                            {self._escape(epic_id)}
                        </span>
                        <h3 class="text-lg font-semibold text-gray-900">{self._escape(name)}</h3>
                    </div>
                    <p class="text-gray-600">{self._escape(intent)}</p>
                </div>
            </div>
        '''
        
        # Business Value
        if business_value:
            html += f'''
            <div class="mb-4 p-3 bg-green-50 rounded-lg">
                <span class="text-sm font-medium text-green-800">Business Value:</span>
                <p class="text-green-900 text-sm">{self._escape(business_value)}</p>
            </div>
            '''
        
        # In Scope / Out of Scope columns
        if in_scope or out_of_scope:
            html += '<div class="grid grid-cols-2 gap-4 mb-4">'
            
            if in_scope:
                html += '''
                <div>
                    <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">In Scope</h4>
                    <ul class="space-y-1">
                '''
                for item in in_scope:
                    html += f'''
                        <li class="flex items-start text-sm text-gray-700">
                            <i data-lucide="check" class="w-4 h-4 mr-2 text-green-500 flex-shrink-0 mt-0.5"></i>
                            {self._escape(item)}
                        </li>
                    '''
                html += '</ul></div>'
            
            if out_of_scope:
                html += '''
                <div>
                    <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">Out of Scope</h4>
                    <ul class="space-y-1">
                '''
                for item in out_of_scope:
                    html += f'''
                        <li class="flex items-start text-sm text-gray-500">
                            <i data-lucide="x" class="w-4 h-4 mr-2 text-gray-400 flex-shrink-0 mt-0.5"></i>
                            {self._escape(item)}
                        </li>
                    '''
                html += '</ul></div>'
            
            html += '</div>'
        
        # Primary Outcomes
        if primary_outcomes:
            html += '''
            <div class="mb-4">
                <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">Primary Outcomes</h4>
                <ul class="space-y-1">
            '''
            for outcome in primary_outcomes:
                html += f'''
                    <li class="flex items-start text-sm text-gray-700">
                        <i data-lucide="target" class="w-4 h-4 mr-2 text-blue-500 flex-shrink-0 mt-0.5"></i>
                        {self._escape(outcome)}
                    </li>
                '''
            html += '</ul></div>'
        
        # Open Questions (now structured objects)
        if open_questions:
            blocking = [q for q in open_questions if q.get("blocking_for_epic")]
            non_blocking = [q for q in open_questions if not q.get("blocking_for_epic")]
            
            html += '''
            <div class="mb-4 p-3 bg-amber-50 rounded-lg">
                <h4 class="text-sm font-medium text-amber-800 uppercase mb-2">Open Questions</h4>
                <div class="space-y-2">
            '''
            
            # Show blocking questions first
            for q in blocking:
                question = q.get("question", "") if isinstance(q, dict) else str(q)
                directed_to = q.get("directed_to", "") if isinstance(q, dict) else ""
                html += f'''
                    <div class="flex items-start">
                        <i data-lucide="alert-circle" class="w-4 h-4 mr-2 text-red-500 flex-shrink-0 mt-0.5"></i>
                        <div class="flex-1">
                            <span class="text-amber-900 text-sm">{self._escape(question)}</span>
                            <span class="ml-2 px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">Blocking</span>
                            {f'<span class="ml-1 text-xs text-gray-500">→ {self._escape(directed_to)}</span>' if directed_to else ''}
                        </div>
                    </div>
                '''
            
            for q in non_blocking:
                question = q.get("question", "") if isinstance(q, dict) else str(q)
                directed_to = q.get("directed_to", "") if isinstance(q, dict) else ""
                html += f'''
                    <div class="flex items-start">
                        <i data-lucide="help-circle" class="w-4 h-4 mr-2 text-amber-500 flex-shrink-0 mt-0.5"></i>
                        <div class="flex-1">
                            <span class="text-amber-900 text-sm">{self._escape(question)}</span>
                            {f'<span class="ml-2 text-xs text-gray-500">→ {self._escape(directed_to)}</span>' if directed_to else ''}
                        </div>
                    </div>
                '''
            
            html += '</div></div>'
        
        # Dependencies
        if dependencies:
            html += '''
            <div class="mb-4">
                <h4 class="text-sm font-medium text-gray-500 uppercase mb-2">Dependencies</h4>
                <div class="space-y-2">
            '''
            for dep in dependencies:
                dep_id = dep.get("depends_on_epic_id", "") if isinstance(dep, dict) else str(dep)
                reason = dep.get("reason", "") if isinstance(dep, dict) else ""
                html += f'''
                    <div class="flex items-center text-sm">
                        <span class="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-mono mr-2">
                            {self._escape(dep_id)}
                        </span>
                        <span class="text-gray-500">{self._escape(reason)}</span>
                    </div>
                '''
            html += '</div></div>'
        
        # Architecture Attention Points
        if arch_attention:
            html += '''
            <div class="mb-4 p-3 bg-indigo-50 rounded-lg">
                <h4 class="text-sm font-medium text-indigo-800 uppercase mb-2">Architecture Attention Points</h4>
                <ul class="space-y-1">
            '''
            for note in arch_attention:
                html += f'<li class="text-indigo-900 text-sm">• {self._escape(note)}</li>'
            html += '</ul></div>'
        
        # Related Discovery Items
        if related and any([related.get("risks"), related.get("unknowns"), related.get("early_decision_points")]):
            html += '''
            <div class="p-3 bg-gray-50 rounded-lg">
                <h4 class="text-sm font-medium text-gray-600 uppercase mb-2">Related Discovery Items</h4>
                <div class="space-y-2 text-sm">
            '''
            if related.get("risks"):
                html += '<div><span class="text-red-600 font-medium">Risks:</span> '
                html += ', '.join(self._escape(r) for r in related["risks"])
                html += '</div>'
            if related.get("unknowns"):
                html += '<div><span class="text-amber-600 font-medium">Unknowns:</span> '
                html += ', '.join(self._escape(u) for u in related["unknowns"])
                html += '</div>'
            if related.get("early_decision_points"):
                html += '<div><span class="text-purple-600 font-medium">Decisions:</span> '
                html += ', '.join(self._escape(d) for d in related["early_decision_points"])
                html += '</div>'
            html += '</div></div>'
        
        html += '</div>'
        return html
    
    def _render_risks_overview(self, risks: List[Dict]) -> str:
        """Render risks overview section."""
        html = '''
        <div class="bg-white rounded-lg border border-red-200 p-6 mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <i data-lucide="alert-triangle" class="w-5 h-5 mr-2 text-red-500"></i>
                Risks Overview
            </h3>
            <div class="space-y-3">
        '''
        
        for risk in risks:
            affected = risk.get("affected_epics", [])
            html += f'''
            <div class="p-4 bg-red-50 rounded-lg">
                <p class="font-medium text-red-900 mb-1">{self._escape(risk.get("description", ""))}</p>
                <p class="text-sm text-red-700 mb-2">{self._escape(risk.get("impact", ""))}</p>
                <div class="flex flex-wrap gap-1">
            '''
            for epic_id in affected:
                html += f'<span class="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">{self._escape(epic_id)}</span>'
            html += '</div></div>'
        
        html += '</div></div>'
        return html
    
    def _render_arch_recommendations(self, recommendations: List[str]) -> str:
        """Render architecture recommendations."""
        html = '''
        <div class="bg-white rounded-lg border border-indigo-200 p-6 mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <i data-lucide="lightbulb" class="w-5 h-5 mr-2 text-indigo-500"></i>
                Recommendations for Architecture
            </h3>
            <ul class="space-y-2">
        '''
        
        for rec in recommendations:
            html += f'''
            <li class="flex items-start">
                <i data-lucide="arrow-right" class="w-4 h-4 mr-2 text-indigo-500 flex-shrink-0 mt-1"></i>
                <span class="text-gray-700">{self._escape(rec)}</span>
            </li>
            '''
        
        html += '</ul></div>'
        return html
    
    # =========================================================================
    # SUMMARY RENDERING
    # =========================================================================
    
    def render_summary(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render compact summary for cards/lists.
        """
        epics = data.get("epics", [])
        mvp_count = len([e for e in epics if e.get("mvp_phase") == "mvp"])
        later_count = len([e for e in epics if e.get("mvp_phase") == "later-phase"])
        
        # Get first 3 epic names
        names = [e.get("name", "Untitled") for e in epics[:3]]
        
        html = f'''
        <div class="p-4">
            <div class="flex items-center justify-between mb-2">
                <span class="font-medium text-gray-900">Epic Backlog</span>
                <div class="flex gap-1">
                    <span class="text-xs text-purple-600">{mvp_count} MVP</span>
                    <span class="text-xs text-gray-400">•</span>
                    <span class="text-xs text-gray-500">{later_count} Later</span>
                </div>
            </div>
            <ul class="text-sm text-gray-600 space-y-1">
        '''
        
        for name in names:
            html += f'<li class="truncate">• {self._escape(name)}</li>'
        
        if len(epics) > 3:
            html += f'<li class="text-gray-400">... and {len(epics) - 3} more</li>'
        
        html += '</ul></div>'
        return html