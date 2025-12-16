"""
Databento API client.

Fetches 1-minute OHLCV bars from Databento's historical market data API using the official SDK.
"""

import logging
from datetime import date, datetime, timezone, timedelta
from typing import List

import databento as db

from src.domain.schemas import MarketTick

logger = logging.getLogger(__name__)


class DatabentoClient:
    """
    Client for Databento historical market data API.
    
    Fetches 1-minute OHLCV bars for stock tickers using the official databento SDK.
    """
    
    def __init__(
        self,
        api_key: str,
        dataset: str = "XNAS.ITCH",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Databento client.
        
        Args:
            api_key: Databento API key (should start with 'db-')
            dataset: Dataset identifier (default: XNAS.ITCH for Nasdaq)
            max_retries: Maximum number of retry attempts (not used with SDK but kept for compatibility)
        """
        self.api_key = api_key
        self.dataset = dataset
        self.max_retries = max_retries
        
        # Initialize Databento Historical client
        self.client = db.Historical(api_key)
    
    def fetch_ohlcv_bars(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
    ) -> List[MarketTick]:
        """
        Fetch 1-minute OHLCV bars for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            
        Returns:
            List of MarketTick objects
        """
        logger.info(f"Fetching OHLCV data for {ticker} from {from_date} to {to_date}")
        
        try:
            # Fetch data using Databento SDK
            data = self.client.timeseries.get_range(
                dataset=self.dataset,
                symbols=[ticker],
                schema="ohlcv-1m",
                start=from_date,
                end=to_date,
            )
            
            ticks: List[MarketTick] = []
            
            # Convert Databento records to MarketTick objects
            for record in data:
                try:
                    # Convert timestamp to datetime
                    dt = datetime.fromtimestamp(record.ts_event / 1e9, tz=timezone.utc).replace(
                        tzinfo=None
                    )
                    
                    tick = MarketTick(
                        time=dt,
                        ticker=ticker,
                        open=float(record.open) / 1e9,  # Databento uses fixed-point prices
                        high=float(record.high) / 1e9,
                        low=float(record.low) / 1e9,
                        close=float(record.close) / 1e9,
                        volume=int(record.volume),
                    )
                    
                    ticks.append(tick)
                    
                except (AttributeError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse record for {ticker}: {e}")
                    continue
            
            logger.info(f"Fetched {len(ticks)} OHLCV bars for {ticker}")
            return ticks
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data for {ticker}: {e}")
            return []
    
    def fetch_ohlcv_bars_batch(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
        batch_days: int = 7,
    ) -> List[MarketTick]:
        """
        Fetch OHLCV bars in batches to avoid API limits.
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            batch_days: Number of days per batch
            
        Returns:
            List of MarketTick objects
        """
        all_ticks: List[MarketTick] = []
        current_date = from_date
        
        while current_date <= to_date:
            batch_end = min(current_date + timedelta(days=batch_days - 1), to_date)
            
            batch_ticks = self.fetch_ohlcv_bars(ticker, current_date, batch_end)
            all_ticks.extend(batch_ticks)
            
            current_date = batch_end + timedelta(days=1)
        
        logger.info(f"Fetched {len(all_ticks)} total OHLCV bars for {ticker}")
        return all_ticks
    
    def close(self) -> None:
        """Close the Databento client."""
        # The databento SDK handles cleanup automatically
        pass

