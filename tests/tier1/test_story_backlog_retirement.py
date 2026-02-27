"""WS-REGISTRY-002: Verify story_backlog is fully retired from the codebase."""

import json
import pathlib


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestStoryBacklogRetirement:
    """Verify no story_backlog or story_detail artifacts remain in active systems."""

    def test_not_in_handler_registry(self):
        """story_backlog must not be registered as a handler."""
        from app.domain.handlers.registry import handler_exists

        assert not handler_exists("story_backlog"), (
            "story_backlog handler is still registered in registry.py"
        )

    def test_not_in_active_releases_tasks(self):
        """story_backlog must not be in active_releases.tasks."""
        ar_path = PROJECT_ROOT / "combine-config" / "_active" / "active_releases.json"
        with open(ar_path) as f:
            ar = json.load(f)
        tasks = ar.get("tasks", {})
        assert "story_backlog" not in tasks, (
            "story_backlog is still in active_releases.tasks"
        )

    def test_not_in_active_releases_document_types(self):
        """story_backlog must not be in active_releases.document_types."""
        ar_path = PROJECT_ROOT / "combine-config" / "_active" / "active_releases.json"
        with open(ar_path) as f:
            ar = json.load(f)
        doc_types = ar.get("document_types", {})
        assert "story_backlog" not in doc_types
        assert "story_detail" not in doc_types

    def test_no_task_prompt_directory(self):
        """Task prompt directory must not exist."""
        prompt_dir = PROJECT_ROOT / "combine-config" / "prompts" / "tasks" / "story_backlog"
        assert not prompt_dir.exists(), (
            f"story_backlog task prompt directory still exists: {prompt_dir}"
        )

    def test_handler_file_deleted(self):
        """Handler source file must not exist."""
        handler_file = PROJECT_ROOT / "app" / "domain" / "handlers" / "story_backlog_handler.py"
        assert not handler_file.exists(), (
            f"story_backlog_handler.py still exists: {handler_file}"
        )

    def test_service_file_deleted(self):
        """Service source file must not exist."""
        service_file = PROJECT_ROOT / "app" / "domain" / "services" / "story_backlog_service.py"
        assert not service_file.exists(), (
            f"story_backlog_service.py still exists: {service_file}"
        )

    def test_not_in_loader_seed_data(self):
        """story_backlog and story_detail must not appear in loader seed data."""
        loader_path = PROJECT_ROOT / "app" / "domain" / "registry" / "loader.py"
        content = loader_path.read_text()
        assert "story_backlog" not in content, (
            "story_backlog still referenced in loader.py seed data"
        )
        assert "story_detail" not in content, (
            "story_detail still referenced in loader.py seed data"
        )
