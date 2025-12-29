#!/bin/bash
# The Combine - Docker Entrypoint Script
# Runs migrations, seeds data (if needed), and starts the application

set -e  # Exit on any error

echo "=================================================="
echo "🚀 The Combine - Starting Application"
echo "=================================================="

# Step 1: Run database migrations
echo ""
echo "📊 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed!"
    exit 1
fi

# Step 2: Seed initial data (optional)
# Uncomment if you have a seed script
# echo ""
# echo "🌱 Seeding initial data..."
# python scripts/seed_data.py

# Step 3: Start the application
echo ""
echo "🌐 Starting FastAPI server..."
echo "   Host: 0.0.0.0"
echo "   Port: ${PORT:-8000}"
echo "=================================================="
echo ""

exec uvicorn app.api.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --log-level info