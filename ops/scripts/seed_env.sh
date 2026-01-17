#!/bin/bash
# Seed database for specified environment
# Usage: ./seed_env.sh [dev|prod|both]

# Load your actual connection strings here
DEV_DATABASE_URL="postgresql://combine_user:password@localhost:5432/combine"
PROD_DATABASE_URL=""  # Fill in your prod connection string

seed_database() {
    local env=$1
    local url=$2

    echo "=========================================="
    echo "Seeding $env database..."
    echo "=========================================="

    DATABASE_URL="$url" python3 ops/db/setup.py

    if [ $? -eq 0 ]; then
        echo "✓ $env seeding complete"
    else
        echo "✗ $env seeding failed"
        exit 1
    fi
}

case "${1:-dev}" in
    dev)
        seed_database "DEV" "$DEV_DATABASE_URL"
        ;;
    prod)
        if [ -z "$PROD_DATABASE_URL" ]; then
            echo "Error: PROD_DATABASE_URL not configured in script"
            exit 1
        fi
        read -p "Seed PRODUCTION database? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            seed_database "PROD" "$PROD_DATABASE_URL"
        else
            echo "Aborted"
        fi
        ;;
    both)
        seed_database "DEV" "$DEV_DATABASE_URL"
        echo ""
        if [ -z "$PROD_DATABASE_URL" ]; then
            echo "Error: PROD_DATABASE_URL not configured in script"
            exit 1
        fi
        read -p "Now seed PRODUCTION? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            seed_database "PROD" "$PROD_DATABASE_URL"
        else
            echo "Skipped prod"
        fi
        ;;
    *)
        echo "Usage: $0 [dev|prod|both]"
        exit 1
        ;;
esac
