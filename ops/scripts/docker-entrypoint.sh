#!/bin/bash
# The Combine - Docker Entrypoint Script
# Waits for database, runs migrations, starts the application
set -e

echo "=================================================="
echo "The Combine - Starting Application"
echo "=================================================="

# Step 1: Wait for database to be ready
echo ""
echo "Waiting for database..."

for i in $(seq 1 30); do
    if pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-combine}" -q 2>/dev/null; then
        echo "Database is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Database connection failed after 30 attempts"
        exit 1
    fi
    echo "  Attempt $i/30 - waiting..."
    sleep 2
done

# Step 2: Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head
echo "Migrations completed"

# Step 3: Start the application
echo ""
echo "Starting FastAPI server on port ${PORT:-8000}..."
echo "=================================================="
echo ""

exec uvicorn app.api.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --proxy-headers \
    --forwarded-allow-ips "*" \
    "$@"
