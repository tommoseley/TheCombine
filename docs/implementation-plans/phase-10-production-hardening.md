# Phase 10: Production Hardening for Staging

## Overview

Phase 10 prepares The Combine for staging deployment with structured logging, environment configuration, deployment documentation, and operational readiness tests.

## Goals

1. **Structured Logging**: JSON logging for log aggregation
2. **Environment Configuration**: Clean separation of dev/staging/prod
3. **Deployment Artifacts**: Docker Compose for staging, deployment guide
4. **Operational Tests**: Health checks, configuration validation
5. **Security Baseline**: Environment variable validation, no secrets in code

## Timeline: 3 Days

| Day | Focus | Estimated Tests |
|-----|-------|-----------------|
| 1 | Structured logging + config | 10 |
| 2 | Health checks + operational tests | 8 |
| 3 | Integration verification + docs | 6 |
| **Total** | | **~24** |

**Target: 877 tests (853 + 24)**

---

## Day 1: Structured Logging & Configuration (PARTIALLY COMPLETE)

### Completed
- [x] `app/core/logging.py` - JSONFormatter, TextFormatter, configure_logging
- [x] `.env.example` - Document all required variables
- [x] `docker-compose.staging.yml` - Staging overrides
- [x] `tests/core/test_logging.py` - 10 tests

### Remaining

1. **Environment Configuration Class**

```python
# app/core/environment.py
class Environment:
    """Environment-aware configuration."""
    
    @classmethod
    def current(cls) -> str:
        """Get current environment (development/staging/production)."""
        ...
    
    @classmethod
    def is_production(cls) -> bool:
        ...
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate all required env vars are set. Returns missing vars."""
        ...
```

2. **Startup Validation**
   - Validate required environment variables on startup
   - Fail fast with clear error messages
   - Log configuration (sanitized) on startup

### Tests (Day 1 Remaining)
- Environment detection works
- Required var validation catches missing vars
- Sanitized config logging (no secrets)

---

## Day 2: Health Checks & Operational Tests

### Deliverables

1. **Enhanced Health Checks** (already have basic ones)

```python
# Additions to app/api/routers/health.py

@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}

@router.get("/health/startup")
async def startup_check():
    """Kubernetes startup probe - heavier checks."""
    # Check DB migrations are current
    # Check required services reachable
    ...
```

2. **Metrics Endpoint** (optional but useful)

```python
# app/api/routers/metrics.py
@router.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics."""
    return {
        "uptime_seconds": ...,
        "request_count": ...,
        "error_count": ...,
        "db_pool_size": ...,
    }
```

3. **Operational Test Suite**

```python
# tests/operational/test_health.py
class TestHealthEndpoints:
    def test_liveness_always_succeeds(self):
        """Liveness returns 200 even if DB down."""
        ...
    
    def test_readiness_checks_database(self):
        """Readiness fails if DB unreachable."""
        ...

# tests/operational/test_startup.py
class TestStartupValidation:
    def test_missing_database_url_fails(self):
        """App fails to start without DATABASE_URL."""
        ...
    
    def test_missing_secret_key_fails(self):
        """App fails to start without SECRET_KEY."""
        ...
```

### Tests (Day 2)
- Liveness always returns 200
- Readiness checks database
- Startup probe validates migrations
- Missing required vars fail startup
- Metrics endpoint returns data
- Health detailed shows versions

---

## Day 3: Integration Verification & Documentation

### Deliverables

1. **Docker Build Verification**

```python
# tests/operational/test_docker.py
class TestDockerBuild:
    def test_dockerfile_syntax_valid(self):
        """Dockerfile parses correctly."""
        ...
    
    def test_compose_syntax_valid(self):
        """docker-compose files are valid YAML."""
        ...
```

2. **Configuration Documentation**

```markdown
# docs/CONFIGURATION.md
- All environment variables documented
- Required vs optional clearly marked
- Default values listed
- Example values provided
```

3. **Runbook Updates**

```markdown
# docs/RUNBOOK.md
- Common failure scenarios
- How to diagnose issues
- How to rollback
- Contact/escalation info
```

4. **Pre-deployment Checklist**

```markdown
# docs/DEPLOYMENT-CHECKLIST.md
[ ] All required env vars set
[ ] Database migrations run
[ ] Health check passes
[ ] OAuth redirect URIs configured
[ ] Log aggregation configured
[ ] Alerts configured
```

### Tests (Day 3)
- Docker compose files valid YAML
- All documented env vars exist in .env.example
- Health endpoints return expected format
- API docs accessible

---

## Files to Create/Modify

### New Files
```
app/core/environment.py          - Environment detection & validation
app/api/routers/metrics.py       - Metrics endpoint (optional)
tests/operational/__init__.py
tests/operational/test_health.py
tests/operational/test_startup.py
tests/operational/test_docker.py
docs/CONFIGURATION.md
docs/RUNBOOK.md
docs/DEPLOYMENT-CHECKLIST.md
```

### Modified Files
```
app/core/logging.py              - Already created
app/api/routers/health.py        - Add startup probe
app/api/main.py                  - Add startup validation
.env.example                     - Already created
docker-compose.staging.yml       - Already created
docs/STAGING-DEPLOYMENT.md       - Already created
```

---

## Success Criteria

1. **Logging**: JSON logs parseable by jq
2. **Configuration**: Clear errors for missing required vars
3. **Health**: All probes return appropriate status
4. **Documentation**: Complete deployment guide
5. **Tests**: 877+ tests passing

---

## Staging Deployment Readiness Checklist

After Phase 10:

- [x] OAuth implemented (Google, Microsoft)
- [x] Health endpoints (/health, /health/ready, /health/detailed)
- [x] Dockerfile with health check
- [x] docker-compose.yml for development
- [ ] docker-compose.staging.yml validated
- [ ] Structured JSON logging
- [ ] Environment validation on startup
- [ ] .env.example with all variables
- [ ] Deployment documentation
- [ ] 877+ tests passing

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Missing env vars in staging | Startup validation fails fast |
| Log parsing issues | JSON format tested |
| Health check false positives | Separate liveness/readiness |
| Config drift between envs | Single .env.example source |

---

## Post-Phase 10

With Phase 10 complete, staging deployment requires:

1. Provision PostgreSQL database
2. Set environment variables
3. Run `docker-compose -f docker-compose.yml -f docker-compose.staging.yml up`
4. Run migrations: `alembic upgrade head`
5. Verify health: `curl /health/ready`

Future phases could add:
- Phase 11: Monitoring & Alerting (Prometheus, Grafana)
- Phase 12: CI/CD Pipeline
- Phase 13: Production deployment
