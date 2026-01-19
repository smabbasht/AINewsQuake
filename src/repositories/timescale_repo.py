"""
TimescaleDB repository for database operations.

Provides CRUD operations for news events and market ticks with TimescaleDB
hypertable support and idempotent upsert logic.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import create_engine, text, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.schemas import NewsEvent, MarketTick, VolatilityImpact
from src.repositories.models import Base, AINewsEvent, MarketTick as MarketTickModel

logger = logging.getLogger(__name__)


class TimescaleRepository:
    """
    Repository for TimescaleDB operations.
    
    Handles database initialization, CRUD operations, and time-series queries
    for news events and market data.
    """
    
    def __init__(self, database_url: str, async_mode: bool = True) -> None:
        """
        Initialize the repository.
        
        Args:
            database_url: Database connection URL
            async_mode: Whether to use async SQLAlchemy (default: True)
        """
        self.database_url = database_url
        self.async_mode = async_mode
        
        if async_mode:
            self.engine: AsyncEngine = create_async_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        else:
            # Sync engine for initial setup
            sync_url = database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
            self.sync_engine = create_engine(sync_url, echo=False)
    
    async def init_db(self) -> None:
        """
        Initialize database schema.
        
        Creates tables and converts market_ticks to a TimescaleDB hypertable.
        """
        logger.info("Initializing database schema...")
        
        # Use sync engine for DDL operations
        sync_url = self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        sync_engine = create_engine(sync_url, echo=False)
        
        # Create tables
        Base.metadata.create_all(sync_engine)
        logger.info("Created tables")
        
        # Convert market_ticks to hypertable
        with sync_engine.connect() as conn:
            # Check if already a hypertable
            result = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM timescaledb_information.hypertables
                        WHERE hypertable_name = 'market_ticks'
                    )
                    """
                )
            )
            is_hypertable = result.scalar()
            
            if not is_hypertable:
                conn.execute(
                    text(
                        """
                        SELECT create_hypertable(
                            'market_ticks',
                            'time',
                            chunk_time_interval => INTERVAL '1 day',
                            if_not_exists => TRUE
                        )
                        """
                    )
                )
                conn.commit()
                logger.info("Converted market_ticks to hypertable")
            else:
                logger.info("market_ticks is already a hypertable")
        
        # Create volatility_impact view
        with sync_engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE OR REPLACE VIEW volatility_impact AS
                    SELECT
                        ne.event_id,
                        ne.ticker,
                        ne.published_at,
                        ne.headline,
                        COALESCE(
                            MAX(mt.high) - MIN(mt.low),
                            0
                        ) AS volatility_15min,
                        COALESCE(
                            (SUM(mt.volume)::float / NULLIF(
                                (SELECT AVG(volume) FROM market_ticks mt2
                                 WHERE mt2.ticker = ne.ticker
                                 AND mt2.time BETWEEN ne.published_at - INTERVAL '1 hour'
                                                  AND ne.published_at),
                                0
                            ) - 1) * 100,
                            0
                        ) AS volume_spike
                    FROM ai_news_events ne
                    LEFT JOIN market_ticks mt
                        ON ne.ticker = mt.ticker
                        AND mt.time BETWEEN ne.published_at
                                        AND ne.published_at + INTERVAL '15 minutes'
                    GROUP BY ne.event_id, ne.ticker, ne.published_at, ne.headline
                    """
                )
            )
            conn.commit()
            logger.info("Created volatility_impact view")
        
        sync_engine.dispose()
        logger.info("Database initialization complete")
    
    async def upsert_news_events(self, events: List[NewsEvent]) -> int:
        """
        Insert news events with idempotent upsert logic.
        
        Args:
            events: List of NewsEvent objects to insert
            
        Returns:
            Number of events inserted
        """
        if not events:
            return 0
        
        async with self.SessionLocal() as session:
            inserted_count = 0
            
            # Batch insert for better performance (same as market ticks)
            batch_size = 1000
            for i in range(0, len(events), batch_size):
                batch = events[i : i + batch_size]
                
                values = [
                    {
                        "event_id": event.event_id,
                        "ticker": event.ticker,
                        "published_at": event.published_at,
                        "headline": event.headline,
                        "source": event.source,
                        "sentiment_score": event.sentiment_score,
                    }
                    for event in batch
                ]
                
                stmt = insert(AINewsEvent).values(values)
                stmt = stmt.on_conflict_do_nothing(
                    constraint="uq_news_event"
                )
                
                result = await session.execute(stmt)
                inserted_count += result.rowcount
                
                # Log progress for large batches
                if len(events) > batch_size:
                    logger.info(f"Inserted batch {i//batch_size + 1}/{(len(events)-1)//batch_size + 1} ({inserted_count} so far)")
            
            await session.commit()
            logger.info(f"Inserted {inserted_count} news events (out of {len(events)})")
            return inserted_count
    
    async def upsert_market_ticks(self, ticks: List[MarketTick]) -> int:
        """
        Insert market ticks with idempotent upsert logic.
        
        Args:
            ticks: List of MarketTick objects to insert
            
        Returns:
            Number of ticks inserted
        """
        if not ticks:
            return 0
        
        async with self.SessionLocal() as session:
            inserted_count = 0
            
            # Batch insert for better performance
            batch_size = 1000
            for i in range(0, len(ticks), batch_size):
                batch = ticks[i : i + batch_size]
                
                values = [
                    {
                        "time": tick.time,
                        "ticker": tick.ticker,
                        "open": tick.open,
                        "high": tick.high,
                        "low": tick.low,
                        "close": tick.close,
                        "volume": tick.volume,
                    }
                    for tick in batch
                ]
                
                stmt = insert(MarketTickModel).values(values)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["time", "ticker"]
                )
                
                result = await session.execute(stmt)
                inserted_count += result.rowcount
            
            await session.commit()
            logger.info(f"Inserted {inserted_count} market ticks (out of {len(ticks)})")
            return inserted_count
    
    async def get_volatility_impact(
        self,
        ticker: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[VolatilityImpact]:
        """
        Query volatility impact data from the view.
        
        Args:
            ticker: Optional ticker filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            
        Returns:
            List of VolatilityImpact objects
        """
        async with self.SessionLocal() as session:
            query = text(
                """
                SELECT
                    event_id,
                    ticker,
                    published_at,
                    headline,
                    volatility_15min,
                    volume_spike
                FROM volatility_impact
                WHERE 1=1
                    AND (:ticker IS NULL OR ticker = :ticker)
                    AND (:from_date IS NULL OR published_at >= :from_date)
                    AND (:to_date IS NULL OR published_at <= :to_date)
                ORDER BY published_at DESC
                """
            )
            
            result = await session.execute(
                query,
                {
                    "ticker": ticker,
                    "from_date": from_date,
                    "to_date": to_date,
                },
            )
            
            rows = result.fetchall()
            
            return [
                VolatilityImpact(
                    event_id=row[0],
                    ticker=row[1],
                    published_at=row[2],
                    headline=row[3],
                    volatility_15min=row[4],
                    volume_spike=row[5],
                )
                for row in rows
            ]
    
    async def close(self) -> None:
        """Close database connections."""
        if self.async_mode:
            await self.engine.dispose()
        else:
            self.sync_engine.dispose()
