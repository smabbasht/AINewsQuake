import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

def export_to_csv():
    # Load env vars
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    # Fix for sqlalchemy connection string if needed for psycopg2 (pandas prefers psycopg2 usually)
    # But we installed asyncpg. Pandas needs a synchronous driver for read_sql usually, or we can use the async engine with run_sync.
    # Simpler: convert URL to psycopg2 if possible, or try to use what we have.
    # Our current URL in .env is postgresql+asyncpg://...
    # We should convert it to postgresql:// for standard sync connection if using default pandas/sqlalchemy sync.
    
    if "postgresql+asyncpg" in database_url:
        sync_db_url = database_url.replace("postgresql+asyncpg", "postgresql")
    else:
        sync_db_url = database_url

    print(f"Connecting to database...")
    try:
        # SQLAlchemy 2.0+ might need specific driver setup. 
        # Ensuring we have psycopg2 or similar. 'pip install psycopg2-binary' might be needed if not present.
        # Check if we have psycopg2
        import psycopg2
        engine = create_engine(sync_db_url)
    except ImportError:
        print("psycopg2 not found, trying default...")
        engine = create_engine(sync_db_url)
    except Exception as e:
        print(f"Error creating engine: {e}")
        return

    output_dir = "Exported Data from TimeScaleDB"
    
    tables = [
        "ai_news_events",
        "market_ticks",
        "news_impact_analysis"
    ]
    
    for table in tables:
        print(f"Exporting raw table: {table}...")
        try:
            # Chunk size for large tables
            chunksize = 100000
            offset = 0
            
            # Simple check for count
            count = pd.read_sql_query(f"SELECT COUNT(*) FROM {table}", engine).iloc[0,0]
            print(f"  - Found {count} rows")
            
            if count > 0:
                csv_path = os.path.join(output_dir, f"{table}.csv")
                # Write header first
                first = True
                for chunk in pd.read_sql_query(f"SELECT * FROM {table}", engine, chunksize=chunksize):
                    mode = 'w' if first else 'a'
                    header = first
                    chunk.to_csv(csv_path, mode=mode, header=header, index=False)
                    first = False
                    print(f"  - Wrote chunk of {len(chunk)} rows")
                print(f"✅ Exported {table} to {csv_path}")
            else:
                print(f"⚠️ Table {table} is empty")
                
        except Exception as e:
            print(f"❌ Failed to export {table}: {e}")

if __name__ == "__main__":
    export_to_csv()
