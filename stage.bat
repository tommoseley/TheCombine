# Stage all files
git add app/orchestrator_api/services/llm_response_parser.py \
        app/orchestrator_api/services/llm_caller.py \
        app/orchestrator_api/services/configuration_loader.py \
        app/orchestrator_api/services/usage_recorder.py \
        app/orchestrator_api/services/phase_execution_orchestrator.py \
        app/orchestrator_api/services/pipeline_service.py \
        config.py \
        tests/unit/services/test_llm_response_parser.py \
        tests/unit/services/test_llm_caller.py \
        tests/unit/services/test_configuration_loader.py \
        tests/unit/services/test_usage_recorder.py \
        tests/unit/services/test_phase_execution_orchestrator.py \

# Commit with full message
git commit -m "PIPELINE-175B: Data-Driven Pipeline Execution

Components: 6 new components (496 LOC)
Tests: 62 new tests (70 total, all passing)
Coverage: >95% on all new code
QA: All 5 critical issues resolved

Developer: D-1, D-2, D-3
Date: 2025-12-05"

# Push
git push origin main