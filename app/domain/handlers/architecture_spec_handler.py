"""
Architecture Specification Handler - Handler for architecture_spec document type.

This is the detailed architecture document created after project discovery.
It contains components, data models, interfaces, workflows, and quality attributes.
"""

from typing import Dict, Any, List, Optional, Tuple
import logging

from app.domain.handlers.base_handler import BaseDocumentHandler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def normalize_quality_attributes(qa: Any) -> dict:
    """Normalize quality_attributes from various formats to dict.

    Pure function — no I/O, no side effects.

    Schema expects object form. LLM may produce array of dicts with
    name/acceptance_criteria fields, or non-dict values.

    Args:
        qa: quality_attributes value (list, dict, None, or other)

    Returns:
        Normalized dict with lowercase_underscore keys
    """
    if isinstance(qa, list):
        qa_obj = {}
        for item in qa:
            if isinstance(item, dict) and "name" in item:
                key = item["name"].lower().replace(" ", "_")
                qa_obj[key] = item.get("acceptance_criteria",
                                       item.get("criteria", []))
        return qa_obj
    elif isinstance(qa, dict):
        return qa
    else:
        return {}


def transform_architecture_spec(data: dict) -> dict:
    """Transform architecture spec data.

    Pure function — no I/O, no side effects.
    Mutates the input dict (caller should copy if needed).

    - Migrate legacy field names to schema-canonical names
    - Normalize quality_attributes (array -> object)
    - Ensure required fields exist with correct types
    - Normalize summary structure
    """
    # Legacy field name migration
    if "data_model" in data and "data_models" not in data:
        data["data_models"] = data.pop("data_model")
    if "interfaces" in data and "api_interfaces" not in data:
        data["api_interfaces"] = data.pop("interfaces")

    # Ensure all array fields exist
    for field in [
        "components", "data_models", "api_interfaces",
        "workflows", "risks", "open_questions",
    ]:
        if field not in data:
            data[field] = []

    # Normalize quality_attributes
    data["quality_attributes"] = normalize_quality_attributes(
        data.get("quality_attributes")
    )

    # Ensure architecture_summary is structured
    if "architecture_summary" not in data:
        data["architecture_summary"] = {}
    elif isinstance(data["architecture_summary"], str):
        data["architecture_summary"] = {
            "title": "Architecture Overview",
            "refined_description": data["architecture_summary"],
        }

    return data


class ArchitectureSpecHandler(BaseDocumentHandler):
    """
    Handler for Architecture Specification documents.
    
    Architecture Spec captures:
    - Architecture summary with style and key decisions
    - System components with responsibilities and technologies
    - Data models with fields
    - API interfaces with endpoints
    - Key workflows with steps
    - Quality attributes with targets
    - Risks and mitigations
    """
    
    @property
    def doc_type_id(self) -> str:
        return "architecture_spec"
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def validate(
        self, 
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate architecture spec content.
        
        Required:
        - architecture_summary
        - components (non-empty array)
        """
        errors = []
        
        # Check architecture_summary
        if "architecture_summary" not in data:
            errors.append("Missing required field: 'architecture_summary'")
        
        # Check components exist and non-empty
        if "components" not in data:
            errors.append("Missing required field: 'components'")
        elif not isinstance(data["components"], list):
            errors.append("'components' must be an array")
        elif len(data["components"]) == 0:
            errors.append("'components' cannot be empty")
        else:
            # Validate each component has required fields
            for idx, comp in enumerate(data["components"]):
                if not isinstance(comp, dict):
                    errors.append(f"Component {idx+1} must be an object")
                    continue
                if "name" not in comp:
                    errors.append(f"Component {idx+1} missing 'name'")
                if "purpose" not in comp:
                    errors.append(f"Component {idx+1} missing 'purpose'")
        
        return len(errors) == 0, errors
    
    # =========================================================================
    # TRANSFORMATION
    # =========================================================================
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform architecture spec data. Delegates to pure function."""
        return transform_architecture_spec(data)
    
    # =========================================================================
    # TITLE EXTRACTION
    # =========================================================================
    
    def extract_title(
        self, 
        data: Dict[str, Any],
        fallback: str = "Architecture Specification"
    ) -> str:
        """Extract title from architecture_summary."""
        summary = data.get("architecture_summary", {})
        if isinstance(summary, dict) and summary.get("title"):
            return str(summary["title"])
        return fallback
    
    # =========================================================================
    # RENDERING - Full view
    # =========================================================================
    
    def render(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render full architecture specification document.
        """
        context = context or {}
        html_parts = []
        
        # Main container
        html_parts.append('<div class="space-y-8">')
        
        # Architecture Summary
        summary = data.get("architecture_summary", {})
        if summary:
            html_parts.append(self._render_summary(summary))
        
        # Components
        components = data.get("components", [])
        if components:
            html_parts.append(self._render_components(components))
        
        # Data Models
        data_models = data.get("data_models", [])
        if data_models:
            html_parts.append(self._render_data_models(data_models))

        # Interfaces
        interfaces = data.get("api_interfaces", [])
        if interfaces:
            html_parts.append(self._render_interfaces(interfaces))
        
        # Workflows
        workflows = data.get("workflows", [])
        if workflows:
            html_parts.append(self._render_workflows(workflows))
        
        # Quality Attributes
        qa = data.get("quality_attributes", [])
        if qa:
            html_parts.append(self._render_quality_attributes(qa))
        
        # Risks
        risks = data.get("risks", [])
        if risks:
            html_parts.append(self._render_risks(risks))
        
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
        Render summary card for architecture spec.
        """
        summary = data.get("architecture_summary", {})
        title = summary.get("title", "Architecture Specification") if isinstance(summary, dict) else "Architecture"
        style = summary.get("architectural_style", "") if isinstance(summary, dict) else ""
        
        components = data.get("components", [])
        component_count = len(components)
        
        interfaces = data.get("api_interfaces", [])
        interface_count = len(interfaces)
        
        risks = data.get("risks", [])
        high_risks = len([r for r in risks if r.get("likelihood") == "high"])
        
        html = f'''
        <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between mb-2">
                <div class="flex items-center">
                    <i data-lucide="landmark" class="w-5 h-5 mr-2 text-blue-600"></i>
                    <h3 class="font-semibold text-gray-900">{self._escape(title)}</h3>
                </div>
            </div>
        '''
        
        if style:
            html += f'<p class="text-sm text-gray-600 mb-3">{self._escape(style)}</p>'
        
        html += '<div class="flex items-center space-x-4 text-xs text-gray-500">'
        
        html += f'''
            <span class="flex items-center">
                <i data-lucide="box" class="w-3 h-3 mr-1"></i>
                {component_count} components
            </span>
        '''
        
        if interface_count > 0:
            html += f'''
                <span class="flex items-center">
                    <i data-lucide="plug" class="w-3 h-3 mr-1"></i>
                    {interface_count} interfaces
                </span>
            '''
        
        if high_risks > 0:
            html += f'''
                <span class="flex items-center text-red-600">
                    <i data-lucide="alert-triangle" class="w-3 h-3 mr-1"></i>
                    {high_risks} high risks
                </span>
            '''
        
        html += '</div></div>'
        
        return html
    
    # =========================================================================
    # PRIVATE RENDER HELPERS
    # =========================================================================
    
    def _escape(self, text: Any) -> str:
        """HTML escape a string."""
        if text is None:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    def _render_summary(self, summary: Dict) -> str:
        """Render architecture summary section."""
        title = summary.get("title", "Architecture Overview")
        
        html = f'''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-xl font-semibold text-gray-900">{self._escape(title)}</h2>
            </div>
            <div class="p-6 space-y-4">
        '''
        
        if summary.get("refined_description"):
            html += f'<p class="text-gray-700">{self._escape(summary["refined_description"])}</p>'
        
        if summary.get("architectural_style"):
            html += f'''
                <div class="bg-gray-50 rounded-lg p-4">
                    <h3 class="font-semibold text-gray-900 mb-2">Architectural Style</h3>
                    <p class="text-sm text-gray-700">{self._escape(summary["architectural_style"])}</p>
                </div>
            '''
        
        decisions = summary.get("key_decisions", [])
        if decisions:
            html += '''
                <div>
                    <h3 class="font-semibold text-gray-900 mb-2">Key Decisions</h3>
                    <ul class="space-y-2">
            '''
            for decision in decisions:
                html += f'''
                    <li class="flex items-start gap-2">
                        <i data-lucide="check-circle" class="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0"></i>
                        <span class="text-sm text-gray-700">{self._escape(decision)}</span>
                    </li>
                '''
            html += '</ul></div>'
        
        html += '</div></div>'
        return html
    
    def _render_components(self, components: List[Dict]) -> str:
        """Render system components section."""
        html = f'''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <i data-lucide="box" class="w-5 h-5 text-gray-600"></i>
                <h2 class="text-xl font-semibold text-gray-900">System Components</h2>
                <span class="ml-auto text-sm text-gray-500">{len(components)} components</span>
            </div>
            <div class="p-6">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        '''
        
        for comp in components:
            layer = comp.get("layer", "")
            html += f'''
                <div class="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
                    <div class="flex items-start justify-between mb-2">
                        <h3 class="font-semibold text-gray-900">{self._escape(comp.get("name", ""))}</h3>
            '''
            
            if layer:
                html += f'<span class="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600">{self._escape(layer)}</span>'
            
            html += '</div>'
            
            if comp.get("purpose"):
                html += f'<p class="text-sm text-gray-600 mb-3">{self._escape(comp["purpose"])}</p>'
            
            responsibilities = comp.get("responsibilities", [])
            if responsibilities:
                html += '''
                    <div class="text-xs text-gray-500">
                        <span class="font-medium">Responsibilities:</span>
                        <ul class="list-disc list-inside mt-1 space-y-1">
                '''
                for resp in responsibilities[:3]:
                    html += f'<li>{self._escape(resp)}</li>'
                if len(responsibilities) > 3:
                    html += f'<li class="text-gray-400">+ {len(responsibilities) - 3} more...</li>'
                html += '</ul></div>'
            
            tech = comp.get("technology_choices", [])
            if tech:
                html += '''
                    <div class="mt-3 pt-3 border-t border-gray-100">
                        <div class="flex flex-wrap gap-1">
                '''
                for t in tech[:3]:
                    html += f'<span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">{self._escape(t)}</span>'
                html += '</div></div>'
            
            html += '</div>'
        
        html += '</div></div></div>'
        return html
    
    def _render_data_models(self, models: List[Dict]) -> str:
        """Render data models section."""
        html = f'''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <i data-lucide="database" class="w-5 h-5 text-gray-600"></i>
                <h2 class="text-xl font-semibold text-gray-900">Data Models</h2>
                <span class="ml-auto text-sm text-gray-500">{len(models)} models</span>
            </div>
            <div class="p-6 space-y-4">
        '''
        
        for model in models:
            html += f'''
                <div class="border-l-4 border-gray-400 pl-4 bg-gray-50 rounded-r p-4">
                    <h3 class="font-semibold text-gray-900 mb-2">{self._escape(model.get("name", ""))}</h3>
            '''
            
            if model.get("description"):
                html += f'<p class="text-sm text-gray-600 mb-3">{self._escape(model["description"])}</p>'
            
            fields = model.get("fields", [])
            if fields:
                html += '''
                    <div class="mt-2 space-y-1">
                        <span class="text-xs font-medium text-gray-500">Fields:</span>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                '''
                for field in fields:
                    required = '<span class="text-red-600">*</span>' if field.get("required") else ""
                    html += f'''
                        <div class="text-xs font-mono bg-white rounded px-2 py-1 border border-gray-200">
                            <span class="text-gray-700">{self._escape(field.get("name", ""))}</span>
                            <span class="text-gray-400">: {self._escape(field.get("type", ""))}</span>
                            {required}
                        </div>
                    '''
                html += '</div></div>'
            
            html += '</div>'
        
        html += '</div></div>'
        return html
    
    def _render_interfaces(self, interfaces: List[Dict]) -> str:
        """Render API interfaces section."""
        html = f'''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <i data-lucide="plug" class="w-5 h-5 text-gray-600"></i>
                <h2 class="text-xl font-semibold text-gray-900">API Interfaces</h2>
                <span class="ml-auto text-sm text-gray-500">{len(interfaces)} interfaces</span>
            </div>
            <div class="p-6 space-y-6">
        '''
        
        for interface in interfaces:
            protocol = interface.get("protocol", "")
            html += f'''
                <div class="border border-gray-200 rounded-lg p-4">
                    <div class="flex items-center justify-between mb-2">
                        <div>
                            <h3 class="font-semibold text-gray-900">{self._escape(interface.get("name", ""))}</h3>
            '''
            
            if interface.get("description"):
                html += f'<p class="text-sm text-gray-600">{self._escape(interface["description"])}</p>'
            
            html += '</div>'
            
            if protocol:
                html += f'<span class="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">{self._escape(protocol)}</span>'
            
            html += '</div>'
            
            endpoints = interface.get("endpoints", [])
            if endpoints:
                html += '<div class="space-y-2 mt-4">'
                for ep in endpoints:
                    method = ep.get("method", "GET")
                    method_class = {
                        "GET": "bg-blue-100 text-blue-800",
                        "POST": "bg-green-100 text-green-800",
                        "PUT": "bg-amber-100 text-amber-800",
                        "PATCH": "bg-amber-100 text-amber-800",
                        "DELETE": "bg-red-100 text-red-800",
                    }.get(method, "bg-gray-100 text-gray-800")
                    
                    html += f'''
                        <div class="bg-gray-50 rounded p-3 font-mono text-sm">
                            <div class="flex items-center gap-3 mb-1">
                                <span class="px-2 py-0.5 rounded text-xs font-semibold {method_class}">
                                    {self._escape(method)}
                                </span>
                                <span class="text-gray-900">{self._escape(ep.get("path", ""))}</span>
                            </div>
                    '''
                    
                    if ep.get("description"):
                        html += f'<p class="text-xs text-gray-600 font-sans mt-2">{self._escape(ep["description"])}</p>'
                    
                    html += '</div>'
                
                html += '</div>'
            
            html += '</div>'
        
        html += '</div></div>'
        return html
    
    def _render_workflows(self, workflows: List[Dict]) -> str:
        """Render workflows section."""
        html = f'''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <i data-lucide="workflow" class="w-5 h-5 text-gray-600"></i>
                <h2 class="text-xl font-semibold text-gray-900">Key Workflows</h2>
                <span class="ml-auto text-sm text-gray-500">{len(workflows)} workflows</span>
            </div>
            <div class="p-6 space-y-4">
        '''
        
        for workflow in workflows:
            html += f'''
                <details class="border border-gray-200 rounded-lg">
                    <summary class="p-4 cursor-pointer hover:bg-gray-50 font-semibold text-gray-900">
                        {self._escape(workflow.get("name", ""))}
                    </summary>
                    <div class="p-4 pt-0">
            '''
            
            if workflow.get("description"):
                html += f'<p class="text-sm text-gray-600 mb-4">{self._escape(workflow["description"])}</p>'
            
            steps = workflow.get("steps", [])
            if steps:
                html += '<div class="space-y-3">'
                for step in steps:
                    order = step.get("order", "")
                    html += f'''
                        <div class="flex gap-3">
                            <div class="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-semibold">
                                {self._escape(order)}
                            </div>
                            <div class="flex-1">
                                <div class="font-medium text-gray-900">{self._escape(step.get("action", ""))}</div>
                                <div class="text-xs text-gray-500">Actor: {self._escape(step.get("actor", ""))}</div>
                            </div>
                        </div>
                    '''
                html += '</div>'
            
            html += '</div></details>'
        
        html += '</div></div>'
        return html
    
    def _render_quality_attributes(self, qa_list: List[Dict]) -> str:
        """Render quality attributes section."""
        html = '''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <i data-lucide="target" class="w-5 h-5 text-gray-600"></i>
                <h2 class="text-xl font-semibold text-gray-900">Quality Attributes</h2>
            </div>
            <div class="p-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        '''
        
        for qa in qa_list:
            html += f'''
                <div class="border border-gray-200 rounded-lg p-4">
                    <h3 class="font-semibold text-gray-900 mb-2">{self._escape(qa.get("name", ""))}</h3>
                    <p class="text-sm text-gray-600 mb-2">{self._escape(qa.get("rationale", ""))}</p>
            '''
            
            if qa.get("target"):
                html += f'''
                    <div class="text-xs bg-gray-100 text-gray-700 rounded px-2 py-1 inline-block">
                        Target: {self._escape(qa["target"])}
                    </div>
                '''
            
            html += '</div>'
        
        html += '</div></div></div>'
        return html
    
    def _render_risks(self, risks: List[Dict]) -> str:
        """Render risks section."""
        html = '''
        <div class="bg-white rounded-lg border border-gray-200">
            <div class="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
                <i data-lucide="alert-triangle" class="w-5 h-5 text-amber-600"></i>
                <h2 class="text-xl font-semibold text-gray-900">Risks & Mitigation</h2>
            </div>
            <div class="p-6 space-y-3">
        '''
        
        for risk in risks:
            likelihood = risk.get("likelihood", "medium")
            
            if likelihood == "high":
                border_class = "border-red-600 bg-red-50"
                badge_class = "bg-red-100 text-red-800"
            elif likelihood == "medium":
                border_class = "border-amber-600 bg-amber-50"
                badge_class = "bg-amber-100 text-amber-800"
            else:
                border_class = "border-green-600 bg-green-50"
                badge_class = "bg-green-100 text-green-800"
            
            html += f'''
                <div class="border-l-4 rounded-r p-3 {border_class}">
                    <div class="flex items-start justify-between mb-2">
                        <h3 class="font-semibold text-gray-900">{self._escape(risk.get("description", ""))}</h3>
                        <span class="text-xs px-2 py-1 rounded {badge_class}">
                            {self._escape(likelihood)}
                        </span>
                    </div>
            '''
            
            if risk.get("mitigation"):
                html += f'<p class="text-sm text-gray-700"><strong>Mitigation:</strong> {self._escape(risk["mitigation"])}</p>'
            
            html += '</div>'
        
        html += '</div></div>'
        return html