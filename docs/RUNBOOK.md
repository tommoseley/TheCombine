# Operations Runbook

## Health Monitoring

### Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Liveness probe | `{"status": "healthy"}` |
| `GET /health/ready` | Readiness probe | `{"status": "ready", "database": "connected"}` |
| `GET /health/detailed` | Debug info | Full system status |

### Health Check Commands

```bash
# Quick liveness check
curl -f http://localhost:8000/health

# Readiness with database
curl http://localhost:8000/health/ready

# Full details
curl http://localhost:8000/health/detailed | jq .
```

## Common Issues

### Database Connection Failed

**Symptoms:**
- `/health/ready` returns 503
- `"database": "disconnected"` in response

**Diagnosis:**
```bash
# Check database container
docker-compose ps db
docker-compose logs db

# Test connection directly
docker-compose exec db psql -U combine -d combine -c "SELECT 1"

# Check connection string
echo $DATABASE_URL
```

**Resolution:**
1. Verify database is running
2. Check DATABASE_URL format
3. Verify network connectivity
4. Check credentials

### Application Won't Start

**Symptoms:**
- Container exits immediately
- `EnvironmentError` in logs

**Diagnosis:**
```bash
# Check logs
docker-compose logs app

# Verify required env vars
docker-compose exec app env | grep -E "(DATABASE|SECRET)"
```

**Resolution:**
1. Set missing environment variables
2. Verify `.env` file is loaded
3. Check variable format (no quotes issues)

### OAuth Login Fails

**Symptoms:**
- Redirect to error page after OAuth
- "Invalid client" error

**Diagnosis:**
```bash
# Check OAuth config
echo $GOOGLE_CLIENT_ID
echo $MICROSOFT_CLIENT_ID
```

**Resolution:**
1. Verify client ID/secret are correct
2. Check redirect URIs in provider console
3. Verify ALLOWED_ORIGINS includes your domain

### High Memory Usage

**Symptoms:**
- OOM kills
- Slow responses

**Diagnosis:**
```bash
# Check container resources
docker stats

# Check for memory leaks in logs
docker-compose logs app | grep -i memory
```

**Resolution:**
1. Increase memory limits in docker-compose
2. Check for connection leaks
3. Review recent code changes

### Slow API Responses

**Symptoms:**
- Timeouts
- High latency

**Diagnosis:**
```bash
# Check database performance
docker-compose exec db psql -U combine -d combine -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE state = 'active' AND now() - query_start > interval '5 seconds';
"

# Check logs for slow queries
docker-compose logs app | grep -i "slow\|timeout"
```

**Resolution:**
1. Check database indexes
2. Review N+1 query issues
3. Check LLM API latency

## Maintenance Procedures

### Database Migrations

```bash
# Run pending migrations
docker-compose exec app alembic upgrade head

# Check current version
docker-compose exec app alembic current

# Rollback one version
docker-compose exec app alembic downgrade -1
```

### Log Management

```bash
# View recent logs
docker-compose logs --tail=100 app

# Follow logs
docker-compose logs -f app

# Export logs
docker-compose logs app > app.log
```

### Backup Database

```bash
# Backup
docker-compose exec db pg_dump -U combine combine > backup.sql

# Restore
docker-compose exec -T db psql -U combine combine < backup.sql
```

## Rollback Procedure

1. Stop current deployment
   ```bash
   docker-compose down
   ```

2. Switch to previous version
   ```bash
   git checkout <previous-tag>
   ```

3. Deploy
   ```bash
   docker-compose up -d
   ```

4. Verify health
   ```bash
   curl http://localhost:8000/health/ready
   ```

5. Rollback database if needed
   ```bash
   docker-compose exec app alembic downgrade -1
   ```

## Scaling

### Horizontal Scaling

```bash
# Scale app instances
docker-compose up -d --scale app=3
```

Note: Requires load balancer configuration.

### Resource Limits

In `docker-compose.staging.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
```

## Contacts

| Role | Contact |
|------|---------|
| On-call | TBD |
| Database | TBD |
| Infrastructure | TBD |