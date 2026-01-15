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
    - Problem understanding and architectural intent
    - Blocking questions and unknowns
    - Early decision points
    - Constraints, assumptions, and risks
    - MVP guardrails
    - Recommendations for PM
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
            # Updated required fields - removed proposed_system_shape, added scope_pressure_points
            for field in ["problem_understanding", "architectural_intent"]:
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
            "known_constraints",
            "assumptions",
            "identified_risks",
            "mvp_guardrails",
            "recommendations_for_pm",
        ]
        
        for field in array_fields:
            if field not in data:
                data[field] = []
        
        # Ensure preliminary_summary is structured
        if "preliminary_summary" in data and isinstance(data["preliminary_summary"], str):
            data["preliminary_summary"] = {
                "problem_understanding": data["preliminary_summary"],
                "architectural_intent": "",
                "scope_pressure_points": "",
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
            if summary.get("architectural_intent"):
                html_parts.append(f'''
                    <div>
                        <span class="text-sm font-medium text-blue-800">Architectural Intent:</span>
                        <p class="text-blue-900">{self._escape(summary["architectural_intent"])}</p>
                    </div>
                ''')
            if summary.get("scope_pressure_points"):
                html_parts.append(f'''
                    <div>
                        <span class="text-sm font-medium text-blue-800">Scope Pressure Points:</span>
                        <p class="text-blue-900">{self._escape(summary["scope_pressure_points"])}</p>
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
            html_parts.append(self._render_decision_points(decisions))
        
        # Constraints and Assumptions
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
        
        # Recommendations for PM
        recommendations = data.get("recommendations_for_pm", [])
        if recommendations:
            html_parts.append(self._render_recommendations(recommendations))
        
        # Non-blocking questions
        non_blocking = [q for q in questions if not q.get("blocking")]
        if non_blocking:
            html_parts.append(self._render_non_blocking_questions(non_blocking))
        
        # Close container
        html_parts.append('</div>')
        
        return ''.join(html_parts)
    
    # =========================================================================
    # SUMMARY RENDERING
    # =========================================================================
    
    def render_summary(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render compact project discovery summary for cards/lists.
        """
        project_name = data.get("project_name", "Project")
        summary = data.get("preliminary_summary", {})
        
        # Extract first sentence of problem understanding
        problem = ""
        if isinstance(summary, dict):
            problem = summary.get("problem_understanding", "")[:200]
        elif isinstance(summary, str):
            problem = summary[:200]
        
        unknowns_count = len(data.get("unknowns", []))
        blocking_count = len([q for q in data.get("stakeholder_questions", []) if q.get("blocking")])
        
        html = f'''
        <div class="p-4">
            <div class="flex items-center mb-2">
                <i data-lucide="search" class="w-5 h-5 mr-2 text-blue-600"></i>
                <h3 class="font-semibold text-gray-900">{self._escape(project_name)}</h3>
            </div>
            <p class="text-sm text-gray-600 mb-3">{self._escape(problem)}{'...' if len(problem) == 200 else ''}</p>
            <div class="flex gap-4 text-xs text-gray-500">
                <span>{unknowns_count} unknowns</span>
                <span>{blocking_count} blocking questions</span>
            </div>
        </div>
        '''
        return html
    
    # =========================================================================
    # PRIVATE RENDER HELPERS
    # =========================================================================
    
    def _render_blocking_questions(self, questions: List[Dict]) -> str:
        """Render blocking stakeholder questions."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="alert-circle" class="w-5 h-5 mr-2 text-red-500"></i>
                Blocking Questions
            </h3>
            <div class="space-y-3">
        '''
        
        for q in questions:
            directed_to = q.get("directed_to", "stakeholder")
            html += f'''
                <div class="border-l-4 border-red-400 bg-red-50 p-4 rounded-r-lg">
                    <p class="font-medium text-red-900">{self._escape(q.get("question", ""))}</p>
                    <p class="text-sm text-red-700 mt-1">
                        Directed to: <span class="font-medium">{self._escape(directed_to)}</span>
                    </p>
                </div>
            '''
        
        html += '</div></div>'
        return html
    
    def _render_non_blocking_questions(self, questions: List[Dict]) -> str:
        """Render non-blocking stakeholder questions."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="help-circle" class="w-5 h-5 mr-2 text-gray-500"></i>
                Other Stakeholder Questions
            </h3>
            <div class="space-y-3">
        '''
        
        for q in questions:
            directed_to = q.get("directed_to", "stakeholder")
            html += f'''
                <div class="border border-gray-200 bg-gray-50 p-4 rounded-lg">
                    <p class="font-medium text-gray-900">{self._escape(q.get("question", ""))}</p>
                    <p class="text-sm text-gray-600 mt-1">
                        Directed to: <span class="font-medium">{self._escape(directed_to)}</span>
                    </p>
                </div>
            '''
        
        html += '</div></div>'
        return html
    
    def _render_unknowns(self, unknowns: List[Dict]) -> str:
        """Render unknowns section."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="help-circle" class="w-5 h-5 mr-2 text-amber-500"></i>
                Unknowns
            </h3>
            <div class="space-y-3">
        '''
        
        for unknown in unknowns:
            html += f'''
                <div class="border border-amber-200 bg-amber-50 p-4 rounded-lg">
                    <p class="font-medium text-amber-900">{self._escape(unknown.get("question", ""))}</p>
            '''
            if unknown.get("why_it_matters"):
                html += f'''
                    <p class="text-sm text-amber-700 mt-2">
                        <span class="font-medium">Why it matters:</span> {self._escape(unknown["why_it_matters"])}
                    </p>
                '''
            if unknown.get("impact_if_unresolved"):
                html += f'''
                    <p class="text-sm text-amber-700 mt-1">
                        <span class="font-medium">Impact if unresolved:</span> {self._escape(unknown["impact_if_unresolved"])}
                    </p>
                '''
            html += '</div>'
        
        html += '</div></div>'
        return html
    
    def _render_decision_points(self, decisions: List[Dict]) -> str:
        """Render early decision points."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="git-branch" class="w-5 h-5 mr-2 text-purple-500"></i>
                Early Decision Points
            </h3>
            <div class="space-y-4">
        '''
        
        for decision in decisions:
            html += f'''
                <div class="border border-purple-200 bg-purple-50 p-4 rounded-lg">
                    <p class="font-semibold text-purple-900 mb-2">{self._escape(decision.get("decision_area", ""))}</p>
            '''
            
            if decision.get("why_early"):
                html += f'''
                    <p class="text-sm text-purple-700 mb-2">
                        <span class="font-medium">Why decide early:</span> {self._escape(decision["why_early"])}
                    </p>
                '''
            
            options = decision.get("options", [])
            if options:
                html += '<div class="mb-2"><span class="text-sm font-medium text-purple-800">Options:</span><ul class="list-disc list-inside ml-2">'
                for opt in options:
                    html += f'''
                        <li class="text-sm text-purple-700">{self._escape(opt)}</li>
                    '''
                html += '</ul></div>'
            
            if decision.get("recommendation_direction"):
                html += f'''
                    <div class="bg-purple-100 rounded p-3 mt-2">
                        <span class="text-sm font-medium text-purple-800">Recommendation:</span>
                        <p class="text-sm text-purple-900">{self._escape(decision["recommendation_direction"])}</p>
                    </div>
                '''
            
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
                    <p class="text-sm text-gray-600">{self._escape(risk.get("impact_on_planning", ""))}</p>
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
            <ul class="space-y-2">
        '''
        
        for guardrail in guardrails:
            # Handle both string and dict formats
            if isinstance(guardrail, str):
                html += f'''
                <li class="flex items-start text-sm text-gray-700 bg-green-50 p-3 rounded-lg">
                    <i data-lucide="check" class="w-4 h-4 mr-2 text-green-600 flex-shrink-0 mt-0.5"></i>
                    {self._escape(guardrail)}
                </li>
                '''
            else:
                html += f'''
                <li class="flex items-start text-sm text-gray-700 bg-green-50 p-3 rounded-lg">
                    <i data-lucide="check" class="w-4 h-4 mr-2 text-green-600 flex-shrink-0 mt-0.5"></i>
                    {self._escape(guardrail.get("guardrail", ""))}
                </li>
                '''
        
        html += '</ul></div>'
        return html
    
    def _render_recommendations(self, recommendations: List[str]) -> str:
        """Render recommendations for PM."""
        html = '''
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                <i data-lucide="message-square" class="w-5 h-5 mr-2 text-blue-500"></i>
                Recommendations for PM
            </h3>
            <ul class="space-y-2">
        '''
        
        for rec in recommendations:
            html += f'''
                <li class="flex items-start text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">
                    <i data-lucide="arrow-right" class="w-4 h-4 mr-2 text-blue-600 flex-shrink-0 mt-0.5"></i>
                    {self._escape(rec)}
                </li>
            '''
        
        html += '</ul></div>'
        return html
    # =========================================================================
    # GENERATION - WS-CONCIERGE-001 Integration
    # =========================================================================
    
    def generate_with_profile(
        self,
        project_id: str,
        user_id: str,
        discovery_profile: str = "general",
        handoff_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Project Discovery document with profile and handoff context.
        
        Args:
            project_id: Target project ID
            user_id: User generating the document
            discovery_profile: Question pack profile (general, integrate_systems, change_existing, unknown)
            handoff_context: Optional context from Concierge intake (intent_summary, clarifications, known_unknowns)
        
        Returns:
            Generated discovery document data
            
        Note:
            This is a placeholder for WS-CONCIERGE-001 Step 8.
            Full implementation requires LLM integration with profile-specific prompts.
        """
        logger.info(
            "Generate called with profile=%s, project_id=%s",
            discovery_profile, project_id
        )
        
        # Load profile-specific question pack if needed
        # For v1, this is a placeholder that will be integrated with actual LLM generation
        
        # Incorporate handoff context if provided
        if handoff_context:
            intent_summary = handoff_context.get("intent_summary", "")
            clarifications = handoff_context.get("clarifications", {})
            known_unknowns = handoff_context.get("known_unknowns", [])
            
            logger.info(
                "Handoff context: intent=%s, clarifications=%d, unknowns=%d",
                intent_summary[:50] if intent_summary else "none",
                len(clarifications),
                len(known_unknowns)
            )
        
        # TODO: Actual LLM generation with profile-specific prompts
        # For now, return a minimal valid structure
        return {
            "project_name": f"Project {project_id}",
            "preliminary_summary": {
                "problem_understanding": handoff_context.get("intent_summary", "Project initiated via Concierge") if handoff_context else "Discovery initiated",
                "architectural_intent": "",
                "scope_pressure_points": ""
            },
            "unknowns": handoff_context.get("known_unknowns", []) if handoff_context else [],
            "stakeholder_questions": [],
            "early_decision_points": [],
            "known_constraints": [],
            "assumptions": [],
            "identified_risks": [],
            "mvp_guardrails": [],
            "recommendations_for_pm": []
        }