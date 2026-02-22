"""Tests for artifact schemas."""

from app.domain.schemas.artifacts import (
    ArchitectureSpec,
    CodeDeliverable,
    QAReport,
)


class TestArchitectureSpec:
    def test_valid_architecture(self):
        data = {
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
        assert len(arch.components) == 1
        assert arch.components[0].name == "TestComponent"


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
