"""
Build news_impact_analysis table by calculating impact metrics.

This script:
1. Loads news events and market ticks from database
2. For each news event, calculates:
   - Price impact (30-min delta)
   - Volume spike ratio (vs 2-hour baseline)
   - Volatility impact (high-low range)
3. Inserts results into news_impact_analysis table
"""

import os
import sys
from datetime import timedelta
from typing import Optional

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment
load_dotenv()


def get_db_connection():
    """Get database connection."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)
    
    # Convert asyncpg URL to psycopg2 URL
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(database_url)


def load_news_events(conn) -> pd.DataFrame:
    """Load all news events from database."""
    query = """
        SELECT 
            event_id,
            ticker,
            published_at,
            headline,
            sentiment_score,
            source
        FROM ai_news_events
        ORDER BY published_at
    """
    
    print("📰 Loading news events...")
    df = pd.read_sql_query(query, conn)
    df['published_at'] = pd.to_datetime(df['published_at'])
    print(f"✅ Loaded {len(df):,} news events")
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


def get_nearest_price(market_df: pd.DataFrame, timestamp: pd.Timestamp) -> Optional[float]:
    """Get the nearest price to a given timestamp."""
    if market_df.empty:
        return None
    
    # Find nearest time
    idx = (market_df['time'] - timestamp).abs().idxmin()
    return market_df.loc[idx, 'close']


def calculate_impact_for_event(
    news_row: pd.Series,
    market_df: pd.DataFrame
) -> Optional[dict]:
    """
    Calculate impact metrics for a single news event.
    
    Args:
        news_row: Series with news event data
        market_df: DataFrame with market ticks for this ticker
    
    Returns:
        Dict with impact metrics or None if insufficient data
    """
    published_at = news_row['published_at']
    
    # 1. FIND START OF MARKET REACTION (Next Market Open)
    # Get all ticks at or after publication
    market_after = market_df[market_df['time'] >= published_at]
    
    if market_after.empty:
        # No future market data available yet
        return None
    
    # The reaction measurement starts at the first available tick
    # (Immediate if during market hours, or next open if after hours)
    reaction_start_tick = market_after.iloc[0]
    reaction_start_time = reaction_start_tick['time']
    
    # 2. GET BASELINE (Pre-news price/volume)
    # Get ticks strictly before publication
    market_before = market_df[market_df['time'] < published_at]
    
    if market_before.empty:
        # No prior history
        return None
        
    # Price at news is the last known price before publication
    price_at_news_tick = market_before.iloc[-1]
    price_at_news = price_at_news_tick['close']
    volume_at_news = price_at_news_tick['volume']
    
    # Volume baseline: average of last 120 ticks (approx 2 hours of trading)
    # This correctly handles gaps (overnight/weekends) by taking actual trading minutes
    baseline_data = market_before.tail(120)
    volume_baseline_avg = baseline_data['volume'].mean()

    # 3. MEASURE IMPACT 30 MINS AFTER REACTION START
    window_end = reaction_start_time + timedelta(minutes=30)
    
    # Get window data: from reaction start to 30 mins later
    window_data = market_df[
        (market_df['time'] >= reaction_start_time) &
        (market_df['time'] <= window_end)
    ]
    
    if window_data.empty:
        return None
    
    # Calculate impact metrics
    price_30min_after = window_data.iloc[-1]['close']
    volume_30min_total = window_data['volume'].sum()
    high_30min = window_data['high'].max()
    low_30min = window_data['low'].min()
    
    # Price impact percentage (from pre-news price to 30 mins into reaction)
    price_impact_pct = ((price_30min_after - price_at_news) / price_at_news) * 100
    
    # Volume spike ratio
    if volume_baseline_avg and volume_baseline_avg > 0:
        # Expected volume in 30 min = baseline * (actual minutes in window)
        # Usually 30, but could be less if near end of data.
        # Let's assume 30 for normalization.
        expected_volume = volume_baseline_avg * 30
        volume_spike_ratio = volume_30min_total / expected_volume
    else:
        volume_spike_ratio = None
    
    # Volatility impact percentage
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


def build_impact_analysis(news_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build impact analysis for all news events.
    
    Args:
        news_df: DataFrame with news events
        market_df: DataFrame with market ticks
    
    Returns:
        DataFrame with impact metrics
    """
    print("\n🔬 Calculating impact metrics...")
    
    results = []
    skipped = 0
    
    # Group market data by ticker for efficiency
    market_by_ticker = {
        ticker: group.sort_values('time').reset_index(drop=True)
        for ticker, group in market_df.groupby('ticker')
    }
    
    # Process each news event
    for _, news_row in tqdm(news_df.iterrows(), total=len(news_df), desc="Processing news"):
        ticker = news_row['ticker']
        
        # Get market data for this ticker
        ticker_market = market_by_ticker.get(ticker)
        
        if ticker_market is None or ticker_market.empty:
            skipped += 1
            continue
        
        # Calculate impact
        impact = calculate_impact_for_event(news_row, ticker_market)
        
        if impact is not None:
            results.append(impact)
        else:
            skipped += 1
    
    print(f"✅ Calculated impact for {len(results):,} news events")
    print(f"⚠️  Skipped {skipped:,} events (insufficient market data)")
    
    return pd.DataFrame(results)


def insert_impact_analysis(conn, impact_df: pd.DataFrame):
    """Insert impact analysis results into database."""
    print(f"\n💾 Inserting {len(impact_df):,} records into news_impact_analysis...")
    
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
            volatility_impact_pct = EXCLUDED.volatility_impact_pct,
            price_30min_after = EXCLUDED.price_30min_after,
            volume_30min_total = EXCLUDED.volume_30min_total,
            high_30min = EXCLUDED.high_30min,
            low_30min = EXCLUDED.low_30min
    """
    
    # Prepare data for bulk insert
    records = []
    for _, row in impact_df.iterrows():
        records.append((
            row['event_id'], row['ticker'], row['published_at'], row['headline'],
            row['sentiment_score'], row['source'],
            row['price_at_news'], row['volume_at_news'],
            row['price_30min_after'], row['price_impact_pct'],
            row['volume_30min_total'], row['volume_baseline_avg'], row['volume_spike_ratio'],
            row['high_30min'], row['low_30min'], row['volatility_impact_pct']
        ))
    
    # Execute bulk insert
    cursor.executemany(insert_query, records)
    conn.commit()
    
    print(f"✅ Inserted {cursor.rowcount:,} records")
    cursor.close()


def main():
    """Main ETL pipeline."""
    print("=" * 80)
    print("NEWS IMPACT ANALYSIS ETL PIPELINE")
    print("=" * 80)
    
    # Connect to database
    conn = get_db_connection()
    
    try:
        # Load data
        news_df = load_news_events(conn)
        market_df = load_market_ticks(conn)
        
        # Calculate impact metrics
        impact_df = build_impact_analysis(news_df, market_df)
        
        if impact_df.empty:
            print("⚠️  No impact data to insert")
            return
        
        # Insert into database
        insert_impact_analysis(conn, impact_df)
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(f"Total news events processed: {len(news_df):,}")
        print(f"Impact records created: {len(impact_df):,}")
        print(f"\nPrice Impact:")
        print(f"  Mean: {impact_df['price_impact_pct'].mean():.2f}%")
        print(f"  Median: {impact_df['price_impact_pct'].median():.2f}%")
        print(f"  Max: {impact_df['price_impact_pct'].max():.2f}%")
        print(f"  Min: {impact_df['price_impact_pct'].min():.2f}%")
        
        print(f"\nVolume Spike Ratio:")
        print(f"  Mean: {impact_df['volume_spike_ratio'].mean():.2f}x")
        print(f"  Median: {impact_df['volume_spike_ratio'].median():.2f}x")
        
        print(f"\nVolatility Impact:")
        print(f"  Mean: {impact_df['volatility_impact_pct'].mean():.2f}%")
        print(f"  Median: {impact_df['volatility_impact_pct'].median():.2f}%")
        
        print("\n✅ ETL pipeline completed successfully!")
        
    except Exception as e:
        print(f"\n❌ ETL pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
