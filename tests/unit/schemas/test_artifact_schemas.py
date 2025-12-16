"""Tests for artifact schemas."""
import pytest
from pydantic import ValidationError

from app.domain.schemas.artifacts import (
    EpicSpec,
    Story,
    ArchitectureSpec,
    ComponentSpec,
    CodeDeliverable,
    FileSpec,
    QAReport,
    IssueSpec,
)


class TestEpicSpec:
    def test_valid_epic(self):
        data = {
            "epic_id": "EPIC-001",
            "title": "Test Epic",
            "goal": "Test goal",
            "success_criteria": ["Criterion 1"],
            "stories": [
                {
                    "id": "STORY-1",
                    "title": "Test Story",
                    "user_story": "As a user",
                    "acceptance_criteria": ["AC1"],
                    "estimate_hours": 8,
                    "priority": "high",
                }
            ],
            "total_estimate_hours": 8,
        }
        epic = EpicSpec(**data)
        assert epic.epic_id == "EPIC-001"
        assert len(epic.stories) == 1

    def test_missing_required_field(self):
        data = {"epic_id": "EPIC-001", "title": "Test"}
        with pytest.raises(ValidationError):
            EpicSpec(**data)

    def test_invalid_story_id(self):
        data = {
            "epic_id": "EPIC-001",
            "title": "Test",
            "goal": "Goal",
            "success_criteria": ["SC1"],
            "stories": [
                {
                    "id": "BAD-ID",
                    "title": "Story",
                    "user_story": "As a user",
                    "acceptance_criteria": ["AC1"],
                    "estimate_hours": 8,
                    "priority": "high",
                }
            ],
            "total_estimate_hours": 8,
        }
        with pytest.raises(ValidationError):
            EpicSpec(**data)

    def test_invalid_priority(self):
        data = {
            "epic_id": "EPIC-001",
            "title": "Test",
            "goal": "Goal",
            "success_criteria": ["SC1"],
            "stories": [
                {
                    "id": "STORY-1",
                    "title": "Story",
                    "user_story": "As a user",
                    "acceptance_criteria": ["AC1"],
                    "estimate_hours": 8,
                    "priority": "urgent",
                }
            ],
            "total_estimate_hours": 8,
        }
        with pytest.raises(ValidationError):
            EpicSpec(**data)


class TestArchitectureSpec:
    def test_valid_architecture(self):
        data = {
            "epic_id": "EPIC-001",
            "components": [
                {
                    "name": "TestComponent",
                    "purpose": "Test",
                    "file_path": "test.py",
                    "responsibilities": ["Do thing"],
                    "dependencies": [],
                    "public_interface": [],
                    "error_handling": [],
                    "test_count": 5,
                }
            ],
            "adrs": [],
            "test_strategy": {},
            "acceptance_criteria": ["AC1"],
        }
        arch = ArchitectureSpec(**data)
        assert arch.epic_id == "EPIC-001"
        assert len(arch.components) == 1


class TestCodeDeliverable:
    def test_valid_code_deliverable(self):
        data = {
            "files": [{"path": "test.py", "content": "print('hello')"}],
            "test_files": [],
            "dependencies": ["pytest"],
        }
        code = CodeDeliverable(**data)
        assert len(code.files) == 1


class TestQAReport:
    def test_valid_qa_report(self):
        data = {
            "passed": False,
            "issues": [
                {
                    "id": "QA-1",
                    "severity": "high",
                    "category": "code",
                    "description": "Issue",
                    "location": "test.py:10",
                    "fix_required": True,
                }
            ],
            "test_results": {},
            "recommendations": ["Fix issues"],
        }
        report = QAReport(**data)
        assert report.passed is False
