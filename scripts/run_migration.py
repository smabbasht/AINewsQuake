"""
Run database migration to create news_impact_analysis table.
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment
load_dotenv()

def run_migration():
    """Execute the migration SQL script."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)
    
    # Convert asyncpg URL to psycopg2 URL
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Read migration file
    migration_file = Path(__file__).parent.parent / "migrations" / "002_create_impact_analysis.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Execute migration
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("🔄 Running migration: 002_create_impact_analysis.sql")
        cursor.execute(sql)
        
        print("✅ Migration completed successfully!")
        print("📊 Table 'news_impact_analysis' created with indexes")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
