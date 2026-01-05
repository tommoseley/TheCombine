# Staging Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Access to staging secrets (see Required Secrets below)
- PostgreSQL database provisioned (or use docker-compose)

## Required Secrets

Set these environment variables before deployment:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/combine
POSTGRES_PASSWORD=<secure-password>

# Application
SECRET_KEY=<32-byte-hex-string>
ANTHROPIC_API_KEY=sk-ant-...

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
```

Generate a secret key:
```bash
openssl rand -hex 32
```

## Deployment Steps

### 1. Clone and Configure

```bash
git clone <repo-url>
cd the-combine
cp .env.example .env
# Edit .env with staging values
```

### 2. Deploy with Docker Compose

```bash
# Build and start
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# View logs
docker-compose logs -f app
```

### 3. Run Database Migrations

```bash
# Run migrations
docker-compose exec app alembic upgrade head

# Verify
curl http://localhost:8000/health/detailed
```

### 4. Verify Deployment

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/detailed

# API docs
open http://localhost:8000/docs
```

## Health Endpoints

| Endpoint | Purpose | Use For |
|----------|---------|---------|
| `/health` | Liveness | Container liveness probe |
| `/health/ready` | Readiness | Container readiness probe |
| `/health/detailed` | Debug | Manual inspection |

## Logging

Staging uses JSON logging for aggregation:

```json
{
  "timestamp": "2026-01-04T12:00:00Z",
  "level": "INFO",
  "logger": "app.api.main",
  "message": "Request processed",
  "request_id": "abc123"
}
```

View logs:
```bash
docker-compose logs -f app | jq .
```

## Troubleshooting

### Database Connection Failed
```bash
# Check database is running
docker-compose ps db
docker-compose logs db

# Test connection
docker-compose exec db psql -U combine -d combine -c "SELECT 1"
```

### App Not Starting
```bash
# Check logs
docker-compose logs app

# Check environment
docker-compose exec app env | grep -E "(DATABASE|SECRET|API)"
```

### OAuth Not Working
1. Verify redirect URIs in Google/Microsoft console
2. Check ALLOWED_ORIGINS includes your staging domain
3. Verify client ID/secret are set

## Scaling

For horizontal scaling:
```bash
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d --scale app=3
```

Note: Requires load balancer in front.

## Rollback

```bash
# Stop current
docker-compose down

# Deploy previous version
git checkout <previous-tag>
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```
