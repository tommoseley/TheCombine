#!/bin/bash
set -e

echo "🚀 Starting The Combine..."

# ============================================================
# STEP 1: Build DATABASE_URL from components
# App Runner injects secrets as env vars automatically
# ============================================================
echo "🔐 Configuring database connection..."

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ DB_PASSWORD not set (should be injected by App Runner)"
    exit 1
fi

export DATABASE_URL="postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "✅ Database URL configured"

# ============================================================
# STEP 2: Wait for database to be ready
# ============================================================
echo "⏳ Waiting for database..."

python3 << EOF
import time
import sys
from sqlalchemy import create_engine, text
import os

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print('❌ DATABASE_URL not set')
    sys.exit(1)

max_retries = 30
for i in range(max_retries):
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✅ Database is ready')
        break
    except Exception as e:
        if i == max_retries - 1:
            print(f'❌ Database connection failed after {max_retries} attempts: {e}')
            sys.exit(1)
        print(f'   Attempt {i+1}/{max_retries} - waiting...')
        time.sleep(2)
EOF

# ============================================================
# STEP 3: Initialize database tables
# ============================================================
echo "📦 Initializing database tables..."
python scripts/init_db.py

# ============================================================
# STEP 4: Seed data (idempotent)
# ============================================================
echo "🌱 Seeding data..."
python scripts/seed_data.py

# ============================================================
# STEP 5: Start server
# ============================================================
echo "✅ Initialization complete"
echo "🚀 Starting uvicorn..."

exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
