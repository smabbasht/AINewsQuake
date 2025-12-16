"""
SQLAlchemy ORM models for AINewsQuake database schema.

Defines the database tables for news events and market ticks, with TimescaleDB
hypertable support for time-series data.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base

Base: Any = declarative_base()


class AINewsEvent(Base):
    """
    SQLAlchemy model for AI news events.
    
    This table stores financial news events related to AI stocks, with metadata
    for time-based correlation with market data.
    """
    
    __tablename__ = "ai_news_events"
    
    event_id = Column(String(255), primary_key=True, nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    headline = Column(Text, nullable=False)
    source = Column(String(255), nullable=False)
    sentiment_score = Column(Float, nullable=True)
    
    # Ensure no duplicate news events
    __table_args__ = (
        UniqueConstraint("ticker", "published_at", "headline", name="uq_news_event"),
        Index("idx_ticker_published", "ticker", "published_at"),
    )
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AINewsEvent(event_id='{self.event_id}', ticker='{self.ticker}', "
            f"published_at='{self.published_at}')>"
        )


class MarketTick(Base):
    """
    SQLAlchemy model for 1-minute OHLCV market data.
    
    This table is converted to a TimescaleDB hypertable partitioned by time
    for efficient time-series queries.
    """
    
    __tablename__ = "market_ticks"
    
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    ticker = Column(String(10), primary_key=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    __table_args__ = (
        Index("idx_market_ticker_time", "ticker", "time"),
    )
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<MarketTick(ticker='{self.ticker}', time='{self.time}', "
            f"close={self.close})>"
        )
