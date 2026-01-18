"""
Retry impact analysis with batched inserts to avoid timeout.
Only processes events that don't already have impact analysis.
"""
import os
import sys
from datetime import timedelta
from typing import Optional

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


def get_db_connection():
    """Get database connection."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)
    
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(database_url)


def load_news_events_without_impact(conn) -> pd.DataFrame:
    """Load news events that don't have impact analysis yet."""
    query = """
        SELECT 
            e.event_id,
            e.ticker,
            e.published_at,
            e.headline,
            e.sentiment_score,
            e.source
        FROM ai_news_events e
        LEFT JOIN news_impact_analysis i ON e.event_id = i.event_id
        WHERE i.event_id IS NULL
        ORDER BY e.published_at
    """
    
    print("📰 Loading news events without impact analysis...")
    df = pd.read_sql_query(query, conn)
    df['published_at'] = pd.to_datetime(df['published_at'])
    print(f"✅ Found {len(df):,} events needing analysis")
    return df


def load_market_ticks(conn) -> pd.DataFrame:
    """Load all market ticks from database."""
    query = """
        SELECT 
            time,
            ticker,
            open,
            high,
            low,
            close,
            volume
        FROM market_ticks
        ORDER BY time
    """
    
    print("📈 Loading market ticks...")
    df = pd.read_sql_query(query, conn)
    df['time'] = pd.to_datetime(df['time'])
    print(f"✅ Loaded {len(df):,} market ticks")
    return df


def calculate_impact_for_event(news_row: pd.Series, market_df: pd.DataFrame) -> Optional[dict]:
    """Calculate impact metrics for a single news event."""
    published_at = news_row['published_at']
    
    market_after = market_df[market_df['time'] >= published_at]
    if market_after.empty:
        return None
    
    reaction_start_tick = market_after.iloc[0]
    reaction_start_time = reaction_start_tick['time']
    
    market_before = market_df[market_df['time'] < published_at]
    if market_before.empty:
        return None
        
    price_at_news_tick = market_before.iloc[-1]
    price_at_news = price_at_news_tick['close']
    volume_at_news = price_at_news_tick['volume']
    
    baseline_data = market_before.tail(120)
    volume_baseline_avg = baseline_data['volume'].mean()

    window_end = reaction_start_time + timedelta(minutes=30)
    window_data = market_df[
        (market_df['time'] >= reaction_start_time) &
        (market_df['time'] <= window_end)
    ]
    
    if window_data.empty:
        return None
    
    price_30min_after = window_data.iloc[-1]['close']
    volume_30min_total = window_data['volume'].sum()
    high_30min = window_data['high'].max()
    low_30min = window_data['low'].min()
    
    price_impact_pct = ((price_30min_after - price_at_news) / price_at_news) * 100
    
    if volume_baseline_avg and volume_baseline_avg > 0:
        expected_volume = volume_baseline_avg * 30
        volume_spike_ratio = volume_30min_total / expected_volume
    else:
        volume_spike_ratio = None
    
    volatility_impact_pct = ((high_30min - low_30min) / price_at_news) * 100
    
    return {
        'event_id': news_row['event_id'],
        'ticker': news_row['ticker'],
        'published_at': published_at,
        'headline': news_row['headline'],
        'sentiment_score': news_row['sentiment_score'],
        'source': news_row['source'],
        'price_at_news': price_at_news,
        'volume_at_news': volume_at_news,
        'price_30min_after': price_30min_after,
        'price_impact_pct': price_impact_pct,
        'volume_30min_total': volume_30min_total,
        'volume_baseline_avg': volume_baseline_avg,
        'volume_spike_ratio': volume_spike_ratio,
        'high_30min': high_30min,
        'low_30min': low_30min,
        'volatility_impact_pct': volatility_impact_pct,
    }


def insert_impact_batch(conn, records):
    """Insert a batch of impact analysis records."""
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO news_impact_analysis (
            event_id, ticker, published_at, headline, sentiment_score, source,
            price_at_news, volume_at_news,
            price_30min_after, price_impact_pct,
            volume_30min_total, volume_baseline_avg, volume_spike_ratio,
            high_30min, low_30min, volatility_impact_pct
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (event_id) DO UPDATE SET
            price_impact_pct = EXCLUDED.price_impact_pct,
            volume_spike_ratio = EXCLUDED.volume_spike_ratio,
            volatility_impact_pct = EXCLUDED.volatility_impact_pct
    """
    
    cursor.executemany(insert_query, records)
    conn.commit()
    cursor.close()


def main():
    """Main ETL pipeline."""
    print("=" * 80)
    print("IMPACT ANALYSIS RETRY (BATCHED)")
    print("=" * 80)
    
    conn = get_db_connection()
    
    try:
        news_df = load_news_events_without_impact(conn)
        
        if news_df.empty:
            print("✅ All events already have impact analysis!")
            return
        
        market_df = load_market_ticks(conn)
        
        print("\n🔬 Calculating impact metrics...")
        
        market_by_ticker = {
            ticker: group.sort_values('time').reset_index(drop=True)
            for ticker, group in market_df.groupby('ticker')
        }
        
        batch_size = 1000
        batch_records = []
        total_inserted = 0
        skipped = 0
        
        for _, news_row in tqdm(news_df.iterrows(), total=len(news_df), desc="Processing"):
            ticker = news_row['ticker']
            ticker_market = market_by_ticker.get(ticker)
            
            if ticker_market is None or ticker_market.empty:
                skipped += 1
                continue
            
            impact = calculate_impact_for_event(news_row, ticker_market)
            
            if impact is not None:
                # Convert numpy types to Python native types
                batch_records.append((
                    impact['event_id'], impact['ticker'], impact['published_at'], impact['headline'],
                    impact['sentiment_score'], impact['source'],
                    float(impact['price_at_news']), int(impact['volume_at_news']),
                    float(impact['price_30min_after']), float(impact['price_impact_pct']),
                    int(impact['volume_30min_total']), float(impact['volume_baseline_avg']), 
                    float(impact['volume_spike_ratio']) if impact['volume_spike_ratio'] is not None else None,
                    float(impact['high_30min']), float(impact['low_30min']), float(impact['volatility_impact_pct'])
                ))
                
                # Insert in batches
                if len(batch_records) >= batch_size:
                    insert_impact_batch(conn, batch_records)
                    total_inserted += len(batch_records)
                    print(f"  ✅ Inserted batch: {total_inserted:,} records so far")
                    batch_records = []
            else:
                skipped += 1
        
        # Insert remaining records
        if batch_records:
            insert_impact_batch(conn, batch_records)
            total_inserted += len(batch_records)
            print(f"  ✅ Inserted final batch: {total_inserted:,} total records")
        
        print(f"\n✅ Successfully inserted {total_inserted:,} impact analysis records")
        print(f"⚠️  Skipped {skipped:,} events (insufficient market data)")
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
