"""Workflow definition models and loader."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class StepDefinition:
    """Definition of a workflow step."""
    step_id: str
    name: str
    role: str
    task_prompt_id: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    output_schema: Optional[str] = None
    description: Optional[str] = None
    allow_clarification: bool = True
    quality_gate: Optional[str] = None
    is_final: bool = False
    model: str = "sonnet"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepDefinition":
        """Create from dictionary."""
        return cls(
            step_id=data["step_id"],
            name=data["name"],
            role=data["role"],
            task_prompt_id=data["task_prompt_id"],
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            output_schema=data.get("output_schema"),
            description=data.get("description"),
            allow_clarification=data.get("allow_clarification", True),
            quality_gate=data.get("quality_gate"),
            is_final=data.get("is_final", False),
            model=data.get("model", "sonnet"),
        )


@dataclass
class WorkflowMetadata:
    """Workflow metadata."""
    estimated_duration_minutes: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowMetadata":
        """Create from dictionary."""
        return cls(
            estimated_duration_minutes=data.get("estimated_duration_minutes"),
            estimated_cost_usd=data.get("estimated_cost_usd"),
            tags=data.get("tags", []),
        )


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    workflow_id: str
    name: str
    version: str
    steps: List[StepDefinition]
    description: Optional[str] = None
    document_type: Optional[str] = None
    metadata: Optional[WorkflowMetadata] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create from dictionary."""
        steps = [StepDefinition.from_dict(s) for s in data["steps"]]
        metadata = None
        if "metadata" in data:
            metadata = WorkflowMetadata.from_dict(data["metadata"])
        
        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            version=data["version"],
            steps=steps,
            description=data.get("description"),
            document_type=data.get("document_type"),
            metadata=metadata,
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowDefinition":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, path: Path) -> "WorkflowDefinition":
        """Load from JSON file."""
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """Get step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_step_inputs(self, step_id: str) -> List[str]:
        """Get input document types for a step."""
        step = self.get_step(step_id)
        return step.inputs if step else []
    
    def get_step_outputs(self, step_id: str) -> List[str]:
        """Get output document types for a step."""
        step = self.get_step(step_id)
        return step.outputs if step else []
    
    def get_execution_order(self) -> List[str]:
        """Get steps in execution order (respects dependencies)."""
        # Simple topological sort based on input dependencies
        result = []
        available_docs = set()
        remaining = list(self.steps)
        
        while remaining:
            # Find steps whose inputs are all available
            ready = []
            for step in remaining:
                if all(inp in available_docs for inp in step.inputs):
                    ready.append(step)
            
            if not ready:
                # No progress - circular dependency or missing input
                logger.warning(f"Cannot resolve dependencies for: {[s.step_id for s in remaining]}")
                # Add remaining in order
                result.extend([s.step_id for s in remaining])
                break
            
            # Add ready steps and their outputs
            for step in ready:
                result.append(step.step_id)
                available_docs.update(step.outputs)
                remaining.remove(step)
        
        return result
    
    def validate(self) -> List[str]:
        """Validate workflow definition. Returns list of errors."""
        errors = []
        
        # Check required fields
        if not self.workflow_id:
            errors.append("Missing workflow_id")
        if not self.name:
            errors.append("Missing name")
        if not self.steps:
            errors.append("No steps defined")
        
        # Check step dependencies
        all_outputs = set()
        for step in self.steps:
            all_outputs.update(step.outputs)
        
        for step in self.steps:
            for inp in step.inputs:
                if inp not in all_outputs:
                    errors.append(f"Step {step.step_id} requires '{inp}' but no step produces it")
        
        # Check for duplicate step IDs
        step_ids = [s.step_id for s in self.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")
        
        # Check final step exists
        final_steps = [s for s in self.steps if s.is_final]
        if not final_steps:
            errors.append("No final step defined")
        
        return errors


class WorkflowLoader:
    """Load workflow definitions from files."""

    def __init__(self, workflows_dir: Optional[Path] = None):
        """
        Initialize loader.

        Args:
            workflows_dir: Directory containing workflow JSON files
        """
        self._workflows_dir = workflows_dir or Path("combine-config/workflows")
        self._cache: Dict[str, WorkflowDefinition] = {}
    
    def load(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Load a workflow by ID."""
        if workflow_id in self._cache:
            return self._cache[workflow_id]
        
        path = self._workflows_dir / f"{workflow_id}.json"
        if not path.exists():
            logger.warning(f"Workflow not found: {path}")
            return None
        
        try:
            workflow = WorkflowDefinition.from_file(path)
            self._cache[workflow_id] = workflow
            return workflow
        except Exception as e:
            logger.error(f"Failed to load workflow {workflow_id}: {e}")
            return None
    
    def list_workflows(self) -> List[str]:
        """List available workflow IDs."""
        if not self._workflows_dir.exists():
            return []
        return [p.stem for p in self._workflows_dir.glob("*.json")]
    
    def clear_cache(self) -> None:
        """Clear the workflow cache."""
        self._cache.clear()

