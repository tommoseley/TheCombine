# Configuration Reference

This document describes all environment variables used by The Combine.

## Required Variables

These must be set in all environments (except test).

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Session encryption key (32+ bytes hex) | `openssl rand -hex 32` |

## Environment-Specific Requirements

### Staging

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM calls |

### Production

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM calls |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

## Optional Variables

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment type: development, staging, production, test |
| `DEBUG` | `false` | Enable debug mode |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | `text` | Log format: text (human), json (structured) |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | `10` | Connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Max overflow connections |

### OAuth

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `MICROSOFT_CLIENT_ID` | Microsoft OAuth client ID |
| `MICROSOFT_CLIENT_SECRET` | Microsoft OAuth client secret |

### LLM Pricing

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_INPUT_PRICE_PER_MTK` | `3.0` | Input token price per million |
| `ANTHROPIC_OUTPUT_PRICE_PER_MTK` | `15.0` | Output token price per million |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | - | CORS allowed origins (comma-separated) |
| `MAX_REQUEST_BODY_SIZE` | `10485760` | Max request body size (10MB) |

## Generating Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate secure password
openssl rand -base64 24
```

## Environment Detection

The application detects its environment in this order:

1. `ENVIRONMENT` environment variable
2. Pytest detection (sets to `test`)
3. Default: `development`

## Validation

On startup, the application validates:

1. All required variables are set
2. Environment-specific variables are present
3. Warnings for recommended but missing variables

In development, missing variables generate warnings.
In staging/production, missing required variables fail startup.

## Sensitive Variables

These variables are masked in logs:

- `SECRET_KEY`
- `DATABASE_URL`
- `ANTHROPIC_API_KEY`
- `GOOGLE_CLIENT_SECRET`
- `MICROSOFT_CLIENT_SECRET`
- `POSTGRES_PASSWORD`