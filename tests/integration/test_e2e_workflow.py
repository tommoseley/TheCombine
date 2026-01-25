"""End-to-end workflow integration tests."""

import pytest
import json
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

from app.execution import (
    ExecutionContext,
    LLMStepExecutor,
    StepInput,
    WorkflowDefinition,
    WorkflowLoader,
)
from app.llm import (
    MockLLMProvider,
    PromptBuilder,
    OutputParser,
    DocumentCondenser,
    TelemetryService,
    InMemoryTelemetryStore,
)
from app.persistence import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
    ExecutionStatus,
)


# Sample LLM responses for strategy workflow
DISCOVERY_RESPONSE = json.dumps({
    "project_name": "Test Project",
    "objectives": [
        {"id": "obj-1", "description": "Build MVP", "priority": "high"}
    ],
    "stakeholders": [
        {"name": "Product Owner", "role": "Decision Maker", "influence": "high"}
    ],
    "constraints": [
        {"type": "budget", "description": "Limited budget", "impact": "Use existing infra"}
    ],
    "risks": [],
    "assumptions": ["Team has skills"],
    "scope_summary": "Build MVP"
})

REQUIREMENTS_RESPONSE = json.dumps({
    "functional_requirements": [
        {"id": "FR-1", "title": "User Login", "description": "Users can log in", "priority": "must-have"}
    ],
    "non_functional_requirements": [
        {"id": "NFR-1", "category": "performance", "description": "Fast load"}
    ]
})

ARCHITECTURE_RESPONSE = json.dumps({
    "overview": {
        "summary": "Microservices",
        "architecture_style": "microservices",
        "key_decisions": ["Use FastAPI"]
    },
    "components": [
        {"id": "api", "name": "API", "responsibility": "Handle requests"}
    ],
    "technology_stack": {"backend": ["Python"], "database": ["PostgreSQL"]}
})

REVIEW_RESPONSE = json.dumps({
    "overall_assessment": {"status": "approved", "confidence_score": 85, "summary": "Complete"},
    "findings": [],
    "recommendation": {"action": "proceed", "rationale": "All good"}
})

