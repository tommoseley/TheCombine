"""
Project Discovery Handler - Handler for project_discovery document type.

This is the first document in the project lifecycle.
It captures early architectural discovery before PM decomposition.
"""

from typing import Dict, Any, List, Optional, Tuple
import logging

from app.domain.handlers.base_handler import BaseDocumentHandler

logger = logging.getLogger(__name__)


class ProjectDiscoveryHandler(BaseDocumentHandler):
    """
    Handler for Project Discovery documents.
    
    Project Discovery captures:
    - Problem understanding and system shape
    - Blocking questions and unknowns
    - Early decision points
    - Candidate architectural patterns
    - Constraints, assumptions, and risks
    - MVP guardrails
    """
    
    @property
    def doc_type_id(self) -> str:
        return "project_discovery"
    
    # =========================================================================
    # VALIDATION - Custom validation for project discovery
    # =========================================================================
    
    def validate(
        self, 
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate project discovery content.
        
        Required:
        - project_name
        - preliminary_summary (with sub-fields)
        """
        errors = []
        
        # Check project_name
        if "project_name" not in data or not data["project_name"]:
            errors.append("Missing required field: 'project_name'")
        
        # Check preliminary_summary
        if "preliminary_summary" not in data:
            errors.append("Missing required field: 'preliminary_summary'")
        elif isinstance(data["preliminary_summary"], dict):
            summary = data["preliminary_summary"]
            for field in ["problem_understanding", "proposed_system_shape", "architectural_intent"]:
                if field not in summary or not summary[field]:
                    errors.append(f"Missing required summary field: '{field}'")
        elif isinstance(data["preliminary_summary"], str):
            # Allow string summary as fallback
            if not data["preliminary_summary"].strip():
                errors.append("'preliminary_summary' cannot be empty")
        else:
            errors.append("'preliminary_summary' must be an object or string")
        
        return len(errors) == 0, errors
    
    # =========================================================================
    # TRANSFORMATION - Normalize and enrich
    # =========================================================================
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform project discovery data.
        
        - Ensure arrays exist (even if empty)
        - Normalize string fields
        """
        # Ensure all array fields exist
        array_fields = [
            "unknowns",
            "stakeholder_questions", 
            "early_decision_points",
            "candidate_architectural_patterns",
            "known_constraints",
            "assumptions",
            "identified_risks",
            "mvp_guardrails",
            "next_steps",
        ]
        
        for field in array_fields:
            if field not in data:
                data[field] = []
        
        # Ensure preliminary_summary is structured
        if "preliminary_summary" in data and isinstance(data["preliminary_summary"], str):
            data["preliminary_summary"] = {
                "problem_understanding": data["preliminary_summary"],
                "proposed_system_shape": "",
                "architectural_intent": "",
            }
        
        return data
    
    # =========================================================================
    # TITLE EXTRACTION
    # =========================================================================
    
    def extract_title(
        self, 
        data: Dict[str, Any],
        fallback: str = "Project Discovery"
    ) -> str:
        """Extract title from project_name."""
        project_name = data.get("project_name", "")
        if project_name:
            return f"Project Discovery: {project_name}"
        return fallback
    
    # =========================================================================
    # RENDERING - Full HTML view
    # =========================================================================
    
    def render(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render full project discovery document.
        
        This produces the complete HTML for the document detail view.
        """
        context = context or {}
        project_name = data.get("project_name", "Project")
        summary = data.get("preliminary_summary", {})
        
        html_parts = []
        
        # Header
        html_parts.append(f'''
        <div class="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center">
                    <i data-lucide="search" class="w-6 h-6 mr-3 text-blue-600"></i>
                    <h2 class="text-2xl font-bold text-gray-900">Project Discovery</h2>
                </div>
            </div>
        ''')
        
        # Project Name & Summary
        html_parts.append(f'''
            <div class="mb-8">
                <h3 class="text-lg font-semibold text-gray-900 mb-3">{self._escape(project_name)}</h3>
        ''')
        
        if isinstance(summary, dict):
            html_parts.append('''
                <div class="bg-blue-50 rounded-lg p-4 space-y-3">
            ''')
            if summary.get("problem_understanding"):
                html_parts.append(f'''
                    <div>
                        <span class="text-sm font-medium text-blue-800">Problem Understanding:</span>
                        <p class="text-blue-900">{self._escape(summary["problem_understanding"])}</p>
                    </div>
                ''')
            if summary.get("proposed_system_shape"):
                html_parts.append(f'''
                    <div>
                        <span class="text-sm font-medium text-blue-800">Proposed System Shape:</span>
                        <p class="text-blue-900">{self._escape(summary["proposed_system_shape"])}</p>
                    </div>
                ''')
            if summary.get("architectural_intent"):
                html_parts.append(f'''
                    <div>
                        <span class="text-sm font-medium text-blue-800">Architectural Intent:</span>
                        <p class="text-blue-900">{self._escape(summary["architectural_intent"])}</p>
                    </div>
                ''')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        
        # Blocking Questions
        questions = data.get("stakeholder_questions", [])
        blocking = [q for q in questions if q.get("blocking")]
        if blocking:
            html_parts.append(self._render_blocking_questions(blocking))
        
        # Unknowns
        unknowns = data.get("unknowns", [])
        if unknowns:
            html_parts.append(self._render_unknowns(unknowns))
        
        # Early Decision Points
        decisions = data.get("early_decision_points", [])
        if decisions:
            html_parts.append(self._render_decisions(decisions))
        
        # Candidate Patterns
        patterns = data.get("candidate_architectural_patterns", [])
        if patterns:
            html_parts.append(self._render_patterns(patterns))
        
        # Two column: Constraints & Assumptions
        constraints = data.get("known_constraints", [])
        assumptions = data.get("assumptions", [])
        if constraints or assumptions:
            html_parts.append(self._render_constraints_assumptions(constraints, assumptions))
        
        # Risks
        risks = data.get("identified_risks", [])
        if risks:
            html_parts.append(self._render_risks(risks))
        
        # MVP Guardrails
        guardrails = data.get("mvp_guardrails", [])
        if guardrails:
            html_parts.append(self._render_guardrails(guardrails))
        
        # Next Steps
        next_steps = data.get("next_steps", [])
        if next_steps:
            html_parts.append(self._render_next_steps(next_steps))
        
        # Close container
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    # =========================================================================
    # RENDERING - Summary view
    # =========================================================================
    
    def render_summary(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render summary card for project discovery.
        
        Shows:
        - Project name
        - Problem understanding (truncated)
        - Counts of blocking items
        """
        project_name = data.get("project_name", "Project")
        summary = data.get("preliminary_summary", {})
        
        # Get problem understanding
        if isinstance(summary, dict):
            problem = summary.get("problem_understanding", "")
        else:
            problem = str(summary)
        
        # Truncate if too long
        if len(problem) > 150:
            problem = problem[:147] + "..."
        
        # Count blocking items
        questions = data.get("stakeholder_questions", [])
        blocking_count = len([q for q in questions if q.get("blocking")])
        unknowns_count = len(data.get("unknowns", []))
        
        html = f'''
        <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between mb-2">
                <div class="flex items-center">
                    <i data-lucide="search" class="w-5 h-5 mr-2 text-blue-600"></i>
                    <h3 class="font-semibold text-gray-900">{self._escape(project_name)}</h3>
                </div>
            </div>
            <p class="text-sm text-gray-600 mb-3">{self._escape(problem)}</p>
            <div class="flex items-center space-x-4 text-xs text-gray-500">
        '''
        
        if blocking_count > 0:
            html += f'''
                <span class="flex items-center text-red-600">
                    <i data-lucide="alert-circle" class="w-3 h-3 mr-1"></i>
                    {blocking_count} blocking
                </span>
            '''
        
        if unknowns_count > 0:
            html += f'''
                <span class="flex items-center text-amber-600">
                    <i data-lucide="help-circle" class="w-3 h-3 mr-1"></i>
                    {unknowns_count} unknowns
                </span>
            '''
        
        html += '''
            </div>
        </div>
        '''
        
        return html
    
    # =========================================================================
    # PRIVATE RENDER HELPERS
    # =========================================================================
    
    def _escape(self, text: Any) -> str:
        """HTML escape a string."""
        if text is None:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    def _render_blocking_questions(self, questions: List[Dict]) -> str:
        """Render blocking questions section."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="alert-circle" class="w-5 h-5 mr-2 text-red-500"></i>
                Blocking Questions
            </h3>
            <div class="space-y-3">
        '''
        
        for q in questions:
            directed_to = q.get("directed_to", "").replace("_", " ").title()
            html += f'''
                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div class="flex items-start justify-between">
                        <p class="font-medium text-red-900">{self._escape(q.get("question", ""))}</p>
                        <span class="ml-2 px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded">{directed_to}</span>
                    </div>
            '''
            if q.get("notes"):
                html += f'<p class="text-sm text-red-700 mt-2">{self._escape(q["notes"])}</p>'
            html += '</div>'
        
        html += '</div></div>'
        return html
    
    def _render_unknowns(self, unknowns: List[Dict]) -> str:
        """Render unknowns section."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="help-circle" class="w-5 h-5 mr-2 text-amber-500"></i>
                Unknowns to Resolve
            </h3>
            <div class="space-y-3">
        '''
        
        for unknown in unknowns:
            html += f'''
                <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <p class="font-medium text-amber-900">{self._escape(unknown.get("question", ""))}</p>
                    <p class="text-sm text-amber-700 mt-1"><strong>Why it matters:</strong> {self._escape(unknown.get("why_it_matters", ""))}</p>
                    <p class="text-sm text-amber-700"><strong>Impact if unresolved:</strong> {self._escape(unknown.get("impact_if_unresolved", ""))}</p>
                </div>
            '''
        
        html += '</div></div>'
        return html
    
    def _render_decisions(self, decisions: List[Dict]) -> str:
        """Render early decision points."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="git-pull-request" class="w-5 h-5 mr-2 text-purple-500"></i>
                Early Decision Points
            </h3>
            <div class="space-y-4">
        '''
        
        for decision in decisions:
            html += f'''
                <div class="border border-gray-200 rounded-lg p-4">
                    <p class="font-semibold text-gray-900 mb-2">{self._escape(decision.get("decision", ""))}</p>
            '''
            
            options = decision.get("options", [])
            if options:
                html += '''
                    <div class="mb-3">
                        <span class="text-sm font-medium text-gray-600">Options:</span>
                        <ul class="mt-1 space-y-1">
                '''
                for option in options:
                    html += f'''
                        <li class="text-sm text-gray-700 flex items-center">
                            <span class="w-1.5 h-1.5 bg-gray-400 rounded-full mr-2"></span>
                            {self._escape(option)}
                        </li>
                    '''
                html += '</ul></div>'
            
            if decision.get("recommendation_direction"):
                html += f'''
                    <div class="bg-purple-50 rounded p-3">
                        <span class="text-sm font-medium text-purple-800">Recommendation:</span>
                        <p class="text-sm text-purple-900">{self._escape(decision["recommendation_direction"])}</p>
                    </div>
                '''
            
            html += '</div>'
        
        html += '</div></div>'
        return html
    
    def _render_patterns(self, patterns: List[Dict]) -> str:
        """Render candidate architectural patterns."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="layers" class="w-5 h-5 mr-2 text-indigo-500"></i>
                Candidate Patterns
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        '''
        
        for pattern in patterns:
            html += f'''
                <div class="border border-gray-200 rounded-lg p-4">
                    <p class="font-semibold text-gray-900 mb-2">{self._escape(pattern.get("pattern", ""))}</p>
                    <p class="text-sm text-gray-600 mb-2">{self._escape(pattern.get("applicability", ""))}</p>
            '''
            
            risks = pattern.get("risks", [])
            if risks:
                html += '''
                    <div class="mt-2">
                        <span class="text-xs font-medium text-gray-500 uppercase">Risks:</span>
                        <ul class="mt-1">
                '''
                for risk in risks:
                    html += f'''
                        <li class="text-sm text-red-600 flex items-center">
                            <i data-lucide="alert-triangle" class="w-3 h-3 mr-1"></i>
                            {self._escape(risk)}
                        </li>
                    '''
                html += '</ul></div>'
            
            html += '</div>'
        
        html += '</div></div>'
        return html
    
    def _render_constraints_assumptions(
        self, 
        constraints: List[str], 
        assumptions: List[str]
    ) -> str:
        """Render constraints and assumptions in two columns."""
        html = '<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">'
        
        if constraints:
            html += '''
                <div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                        <i data-lucide="lock" class="w-5 h-5 mr-2 text-gray-500"></i>
                        Known Constraints
                    </h3>
                    <ul class="space-y-2">
            '''
            for constraint in constraints:
                html += f'''
                    <li class="flex items-start text-sm text-gray-700">
                        <span class="w-1.5 h-1.5 bg-gray-400 rounded-full mr-2 mt-1.5 flex-shrink-0"></span>
                        {self._escape(constraint)}
                    </li>
                '''
            html += '</ul></div>'
        
        if assumptions:
            html += '''
                <div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                        <i data-lucide="lightbulb" class="w-5 h-5 mr-2 text-yellow-500"></i>
                        Assumptions
                    </h3>
                    <ul class="space-y-2">
            '''
            for assumption in assumptions:
                html += f'''
                    <li class="flex items-start text-sm text-gray-700">
                        <span class="w-1.5 h-1.5 bg-yellow-400 rounded-full mr-2 mt-1.5 flex-shrink-0"></span>
                        {self._escape(assumption)}
                    </li>
                '''
            html += '</ul></div>'
        
        html += '</div>'
        return html
    
    def _render_risks(self, risks: List[Dict]) -> str:
        """Render identified risks."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="shield-alert" class="w-5 h-5 mr-2 text-red-500"></i>
                Identified Risks
            </h3>
            <div class="space-y-3">
        '''
        
        for risk in risks:
            likelihood = risk.get("likelihood", "medium")
            
            if likelihood == "high":
                border_class = "border-red-400 bg-red-50"
                badge_class = "bg-red-100 text-red-700"
            elif likelihood == "medium":
                border_class = "border-amber-400 bg-amber-50"
                badge_class = "bg-amber-100 text-amber-700"
            else:
                border_class = "border-gray-300 bg-gray-50"
                badge_class = "bg-gray-100 text-gray-700"
            
            html += f'''
                <div class="border-l-4 {border_class} p-4 rounded-r-lg">
                    <div class="flex items-center justify-between mb-1">
                        <p class="font-medium text-gray-900">{self._escape(risk.get("description", ""))}</p>
                        <span class="px-2 py-0.5 text-xs font-medium rounded {badge_class}">
                            {likelihood.title()}
                        </span>
                    </div>
                    <p class="text-sm text-gray-600">{self._escape(risk.get("impact", ""))}</p>
                </div>
            '''
        
        html += '</div></div>'
        return html
    
    def _render_guardrails(self, guardrails: List) -> str:
        """Render MVP guardrails."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="shield" class="w-5 h-5 mr-2 text-green-500"></i>
                MVP Guardrails
            </h3>
            <div class="space-y-3">
        '''
        
        for guardrail in guardrails:
            # Handle both string and dict formats
            if isinstance(guardrail, str):
                html += f'''
                <div class="border border-green-200 bg-green-50 rounded-lg p-4">
                    <p class="font-medium text-green-900">{self._escape(guardrail)}</p>
                </div>
                '''
            else:
                scope = guardrail.get("scope", "")
                html += f'''
                <div class="border border-green-200 bg-green-50 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-1">
                        <p class="font-medium text-green-900">{self._escape(guardrail.get("guardrail", ""))}</p>
                        <span class="px-2 py-0.5 text-xs font-medium rounded bg-green-100 text-green-700">
                            {self._escape(scope)}
                        </span>
                    </div>
                    <p class="text-sm text-green-700">{self._escape(guardrail.get("rationale", ""))}</p>
                </div>
                '''
        
        html += '</div></div>'
        return html
    
    def _render_next_steps(self, next_steps: List[Dict]) -> str:
        """Render next steps."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="arrow-right-circle" class="w-5 h-5 mr-2 text-blue-500"></i>
                Next Steps
            </h3>
            <div class="space-y-2">
        '''
        
        for step in next_steps:
            owner = step.get("owner", "")
            html += f'''
                <div class="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                    <span class="text-gray-900">{self._escape(step.get("action", ""))}</span>
                    <span class="text-sm text-gray-500">{self._escape(owner)}</span>
                </div>
            '''
        
        html += '</div></div>'
        return html