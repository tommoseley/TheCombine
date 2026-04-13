# The Combine - Production Dockerfile
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (postgresql-client for pg_isready in entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# --- Builder stage ---
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --target=/app/deps -r requirements.txt

# --- Production stage ---
FROM base AS production

# Copy dependencies from builder
COPY --from=builder /app/deps /app/deps
ENV PYTHONPATH=/app/deps \
    USE_WORKFLOW_ENGINE_LLM=true

# Copy application code, configuration, SPA build, alembic, and schema bootstrap
COPY app/ /app/app/
COPY combine-config/ /app/combine-config/
COPY spa/dist/ /app/spa/dist/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY ops/db/schema.sql /app/schema.sql

# Create entrypoint script (ops/ is in .dockerignore)
RUN cat > /app/entrypoint.sh << 'ENTRY'
#!/bin/bash
set -e
echo "The Combine - Starting"

# Parse DB host from DATABASE_URL (or fall back to env vars)
if [ -n "${DATABASE_URL:-}" ]; then
    DB_HOST_PARSED=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:/]*\).*|\1|p')
    DB_PORT_PARSED=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
fi
_DB_HOST="${DB_HOST:-${DB_HOST_PARSED:-localhost}}"
_DB_PORT="${DB_PORT:-${DB_PORT_PARSED:-5432}}"

# Wait for database
for i in $(seq 1 30); do
    if pg_isready -h "$_DB_HOST" -p "$_DB_PORT" -q 2>/dev/null; then
        echo "Database is ready ($_DB_HOST:$_DB_PORT)"
        break
    fi
    [ "$i" -eq 30 ] && echo "Database connection failed" && exit 1
    echo "  Waiting for database ($i/30)..."
    sleep 2
done

# Bootstrap or migrate
DB_URL="${DATABASE_URL:-postgresql://${DB_USER:-combine}:${DB_PASS:-combine}@${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-combine}}"
# Convert async URL to sync for psql
SYNC_URL=$(echo "$DB_URL" | sed 's|postgresql+asyncpg://|postgresql://|')

TABLE_COUNT=$(psql "$SYNC_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$TABLE_COUNT" = "0" ] || [ -z "$TABLE_COUNT" ]; then
    echo "Empty database — bootstrapping from schema.sql..."
    psql "$SYNC_URL" -f /app/schema.sql -q 2>&1 | head -5 || true
    echo "Schema loaded — stamping alembic to head"
    python -m alembic stamp head
else
    echo "Running migrations..."
    python -m alembic upgrade head
fi
echo "Database ready"

# Start app (pass through any extra args like --reload)
echo "Starting uvicorn..."
exec python -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips "*" "$@"
ENTRY
RUN chmod +x /app/entrypoint.sh

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Use entrypoint (waits for DB, runs migrations, starts uvicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
