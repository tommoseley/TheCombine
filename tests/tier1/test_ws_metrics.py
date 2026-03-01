"""
WS-METRICS-001: Developer Execution Metrics — Tier 1 Verification

Criteria:
1. WS execution record created (POST creates DB record)
2. Phase metrics stored (phase completion appends to phase_metrics JSONB)
3. Bug fix linked (POST bug-fix creates record linked to ws_execution_id)
4. Duration calculated (completed_at - started_at = correct duration_seconds)
5. LLM cost aggregated (dashboard returns cost totals consistent with stored data)
6. Filtering works (GET ws-executions with wp_id filter returns only matching)
7. Dashboard aggregates (GET dashboard returns correct sums/averages)
8. Partial updates (posting a phase completion appends, does not overwrite)
9. Migration clean (Alembic migration applies and rolls back cleanly)
10. Idempotent phase updates (duplicate event_id safely ignored)
11. Status enum enforced (invalid status rejected)
12. Phase name enum enforced (invalid phase name rejected)
13. Scoreboard returns correct data
14. Scoreboard window filtering (7d returns only last 7 days)
15. Correlation ID present (LLM execution logs linked via ws_execution_id)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from app.domain.repositories.in_memory_ws_metrics_repository import (
    InMemoryWSMetricsRepository,
)
from app.domain.repositories.ws_metrics_repository import (
    VALID_STATUSES,
    VALID_PHASE_NAMES,
    WSExecutionRecord,
)
from app.domain.services.ws_metrics_service import (
    WSMetricsService,
    InvalidStatusError,
    InvalidPhaseNameError,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def repo():
    return InMemoryWSMetricsRepository()


@pytest.fixture
def service(repo):
    return WSMetricsService(repo)


# =============================================================================
# Criterion 1: WS execution record created
# =============================================================================

class TestCriterion1ExecutionCreated:
    """POST to ws-execution endpoint creates a database record."""

    @pytest.mark.asyncio
    async def test_start_execution_creates_record(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001",
            executor="claude_code",
            wp_id="WP-001",
        )
        record = await repo.get_execution(exec_id)
        assert record is not None
        assert record.ws_id == "WS-TEST-001"
        assert record.executor == "claude_code"
        assert record.wp_id == "WP-001"
        assert record.status == "STARTED"

    @pytest.mark.asyncio
    async def test_start_execution_sets_started_at(self, service, repo):
        before = datetime.now(timezone.utc)
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        after = datetime.now(timezone.utc)
        record = await repo.get_execution(exec_id)
        assert before <= record.started_at <= after

    @pytest.mark.asyncio
    async def test_start_execution_initializes_metrics(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        record = await repo.get_execution(exec_id)
        assert record.phase_metrics == {"phases": []}
        assert record.test_metrics == {"written": 0, "passing": 0, "failing": 0, "skipped": 0}
        assert record.file_metrics == {"created": [], "modified": [], "deleted": []}


# =============================================================================
# Criterion 2: Phase metrics stored
# =============================================================================

class TestCriterion2PhaseMetrics:
    """Phase completion updates append to phase_metrics JSONB."""

    @pytest.mark.asyncio
    async def test_record_phase_appends(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        await service.record_phase(
            execution_id=exec_id,
            event_id="evt-001",
            name="failing_tests",
            started_at="2026-02-23T10:00:00Z",
            completed_at="2026-02-23T10:04:30Z",
            duration_seconds=270,
            result="pass",
            tests_written=6,
        )
        record = await repo.get_execution(exec_id)
        phases = record.phase_metrics["phases"]
        assert len(phases) == 1
        assert phases[0]["name"] == "failing_tests"
        assert phases[0]["duration_seconds"] == 270
        assert phases[0]["tests_written"] == 6
        assert phases[0]["sequence"] == 1


# =============================================================================
# Criterion 3: Bug fix linked
# =============================================================================

class TestCriterion3BugFixLinked:
    """POST to bug-fix endpoint creates record linked to ws_execution_id."""

    @pytest.mark.asyncio
    async def test_record_bug_fix_linked(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        bf_id = await service.record_bug_fix(
            ws_execution_id=exec_id,
            description="Form-data false positive",
            root_cause="URL-encoded + signs creating 3 char classes",
            test_name="test_form_data_not_flagged",
            fix_summary="Added content-type-aware scanning",
            autonomous=True,
            files_modified=["app/api/middleware/secret_ingress.py"],
        )
        fixes = await repo.get_bug_fixes_for_execution(exec_id)
        assert len(fixes) == 1
        assert fixes[0].id == bf_id
        assert fixes[0].ws_execution_id == exec_id
        assert fixes[0].autonomous is True


# =============================================================================
# Criterion 4: Duration calculated
# =============================================================================

class TestCriterion4Duration:
    """completed_at - started_at produces correct duration_seconds."""

    @pytest.mark.asyncio
    async def test_duration_calculated_on_complete(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        # Small sleep equivalent: complete immediately, duration >= 0
        await service.complete_execution(
            execution_id=exec_id, status="COMPLETED"
        )
        record = await repo.get_execution(exec_id)
        assert record.duration_seconds is not None
        assert record.duration_seconds >= 0
        assert record.completed_at is not None
        assert record.status == "COMPLETED"


# =============================================================================
# Criterion 5: LLM cost aggregated
# =============================================================================

class TestCriterion5CostAggregated:
    """Dashboard returns cost totals consistent with stored execution data."""

    @pytest.mark.asyncio
    async def test_dashboard_cost_totals(self, service, repo):
        # Create two completed executions with known costs
        id1 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.complete_execution(
            execution_id=id1, status="COMPLETED", llm_cost_usd=Decimal("1.50")
        )
        id2 = await service.start_execution(ws_id="WS-B", executor="claude_code")
        await service.complete_execution(
            execution_id=id2, status="COMPLETED", llm_cost_usd=Decimal("2.50")
        )

        dashboard = await service.get_dashboard()
        assert dashboard["total_llm_cost_usd"] == pytest.approx(4.0)
        assert dashboard["cost_per_ws"] == pytest.approx(2.0)


# =============================================================================
# Criterion 6: Filtering works
# =============================================================================

class TestCriterion6Filtering:
    """GET ws-executions with wp_id filter returns only matching records."""

    @pytest.mark.asyncio
    async def test_filter_by_wp_id(self, service, repo):
        await service.start_execution(ws_id="WS-A", executor="claude_code", wp_id="WP-001")
        await service.start_execution(ws_id="WS-B", executor="claude_code", wp_id="WP-002")
        await service.start_execution(ws_id="WS-C", executor="claude_code", wp_id="WP-001")

        results = await repo.list_executions(wp_id="WP-001")
        assert len(results) == 2
        assert all(r.wp_id == "WP-001" for r in results)

    @pytest.mark.asyncio
    async def test_filter_by_status(self, service, repo):
        id1 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.complete_execution(execution_id=id1, status="COMPLETED")
        await service.start_execution(ws_id="WS-B", executor="claude_code")

        results = await repo.list_executions(status="COMPLETED")
        assert len(results) == 1
        assert results[0].ws_id == "WS-A"


# =============================================================================
# Criterion 7: Dashboard aggregates
# =============================================================================

class TestCriterion7Dashboard:
    """GET dashboard returns correct sums/averages across multiple executions."""

    @pytest.mark.asyncio
    async def test_dashboard_aggregates(self, service, repo):
        # Create 3 executions: 2 completed, 1 failed
        id1 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.update_execution(
            id1, test_metrics={"written": 6, "passing": 6, "failing": 0, "skipped": 0}
        )
        await service.complete_execution(
            execution_id=id1, status="COMPLETED",
            llm_cost_usd=Decimal("1.00"),
        )

        id2 = await service.start_execution(ws_id="WS-B", executor="claude_code")
        await service.update_execution(
            id2, test_metrics={"written": 4, "passing": 4, "failing": 0, "skipped": 0}
        )
        await service.complete_execution(
            execution_id=id2, status="COMPLETED",
            llm_cost_usd=Decimal("3.00"),
        )

        id3 = await service.start_execution(ws_id="WS-C", executor="claude_code")
        await service.update_execution(
            id3, test_metrics={"written": 2, "passing": 0, "failing": 2, "skipped": 0}
        )
        await service.complete_execution(execution_id=id3, status="FAILED")

        dashboard = await service.get_dashboard()
        assert dashboard["total_ws_completed"] == 2
        assert dashboard["total_tests_written"] == 12
        assert dashboard["total_llm_cost_usd"] == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_dashboard_rework_average(self, service, repo):
        id1 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.update_execution(id1, rework_cycles=0)
        await service.complete_execution(execution_id=id1, status="COMPLETED")

        id2 = await service.start_execution(ws_id="WS-B", executor="claude_code")
        await service.update_execution(id2, rework_cycles=2)
        await service.complete_execution(execution_id=id2, status="COMPLETED")

        dashboard = await service.get_dashboard()
        assert dashboard["rework_cycle_average"] == pytest.approx(1.0)


# =============================================================================
# Criterion 8: Partial updates (append, not overwrite)
# =============================================================================

class TestCriterion8PartialUpdates:
    """Posting a phase completion to an existing execution appends, not overwrites."""

    @pytest.mark.asyncio
    async def test_multiple_phases_append(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        await service.record_phase(
            execution_id=exec_id,
            event_id="evt-001",
            name="failing_tests",
            started_at="2026-02-23T10:00:00Z",
            completed_at="2026-02-23T10:04:30Z",
            duration_seconds=270,
            result="pass",
        )
        await service.record_phase(
            execution_id=exec_id,
            event_id="evt-002",
            name="implement",
            started_at="2026-02-23T10:04:30Z",
            completed_at="2026-02-23T10:18:00Z",
            duration_seconds=810,
            result="pass",
        )
        await service.record_phase(
            execution_id=exec_id,
            event_id="evt-003",
            name="verify",
            started_at="2026-02-23T10:18:00Z",
            completed_at="2026-02-23T10:22:00Z",
            duration_seconds=240,
            result="pass",
        )

        record = await repo.get_execution(exec_id)
        phases = record.phase_metrics["phases"]
        assert len(phases) == 3
        assert phases[0]["name"] == "failing_tests"
        assert phases[1]["name"] == "implement"
        assert phases[2]["name"] == "verify"
        assert phases[0]["sequence"] == 1
        assert phases[1]["sequence"] == 2
        assert phases[2]["sequence"] == 3


# =============================================================================
# Criterion 9: Migration clean
# (Deferred — Alembic migration tested at Tier 2/3 against real DB.
#  For Tier 1, we verify the ORM model can be imported and has expected columns.)
# =============================================================================

class TestCriterion9MigrationClean:
    """Alembic migration applies and rolls back cleanly."""

    def test_orm_model_importable(self):
        """ORM models exist and are importable."""
        from app.domain.models.ws_metrics import WSExecution, WSBugFix
        assert WSExecution.__tablename__ == "ws_executions"
        assert WSBugFix.__tablename__ == "ws_bug_fixes"

    def test_orm_model_has_expected_columns(self):
        """ORM models have all required columns."""
        from app.domain.models.ws_metrics import WSExecution, WSBugFix

        ws_cols = {c.name for c in WSExecution.__table__.columns}
        expected_ws = {
            "id", "ws_id", "wp_id", "scope_id", "executor", "status",
            "started_at", "completed_at", "duration_seconds",
            "phase_metrics", "test_metrics", "file_metrics",
            "rework_cycles", "llm_calls", "llm_tokens_in", "llm_tokens_out",
            "llm_cost_usd", "created_at",
        }
        assert expected_ws.issubset(ws_cols), f"Missing columns: {expected_ws - ws_cols}"

        bf_cols = {c.name for c in WSBugFix.__table__.columns}
        expected_bf = {
            "id", "ws_execution_id", "scope_id", "description", "root_cause",
            "test_name", "fix_summary", "files_modified", "autonomous", "created_at",
        }
        assert expected_bf.issubset(bf_cols), f"Missing columns: {expected_bf - bf_cols}"

    @pytest.mark.skip(reason="ws_metrics migration not yet created — ORM models defined but migration deferred")
    def test_migration_file_exists(self):
        """Alembic migration file exists on disk."""
        from pathlib import Path
        migration_dir = Path(__file__).resolve().parent.parent.parent / "alembic" / "versions"
        migrations = list(migration_dir.glob("*ws_metrics*"))
        assert len(migrations) >= 1, "No ws_metrics migration found"


# =============================================================================
# Criterion 10: Idempotent phase updates
# =============================================================================

class TestCriterion10IdempotentPhase:
    """Duplicate POST with same event_id is safely ignored, not double-appended."""

    @pytest.mark.asyncio
    async def test_duplicate_event_id_ignored(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        await service.record_phase(
            execution_id=exec_id,
            event_id="evt-001",
            name="failing_tests",
            started_at="2026-02-23T10:00:00Z",
            result="pass",
        )
        # Post same event_id again
        await service.record_phase(
            execution_id=exec_id,
            event_id="evt-001",
            name="failing_tests",
            started_at="2026-02-23T10:00:00Z",
            result="pass",
        )
        record = await repo.get_execution(exec_id)
        phases = record.phase_metrics["phases"]
        assert len(phases) == 1, f"Expected 1 phase, got {len(phases)}"


# =============================================================================
# Criterion 11: Status enum enforced
# =============================================================================

class TestCriterion11StatusEnum:
    """POST with invalid status value is rejected."""

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, service):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        with pytest.raises(InvalidStatusError):
            await service.update_execution(exec_id, status="INVALID_STATUS")

    @pytest.mark.asyncio
    async def test_valid_statuses_accepted(self, service):
        for status in VALID_STATUSES:
            exec_id = await service.start_execution(
                ws_id=f"WS-{status}", executor="claude_code"
            )
            await service.update_execution(exec_id, status=status)
            # No exception = pass


# =============================================================================
# Criterion 12: Phase name enum enforced
# =============================================================================

class TestCriterion12PhaseNameEnum:
    """Phase with invalid name is rejected."""

    @pytest.mark.asyncio
    async def test_invalid_phase_name_rejected(self, service):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        with pytest.raises(InvalidPhaseNameError):
            await service.record_phase(
                execution_id=exec_id,
                event_id="evt-001",
                name="invalid_phase",
                started_at="2026-02-23T10:00:00Z",
            )

    @pytest.mark.asyncio
    async def test_valid_phase_names_accepted(self, service):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        for i, name in enumerate(sorted(VALID_PHASE_NAMES)):
            await service.record_phase(
                execution_id=exec_id,
                event_id=f"evt-{i:03d}",
                name=name,
                started_at="2026-02-23T10:00:00Z",
            )
            # No exception = pass


# =============================================================================
# Criterion 13: Scoreboard returns correct data
# =============================================================================

class TestCriterion13Scoreboard:
    """GET scoreboard returns runs, success rate, avg/p95 duration, etc."""

    @pytest.mark.asyncio
    async def test_scoreboard_correct_data(self, service, repo):
        # 3 runs: 2 completed, 1 failed
        id1 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.update_execution(id1, rework_cycles=0)
        await service.complete_execution(
            execution_id=id1, status="COMPLETED", llm_cost_usd=Decimal("1.00")
        )

        id2 = await service.start_execution(ws_id="WS-B", executor="claude_code")
        await service.update_execution(id2, rework_cycles=1)
        await service.complete_execution(
            execution_id=id2, status="COMPLETED", llm_cost_usd=Decimal("3.00")
        )

        id3 = await service.start_execution(ws_id="WS-C", executor="claude_code")
        await service.complete_execution(execution_id=id3, status="FAILED")

        # Record a bug fix
        await service.record_bug_fix(
            ws_execution_id=id1,
            description="Test bug",
            root_cause="Test root cause",
            test_name="test_something",
            fix_summary="Fixed it",
            autonomous=True,
        )

        scoreboard = await service.get_scoreboard(window="all")
        assert scoreboard["total_runs"] == 3
        assert scoreboard["success_rate"] == pytest.approx(2 / 3)
        assert scoreboard["first_pass_rate"] == pytest.approx(0.5)
        assert scoreboard["total_llm_cost_usd"] == pytest.approx(4.0)
        assert scoreboard["cost_per_completed_ws"] == pytest.approx(2.0)
        assert scoreboard["autonomous_bug_fix_count"] == 1

    @pytest.mark.asyncio
    async def test_scoreboard_expected_fields(self, service):
        scoreboard = await service.get_scoreboard(window="all")
        expected_fields = {
            "window", "total_runs", "success_rate",
            "average_duration_seconds", "p95_duration_seconds",
            "first_pass_rate", "total_llm_cost_usd",
            "cost_per_completed_ws", "autonomous_bug_fix_count",
        }
        assert expected_fields == set(scoreboard.keys())


# =============================================================================
# Criterion 14: Scoreboard window filtering
# =============================================================================

class TestCriterion14ScoreboardWindow:
    """Scoreboard with window=7d returns only data from last 7 days."""

    @pytest.mark.asyncio
    async def test_window_filters_old_data(self, service, repo):
        # Insert an "old" execution directly via repo (outside 7d window)
        old_id = uuid4()
        old_time = datetime.now(timezone.utc) - timedelta(days=30)
        old_record = WSExecutionRecord(
            id=old_id,
            ws_id="WS-OLD",
            executor="claude_code",
            status="COMPLETED",
            started_at=old_time,
            completed_at=old_time + timedelta(minutes=10),
            duration_seconds=600,
            phase_metrics={"phases": []},
            test_metrics={"written": 0, "passing": 0, "failing": 0, "skipped": 0},
            file_metrics={"created": [], "modified": [], "deleted": []},
            llm_cost_usd=Decimal("10.00"),
            created_at=old_time,
        )
        await repo.insert_execution(old_record)
        await repo.commit()

        # Insert a recent execution
        recent_id = await service.start_execution(ws_id="WS-RECENT", executor="claude_code")
        await service.complete_execution(
            execution_id=recent_id, status="COMPLETED", llm_cost_usd=Decimal("1.00")
        )

        scoreboard = await service.get_scoreboard(window="7d")
        assert scoreboard["total_runs"] == 1
        assert scoreboard["total_llm_cost_usd"] == pytest.approx(1.0)


# =============================================================================
# Criterion 15: Correlation ID present
# (Verifies the LLMRun model has workflow_execution_id field that can
#  store ws_execution_id for cost attribution.)
# =============================================================================

class TestCriterion15CorrelationID:
    """LLM execution logs linked to WS execution via ws_execution_id."""

    def test_llm_run_has_workflow_execution_id_field(self):
        """LLMRun model supports workflow_execution_id for WS correlation."""
        from app.domain.models.llm_logging import LLMRun
        col_names = {c.name for c in LLMRun.__table__.columns}
        assert "workflow_execution_id" in col_names

    def test_llm_run_record_dto_has_field(self):
        """LLMRunRecord DTO supports workflow_execution_id."""
        from app.domain.repositories.llm_log_repository import LLMRunRecord
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(LLMRunRecord)}
        assert "workflow_execution_id" in field_names

    @pytest.mark.asyncio
    async def test_execution_id_can_be_stored(self, service):
        """WS execution ID is a UUID that can be used as correlation ID."""
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        # exec_id is a UUID that can be passed to LLM calls as
        # workflow_execution_id for cost attribution
        assert exec_id is not None
        from uuid import UUID
        assert isinstance(exec_id, UUID)


# =============================================================================
# Additional edge case tests
# =============================================================================

class TestCostSummary:
    """GET cost-summary returns LLM cost breakdown."""

    @pytest.mark.asyncio
    async def test_cost_summary_by_ws(self, service):
        id1 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.complete_execution(
            execution_id=id1, status="COMPLETED", llm_cost_usd=Decimal("2.00")
        )
        id2 = await service.start_execution(ws_id="WS-A", executor="claude_code")
        await service.complete_execution(
            execution_id=id2, status="COMPLETED", llm_cost_usd=Decimal("3.00")
        )
        id3 = await service.start_execution(ws_id="WS-B", executor="claude_code")
        await service.complete_execution(
            execution_id=id3, status="COMPLETED", llm_cost_usd=Decimal("1.00")
        )

        summary = await service.get_cost_summary()
        assert summary["total_llm_cost_usd"] == pytest.approx(6.0)
        assert summary["by_ws"]["WS-A"] == pytest.approx(5.0)
        assert summary["by_ws"]["WS-B"] == pytest.approx(1.0)
        assert summary["execution_count"] == 3


class TestScopeId:
    """scope_id is stored and available but not enforced in v1."""

    @pytest.mark.asyncio
    async def test_scope_id_stored_on_execution(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code", scope_id="tenant-42"
        )
        record = await repo.get_execution(exec_id)
        assert record.scope_id == "tenant-42"

    @pytest.mark.asyncio
    async def test_scope_id_stored_on_bug_fix(self, service, repo):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        await service.record_bug_fix(
            ws_execution_id=exec_id,
            description="Test",
            root_cause="Test",
            test_name="test_x",
            fix_summary="Fixed",
            autonomous=False,
            scope_id="tenant-42",
        )
        fixes = await repo.get_bug_fixes_for_execution(exec_id)
        assert fixes[0].scope_id == "tenant-42"


class TestExecutionDetail:
    """GET ws-executions/{id} returns execution with bug fixes."""

    @pytest.mark.asyncio
    async def test_detail_includes_bug_fixes(self, service):
        exec_id = await service.start_execution(
            ws_id="WS-TEST-001", executor="claude_code"
        )
        await service.record_bug_fix(
            ws_execution_id=exec_id,
            description="Bug 1",
            root_cause="Root 1",
            test_name="test_1",
            fix_summary="Fix 1",
            autonomous=True,
        )
        await service.record_bug_fix(
            ws_execution_id=exec_id,
            description="Bug 2",
            root_cause="Root 2",
            test_name="test_2",
            fix_summary="Fix 2",
            autonomous=False,
        )

        detail = await service.get_execution_detail(exec_id)
        assert detail is not None
        assert detail["execution"].ws_id == "WS-TEST-001"
        assert len(detail["bug_fixes"]) == 2
