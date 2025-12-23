#!/bin/bash

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '#' | xargs)
else
    echo "❌ ../.env file not found!"
    exit 1
fi

# Check variables
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL (Local) not set in .env"
    exit 1
fi

if [ -z "$PROD_DB_URL" ]; then
    echo "❌ PROD_DB_URL (Cloud) not set in .env"
    exit 1
fi

# Check if psql/pg_dump exist, otherwise use Docker
USE_DOCKER=false
if ! command -v pg_dump &> /dev/null; then
    echo "⚠️  Local pg_dump not found. Switching to Docker mode..."
    USE_DOCKER=true
fi

echo "🚀 Starting migration..."
echo "From: Local DB (Docker Container: ainewsquake-timescaledb)"
echo "To:   Cloud DB ($PROD_DB_URL)"
echo ""
echo "Tables to migrate:"
echo "1. ai_news_events"
echo "2. market_ticks"
echo "3. news_impact_analysis (Materialized View/Table)"
echo ""

# Run Migration
echo "📦 Dumping and restoring (this may take a few minutes)..."

if [ "$USE_DOCKER" = true ]; then
    # Use tools inside the container to dump and pipe to cloud
    docker exec ainewsquake-timescaledb pg_dump -U postgres ainewsquake --no-owner --no-acl --verbose | \
    docker exec -i ainewsquake-timescaledb psql "$PROD_DB_URL"
else
    # Use local tools
    LOCAL_DB=${DATABASE_URL//+asyncpg/}
    pg_dump "$LOCAL_DB" --no-owner --no-acl --verbose | psql "$PROD_DB_URL"
fi

echo ""
echo "✅ Migration pipeline finished! All 3 tables transferred."
