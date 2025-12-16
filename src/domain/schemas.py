"""
Pydantic schemas for AINewsQuake domain models.

These schemas define the data transfer objects (DTOs) used throughout the application
for type-safe data validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class NewsEvent(BaseModel):
    """
    Represents a financial news event related to AI stocks.
    
    Attributes:
        event_id: Unique identifier for the news event
        ticker: Stock ticker symbol (e.g., 'NVDA', 'MSFT')
        published_at: Publication timestamp in UTC
        headline: News headline text
        source: News source/publisher
        sentiment_score: Optional sentiment analysis score (-1.0 to 1.0)
    """
    
    event_id: str = Field(..., description="Unique event identifier")
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    published_at: datetime = Field(..., description="Publication timestamp (UTC)")
    headline: str = Field(..., min_length=1, description="News headline")
    source: str = Field(..., description="News source/publisher")
    sentiment_score: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="Sentiment score (-1.0 to 1.0)"
    )
    
    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        """Ensure ticker is uppercase."""
        return v.upper()
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "event_id": "fmp_nvda_20250115_001",
                "ticker": "NVDA",
                "published_at": "2025-01-15T14:30:00Z",
                "headline": "NVIDIA Announces New Blackwell GPU Architecture",
                "source": "Reuters",
                "sentiment_score": 0.85,
            }
        }


class MarketTick(BaseModel):
    """
    Represents a 1-minute OHLCV market data tick.
    
    Attributes:
        time: Timestamp of the bar (UTC)
        ticker: Stock ticker symbol
        open: Opening price
        high: Highest price in the period
        low: Lowest price in the period
        close: Closing price
        volume: Trading volume
    """
    
    time: datetime = Field(..., description="Bar timestamp (UTC)")
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    
    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        """Ensure ticker is uppercase."""
        return v.upper()
    
    @field_validator("high")
    @classmethod
    def validate_high(cls, v: float, info: dict) -> float:
        """Ensure high is the highest price."""
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("High must be >= Low")
        if "open" in info.data and v < info.data["open"]:
            raise ValueError("High must be >= Open")
        if "close" in info.data and v < info.data["close"]:
            raise ValueError("High must be >= Close")
        return v
    
    @field_validator("low")
    @classmethod
    def validate_low(cls, v: float, info: dict) -> float:
        """Ensure low is the lowest price."""
        if "open" in info.data and v > info.data["open"]:
            raise ValueError("Low must be <= Open")
        if "close" in info.data and v > info.data["close"]:
            raise ValueError("Low must be <= Close")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "time": "2025-01-15T14:30:00Z",
                "ticker": "NVDA",
                "open": 520.50,
                "high": 522.75,
                "low": 519.25,
                "close": 521.00,
                "volume": 125000,
            }
        }


class VolatilityImpact(BaseModel):
    """
    Represents the volatility impact of a news event on stock price.
    
    This is typically computed from a database view that joins news events
    with market data in a 15-minute window following the event.
    
    Attributes:
        event_id: Reference to the news event
        ticker: Stock ticker symbol
        published_at: News publication timestamp (UTC)
        headline: News headline
        volatility_15min: Price volatility (High - Low) in 15-min window
        volume_spike: Volume change percentage compared to baseline
    """
    
    event_id: str = Field(..., description="News event identifier")
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    published_at: datetime = Field(..., description="News publication timestamp (UTC)")
    headline: str = Field(..., description="News headline")
    volatility_15min: float = Field(..., ge=0, description="15-min volatility (High - Low)")
    volume_spike: float = Field(..., description="Volume change percentage")
    
    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        """Ensure ticker is uppercase."""
        return v.upper()
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "event_id": "fmp_nvda_20250115_001",
                "ticker": "NVDA",
                "published_at": "2025-01-15T14:30:00Z",
                "headline": "NVIDIA Announces New Blackwell GPU Architecture",
                "volatility_15min": 3.50,
                "volume_spike": 245.5,
            }
        }
