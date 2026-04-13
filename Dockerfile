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

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
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
