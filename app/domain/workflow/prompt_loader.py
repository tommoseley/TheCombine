"""Prompt loader - load role and task prompts from seed/prompts/.

Provides access to governed prompt artifacts.
"""

from pathlib import Path
from typing import Optional
import logging


logger = logging.getLogger(__name__)


class PromptNotFoundError(Exception):
    """Raised when a prompt file is not found."""
    pass


class PromptLoader:
    """Load role and task prompts from the seed directory.
    
    Prompt naming convention:
    - Role: "Technical Architect 1.0" -> seed/prompts/roles/Technical Architect 1.0.txt
    - Task: "Project Discovery v1.0" -> seed/prompts/tasks/Project Discovery v1.0.txt
    
    Usage:
        loader = PromptLoader()
        role_prompt = loader.load_role("Technical Architect 1.0")
        task_prompt = loader.load_task("Project Discovery v1.0")
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize loader.
        
        Args:
            prompts_dir: Base directory for prompts. Defaults to seed/prompts
        """
        self._prompts_dir = prompts_dir or Path("seed/prompts")
        self._roles_dir = self._prompts_dir / "roles"
        self._tasks_dir = self._prompts_dir / "tasks"
        
        # Cache loaded prompts
        self._role_cache: dict[str, str] = {}
        self._task_cache: dict[str, str] = {}
    
    def load_role(self, role_name: str) -> str:
        """Load a role prompt by name.
        
        Args:
            role_name: Role name (e.g., "Technical Architect 1.0")
            
        Returns:
            Role prompt content
            
        Raises:
            PromptNotFoundError: If role prompt file not found
        """
        if role_name in self._role_cache:
            return self._role_cache[role_name]
        
        path = self._roles_dir / f"{role_name}.txt"
        content = self._load_file(path, "role", role_name)
        self._role_cache[role_name] = content
        return content
    
    def load_task(self, task_name: str) -> str:
        """Load a task prompt by name.
        
        Args:
            task_name: Task name (e.g., "Project Discovery v1.0")
            
        Returns:
            Task prompt content
            
        Raises:
            PromptNotFoundError: If task prompt file not found
        """
        if task_name in self._task_cache:
            return self._task_cache[task_name]
        
        path = self._tasks_dir / f"{task_name}.txt"
        content = self._load_file(path, "task", task_name)
        self._task_cache[task_name] = content
        return content
    
    def _load_file(self, path: Path, prompt_type: str, name: str) -> str:
        """Load and return file content."""
        if not path.exists():
            available = self._list_available(prompt_type)
            raise PromptNotFoundError(
                f"{prompt_type.title()} prompt '{name}' not found at {path}. "
                f"Available: {available}"
            )
        
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            logger.debug(f"Loaded {prompt_type} prompt: {name} ({len(content)} chars)")
            return content
        except IOError as e:
            raise PromptNotFoundError(f"Error reading {prompt_type} prompt '{name}': {e}")
    
    def _list_available(self, prompt_type: str) -> str:
        """List available prompts of given type."""
        dir_path = self._roles_dir if prompt_type == "role" else self._tasks_dir
        if not dir_path.exists():
            return "(directory not found)"
        
        files = [p.stem for p in dir_path.glob("*.txt")]
        return ", ".join(sorted(files)) if files else "(none)"
    
    def list_roles(self) -> list[str]:
        """List available role prompt names."""
        if not self._roles_dir.exists():
            return []
        return sorted([p.stem for p in self._roles_dir.glob("*.txt")])
    
    def list_tasks(self) -> list[str]:
        """List available task prompt names."""
        if not self._tasks_dir.exists():
            return []
        return sorted([p.stem for p in self._tasks_dir.glob("*.txt")])
    
    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._role_cache.clear()
        self._task_cache.clear()
    
    def role_exists(self, role_name: str) -> bool:
        """Check if a role prompt exists."""
        path = self._roles_dir / f"{role_name}.txt"
        return path.exists()
    
    def task_exists(self, task_name: str) -> bool:
        """Check if a task prompt exists."""
        path = self._tasks_dir / f"{task_name}.txt"
        return path.exists()