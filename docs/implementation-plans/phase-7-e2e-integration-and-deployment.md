# Phase 7: End-to-End Integration & Production Deployment

## Overview

Phase 7 integrates all components into a working end-to-end system and prepares for AWS production deployment. This phase validates the complete pipeline from user request through LLM execution to document persistence.

## Goals

1. **End-to-End Integration**: Wire LLM module into workflow executor
2. **Strategy Workflow**: First complete production line
3. **AWS Deployment**: ECS Fargate with PostgreSQL RDS
4. **Observability**: Structured logging, health checks, metrics
5. **Error Recovery**: Graceful degradation, retry policies

## Timeline: 5 Days

| Day | Focus | Estimated Tests |
|-----|-------|-----------------|
| 1 | LLM Step Executor integration | 12 |
| 2 | Strategy workflow definition | 10 |
| 3 | AWS infrastructure (Terraform) | 5 |
| 4 | Observability and monitoring | 10 |
| 5 | Integration tests and smoke tests | 15 |
| **Total** | | **~52** |

**Target: 665 tests (613 + 52)**

---

## Day 1: LLM Step Executor Integration

### Deliverables

1. **LLMStepExecutor** - Wires LLM module into step execution

`python
class LLMStepExecutor:
    def __init__(
        self,
        llm_provider: LLMProvider,
        prompt_builder: PromptBuilder,
        output_parser: OutputParser,
        telemetry: TelemetryService,
        document_repo: DocumentRepository,
    ): ...
    
    async def execute(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
    ) -> StepResult:
        # 1. Build prompts
        # 2. Call LLM with retry
        # 3. Log telemetry
        # 4. Parse and validate output
        # 5. Handle clarification or save document
        ...
`

2. **ExecutionContext Integration** - Enhanced context with persistence
3. **Provider Factory** - Create appropriate LLM provider based on settings

### Tests (12)
- LLMStepExecutor complete flow
- Clarification handling
- Validation failure handling
- Telemetry recording
- Document persistence
- Retry on transient errors

---

## Day 2: Strategy Workflow Definition

### Deliverables

1. **Strategy Workflow JSON** (seed/workflows/strategy-document.json)

`json
{
  "workflow_id": "strategy-document",
  "name": "Strategy Document",
  "version": "1.0",
  "steps": [
    {
      "step_id": "discovery",
      "role": "PM",
      "inputs": [],
      "outputs": ["project-discovery"]
    },
    {
      "step_id": "requirements",
      "role": "BA",
      "inputs": ["project-discovery"],
      "outputs": ["requirements-doc"]
    },
    {
      "step_id": "architecture",
      "role": "Architect",
      "inputs": ["project-discovery", "requirements-doc"],
      "outputs": ["architecture-doc"]
    },
    {
      "step_id": "review",
      "role": "QA",
      "inputs": ["project-discovery", "requirements-doc", "architecture-doc"],
      "outputs": ["strategy-review"],
      "is_final": true
    }
  ]
}
`

2. **Task Prompts** (seed/prompts/tasks/)
3. **Output Schemas** (seed/schemas/)

### Tests (10)
- Workflow JSON validation
- Step dependency resolution
- Input/output mapping
- Schema validation per step
- End-to-end with mock LLM

---

## Day 3: AWS Infrastructure

### Deliverables

1. **ECS Fargate Service** (terraform/ecs.tf)
   - Task definition with container config
   - Service with desired count 2
   - Load balancer integration

2. **RDS PostgreSQL** (terraform/rds.tf)
   - db.t3.medium instance
   - Multi-AZ for high availability
   - Encrypted storage
   - 7-day backup retention

3. **Secrets Manager** (terraform/secrets.tf)
   - Anthropic API key
   - Database credentials
   - OAuth client secrets

4. **ALB with HTTPS** (terraform/alb.tf)
   - SSL certificate via ACM
   - Health check configuration
   - Target group routing

### Tests (5)
- Health check endpoint responds
- Database connectivity
- Secrets retrieval
- Container startup
- ALB routing

---

## Day 4: Observability & Monitoring

### Deliverables

1. **Structured Logging** (app/observability/logging.py)

`python
import structlog

def configure_logging(settings: Settings):
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )
`

2. **Metrics Collection** (app/observability/metrics.py)

`python
@dataclass
class ExecutionMetrics:
    executions_started: int = 0
    executions_completed: int = 0
    executions_failed: int = 0
    llm_calls_total: int = 0
    total_tokens_used: int = 0
    total_cost_usd: Decimal = Decimal("0")
`

3. **Health Check Enhancements**
   - Database connectivity check
   - Anthropic API check
   - Secrets accessibility check

4. **CloudWatch Integration** (app/observability/cloudwatch.py)

### Tests (10)
- Structured log format
- Metrics recording
- Health check aggregation
- CloudWatch metric formatting
- Log correlation IDs

---

## Day 5: Integration & Smoke Tests

### Deliverables

1. **End-to-End Integration Tests** (tests/integration/test_e2e_workflow.py)
   - Complete workflow execution with mock LLM
   - Workflow pauses for clarification
   - QA gate rejects and triggers remediation
   - Documents persist correctly

2. **API Integration Tests** (tests/integration/test_api_integration.py)
   - Start execution with valid session
   - Status endpoint reflects progress
   - Document retrieval works

3. **Smoke Tests** (tests/smoke/test_production_smoke.py)
   - Health endpoint returns healthy
   - OAuth flow works
   - API returns correct version

4. **Load Test Script** (scripts/load_test.py)

### Tests (15)
- E2E workflow completion
- Clarification flow
- QA rejection/remediation
- Document persistence verification
- API authentication
- Concurrent execution
- Error recovery

---

## File Structure

`
app/
  execution/
    llm_step_executor.py    # LLM-integrated executor
    context.py              # Enhanced execution context
  observability/
    logging.py              # Structured logging
    metrics.py              # Metrics collection
    cloudwatch.py           # AWS CloudWatch integration

terraform/
  main.tf, ecs.tf, rds.tf, alb.tf, secrets.tf

seed/
  workflows/strategy-document.json
  prompts/tasks/strategy-*.txt
  schemas/strategy/*.json

tests/
  integration/test_e2e_workflow.py, test_api_integration.py
  smoke/test_production_smoke.py
`

---

## Configuration Additions

`python
@dataclass
class Settings:
    # LLM
    anthropic_api_key: str = ""
    llm_default_model: str = "claude-sonnet-4-20250514"
    llm_enable_caching: bool = True
    llm_max_retries: int = 3
    
    # AWS
    aws_region: str = "us-east-1"
    cloudwatch_namespace: str = "TheCombine"
    
    # Observability
    log_format: str = "json"
    enable_metrics: bool = True
`

---

## Deployment Checklist

- [ ] Terraform state backend (S3 + DynamoDB)
- [ ] VPC with public/private subnets
- [ ] ECS cluster and service
- [ ] RDS PostgreSQL instance
- [ ] Secrets in Secrets Manager
- [ ] ALB with SSL certificate
- [ ] Route 53 DNS record
- [ ] CloudWatch log groups and alarms
- [ ] IAM roles and policies

---

## Success Criteria

1. Strategy workflow executes end-to-end with mock LLM
2. Documents persist to PostgreSQL correctly
3. Health checks pass in deployed environment
4. Structured logs flow to CloudWatch
5. Metrics visible in CloudWatch dashboard
6. 665+ tests passing

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM API outage | Graceful degradation, clear error messages |
| Database connection exhaustion | Connection pooling, health checks |
| Cost overruns | Budget alerts, usage monitoring |
| Cold start latency | Keep-alive requests, min capacity |
| Secret rotation | Automatic rotation, cached retrieval |
