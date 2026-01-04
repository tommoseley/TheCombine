# Deployment Checklist

Use this checklist before each staging/production deployment.

## Pre-Deployment

### Environment Variables
- [ ] DATABASE_URL is set and tested
- [ ] SECRET_KEY is set (32+ bytes, unique per environment)
- [ ] ANTHROPIC_API_KEY is set
- [ ] ENVIRONMENT is set correctly (staging/production)
- [ ] LOG_FORMAT=json for structured logging
- [ ] LOG_LEVEL is appropriate (INFO for production)

### OAuth Configuration
- [ ] GOOGLE_CLIENT_ID is set
- [ ] GOOGLE_CLIENT_SECRET is set
- [ ] MICROSOFT_CLIENT_ID is set (if used)
- [ ] MICROSOFT_CLIENT_SECRET is set (if used)
- [ ] Redirect URIs configured in OAuth provider consoles

### Database
- [ ] Database is provisioned and accessible
- [ ] Connection string is correct
- [ ] Database user has required permissions
- [ ] Migrations are ready to run

### Infrastructure
- [ ] Docker images built and pushed
- [ ] docker-compose files validated
- [ ] Resource limits configured
- [ ] Health check endpoints configured

## Deployment

### Build
- [ ] `docker-compose build` succeeds
- [ ] No build warnings or errors

### Deploy
- [ ] `docker-compose up -d` succeeds
- [ ] All containers start without errors
- [ ] No crash loops

### Migrations
- [ ] `alembic upgrade head` succeeds
- [ ] Migration version matches expected

## Post-Deployment Verification

### Health Checks
- [ ] `GET /health` returns 200
- [ ] `GET /health/ready` returns 200 with database connected
- [ ] `GET /health/detailed` shows all services healthy

### Functional Tests
- [ ] Homepage loads
- [ ] OAuth login works (Google)
- [ ] OAuth login works (Microsoft) - if configured
- [ ] API endpoints respond
- [ ] WebSocket/SSE connections work

### Monitoring
- [ ] Logs are being captured
- [ ] JSON log format parses correctly
- [ ] No errors in logs
- [ ] Metrics are being collected (if applicable)

### Performance
- [ ] Response times are acceptable
- [ ] No memory leaks observed
- [ ] CPU usage is stable

## Rollback Plan

If issues are detected:

1. [ ] Stop deployment: `docker-compose down`
2. [ ] Checkout previous version: `git checkout <tag>`
3. [ ] Redeploy: `docker-compose up -d`
4. [ ] Rollback migrations if needed: `alembic downgrade -1`
5. [ ] Verify health: `curl /health/ready`
6. [ ] Notify team of rollback

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Deployer | | | |
| Reviewer | | | |

## Notes

_Add any deployment-specific notes here:_

---

**Deployment Version:** _____________

**Deployment Date:** _____________

**Deployment Time:** _____________