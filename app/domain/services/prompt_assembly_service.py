"""
Prompt Assembly Service (ADR-041).

Provides prompt assembly from filesystem templates with token resolution.
Can be used both programmatically by workflow executors and via API.

This is distinct from the ADR-034 PromptAssembler which assembles from
database-stored document definitions and components.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from app.domain.prompt.assembler import PromptAssembler, AssembledPrompt
from app.domain.prompt.errors import PromptAssemblyError


logger = logging.getLogger(__name__)


@dataclass
class WorkflowNode:
    """Minimal workflow node data needed for assembly."""
    node_id: str
    task_ref: str
    includes: Dict[str, str]


class PromptAssemblyService:
    """
    Service for assembling prompts from templates with token resolution.
    
    Wraps the ADR-041 PromptAssembler with:
    - Default path configuration
    - Workflow loading and node lookup
    - Consistent interface for API and programmatic use
    
    Usage:
        # Direct assembly
        service = PromptAssemblyService()
        result = service.assemble(
            task_ref="Clarification Questions Generator v1.0",
            includes={"PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt"}
        )

        # From workflow node
        result = service.assemble_from_workflow("pm_discovery", "pgc")
    """

    def __init__(
        self,
        template_root: Optional[Path] = None,
        workflow_root: Optional[Path] = None,
    ):
        """
        Initialize service with path configuration.

        Args:
            template_root: Root directory for task templates.
                          Defaults to combine-config/prompts (via PackageLoader)
            workflow_root: Root directory for workflow JSON files.
                          Defaults to combine-config/workflows
        """
        from app.config.package_loader import get_package_loader
        loader = get_package_loader()

        self._template_root = template_root or (loader.config_path / "prompts")
        self._workflow_root = workflow_root or (loader.config_path / "workflows")

        self._assembler = PromptAssembler(
            template_root=str(self._template_root) if template_root else None,
        )
    
    def assemble(
        self,
        task_ref: str,
        includes: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
    ) -> AssembledPrompt:
        """
        Assemble a prompt from template and includes.
        
        Args:
            task_ref: Task prompt name (e.g., "Clarification Questions Generator v1.0")
            includes: Map of token name to file path for workflow tokens
            correlation_id: Optional correlation ID for logging
            
        Returns:
            AssembledPrompt with content, hash, and metadata
            
        Raises:
            PromptAssemblyError: If assembly fails
        """
        logger.info(
            f"[ADR-041] Assembling prompt: task_ref={task_ref}, "
            f"includes={list((includes or {}).keys())}, "
            f"correlation_id={correlation_id}"
        )
        
        # Convert string to UUID, generate one if not provided
        if correlation_id:
            corr_uuid = UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id
        else:
            corr_uuid = uuid4()
        
        result = self._assembler.assemble(
            task_ref=task_ref,
            includes=includes or {},
            correlation_id=corr_uuid,
        )
        
        logger.info(
            f"[ADR-041] Assembly complete: hash={result.content_hash[:16]}..., "
            f"length={len(result.content)}, resolved={result.includes_resolved}"
        )
        
        return result
    
    def assemble_from_workflow(
        self,
        workflow_id: str,
        node_id: str,
        correlation_id: Optional[str] = None,
    ) -> AssembledPrompt:
        """
        Assemble a prompt using workflow node configuration.
        
        Loads the workflow JSON, finds the specified node, and assembles
        the prompt using the node's task_ref and includes map.
        
        Args:
            workflow_id: Workflow identifier (e.g., "pm_discovery")
            node_id: Node identifier within the workflow (e.g., "pgc")
            correlation_id: Optional correlation ID for logging
            
        Returns:
            AssembledPrompt with content, hash, and metadata
            
        Raises:
            PromptAssemblyError: If workflow/node not found or assembly fails
        """
        logger.info(
            f"[ADR-041] Assembling from workflow: workflow={workflow_id}, "
            f"node={node_id}, correlation_id={correlation_id}"
        )
        
        # Load and find node
        node = self._load_workflow_node(workflow_id, node_id)
        
        # Assemble using node config
        return self.assemble(
            task_ref=node.task_ref,
            includes=node.includes,
            correlation_id=correlation_id,
        )
    
    def get_workflow_node(self, workflow_id: str, node_id: str) -> WorkflowNode:
        """
        Get workflow node configuration without assembling.
        
        Useful for inspection or validation.
        
        Args:
            workflow_id: Workflow identifier
            node_id: Node identifier
            
        Returns:
            WorkflowNode with task_ref and includes
            
        Raises:
            PromptAssemblyError: If workflow/node not found
        """
        return self._load_workflow_node(workflow_id, node_id)
    
    def list_workflows(self) -> List[str]:
        """List available workflow IDs."""
        if not self._workflow_root.exists():
            return []
        
        workflows = []
        for path in self._workflow_root.glob("*.json"):
            # Extract workflow_id from filename (e.g., pm_discovery.v1.json -> pm_discovery)
            name = path.stem
            if ".v" in name:
                name = name.rsplit(".v", 1)[0]
            workflows.append(name)
        
        return sorted(set(workflows))
    
    def list_workflow_nodes(self, workflow_id: str) -> List[str]:
        """
        List node IDs in a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            List of node IDs
            
        Raises:
            PromptAssemblyError: If workflow not found
        """
        workflow = self._load_workflow(workflow_id)
        return [n.get("node_id") for n in workflow.get("nodes", []) if n.get("node_id")]
    
    def _load_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Load workflow JSON by ID."""
        # Try versioned filename first (pm_discovery.v1.json)
        workflow_path = self._workflow_root / f"{workflow_id}.v1.json"
        
        if not workflow_path.exists():
            # Try unversioned
            workflow_path = self._workflow_root / f"{workflow_id}.json"
        
        if not workflow_path.exists():
            available = self.list_workflows()
            raise PromptAssemblyError(
                f"Workflow not found: {workflow_id}. Available: {available}"
            )
        
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise PromptAssemblyError(f"Invalid workflow JSON: {workflow_path}: {e}")
    
    def _load_workflow_node(self, workflow_id: str, node_id: str) -> WorkflowNode:
        """Load and validate a specific workflow node."""
        workflow = self._load_workflow(workflow_id)
        
        # Find node
        node = None
        for n in workflow.get("nodes", []):
            if n.get("node_id") == node_id:
                node = n
                break
        
        if not node:
            available = self.list_workflow_nodes(workflow_id)
            raise PromptAssemblyError(
                f"Node '{node_id}' not found in workflow '{workflow_id}'. "
                f"Available: {available}"
            )
        
        task_ref = node.get("task_ref")
        if not task_ref:
            raise PromptAssemblyError(
                f"Node '{node_id}' in workflow '{workflow_id}' has no task_ref"
            )
        
        return WorkflowNode(
            node_id=node_id,
            task_ref=task_ref,
            includes=node.get("includes", {}),
        )


# Singleton instance for simple use cases
_default_service: Optional[PromptAssemblyService] = None


def get_prompt_assembly_service() -> PromptAssemblyService:
    """
    Get the default PromptAssemblyService instance.
    
    Creates a singleton instance on first call.
    For dependency injection in FastAPI, use PromptAssemblyService() directly.
    """
    global _default_service
    if _default_service is None:
        _default_service = PromptAssemblyService()
    return _default_service