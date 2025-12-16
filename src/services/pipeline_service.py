"""
ETL Pipeline Service.

Orchestrates the Extract-Transform-Load process for news and market data.
"""

import asyncio
import logging
from datetime import date
from typing import List

from tqdm import tqdm

from src.adapters.finnhub_client import FinnhubClient
from src.adapters.databento_client import DatabentoClient
from src.repositories.timescale_repo import TimescaleRepository
from src.domain.schemas import NewsEvent, MarketTick

logger = logging.getLogger(__name__)


class PipelineService:
    """
    ETL pipeline orchestration service.
    
    Coordinates data extraction from Finnhub and Databento, transformation,
    and loading into TimescaleDB.
    """
    
    def __init__(
        self,
        finnhub_client: FinnhubClient,
        databento_client: DatabentoClient,
        repository: TimescaleRepository,
    ) -> None:
        """
        Initialize pipeline service.
        
        Args:
            finnhub_client: Finnhub API client for news data
            databento_client: Databento API client for market data
            repository: TimescaleDB repository for data storage
        """
        self.finnhub_client = finnhub_client
        self.databento_client = databento_client
        self.repository = repository
    
    async def run_etl(
        self,
        tickers: List[str],
        from_date: date,
        to_date: date,
        skip_market_data: bool = False,
    ) -> None:
        """
        Run the complete ETL pipeline.
        
        Args:
            tickers: List of stock ticker symbols
            from_date: Start date for data extraction
            to_date: End date for data extraction
            skip_market_data: If True, skip fetching market data (news only)
        """
        logger.info(
            f"Starting ETL pipeline for {len(tickers)} tickers "
            f"from {from_date} to {to_date}"
        )
        
        # Step 1: Extract News Data from Finnhub
        logger.info("=" * 80)
        logger.info("STEP 1: Extracting News Data from Finnhub")
        logger.info("=" * 80)
        
        total_news_inserted = 0
        
        for ticker in tqdm(tickers, desc="Fetching news"):
            logger.info(f"Processing news for {ticker}...")
            events = self.finnhub_client.fetch_company_news_batch(ticker, from_date, to_date)
            
            # Flush to database immediately after each ticker
            if events:
                inserted = await self.repository.upsert_news_events(events)
                total_news_inserted += inserted
                logger.info(f"✓ {ticker}: Fetched {len(events)} items, inserted {inserted} new items")
            else:
                logger.warning(f"✗ {ticker}: No news items fetched")
        
        logger.info(f"Extracted and inserted {total_news_inserted} total news events")
        
        # Step 3: Extract Market Data (skip if requested)
        if skip_market_data:
            logger.info("=" * 80)
            logger.info("SKIPPING Market Data Extraction (--skip-market-data flag set)")
            logger.info("=" * 80)
            all_market_ticks: List[MarketTick] = []
            inserted_ticks = 0
        else:
            logger.info("=" * 80)
            logger.info("STEP 3: Extracting Market Data from Databento")
            logger.info("=" * 80)
            
            all_market_ticks: List[MarketTick] = []
            
            for ticker in tqdm(tickers, desc="Fetching OHLCV"):
                # Use batch fetching for large date ranges
                ticks = self.databento_client.fetch_ohlcv_bars_batch(
                    ticker, from_date, to_date, batch_days=7
                )
                all_market_ticks.extend(ticks)
            
            logger.info(f"Extracted {len(all_market_ticks)} total market ticks")
            
            # Step 4: Load Market Data
            logger.info("=" * 80)
            logger.info("STEP 4: Loading Market Data to Database")
            logger.info("=" * 80)
            
            if all_market_ticks:
                inserted_ticks = await self.repository.upsert_market_ticks(all_market_ticks)
                logger.info(f"Inserted {inserted_ticks} market ticks into database")
            else:
                inserted_ticks = 0
                logger.warning("No market ticks to insert")
        
        # Step 5: Summary
        logger.info("=" * 80)
        logger.info("ETL PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total News Events Inserted: {total_news_inserted}")
        logger.info(
            f"Total Market Ticks: {len(all_market_ticks)} (Inserted: {inserted_ticks})"
        )
        logger.info("=" * 80)
    
    async def run_etl_parallel(
        self,
        tickers: List[str],
        from_date: date,
        to_date: date,
        skip_market_data: bool = False,
    ) -> None:
        """
        Run ETL pipeline with parallel extraction for better performance.
        
        Args:
            tickers: List of stock ticker symbols
            from_date: Start date for data extraction
            to_date: End date for data extraction
            skip_market_data: If True, skip fetching market data (news only)
        """
        logger.info(
            f"Starting PARALLEL ETL pipeline for {len(tickers)} tickers "
            f"from {from_date} to {to_date}"
        )
        
        # Extract news and market data in parallel
        logger.info("Extracting news and market data in parallel...")
        
        async def extract_news() -> List[NewsEvent]:
            """Extract news data for all tickers."""
            all_events: List[NewsEvent] = []
            for ticker in tickers:
                events = self.finnhub_client.fetch_company_news_batch(ticker, from_date, to_date)
                all_events.extend(events)
            return all_events
        
        async def extract_market() -> List[MarketTick]:
            """Extract market data for all tickers."""
            all_ticks: List[MarketTick] = []
            for ticker in tickers:
                ticks = self.databento_client.fetch_ohlcv_bars_batch(
                    ticker, from_date, to_date, batch_days=7
                )
                all_ticks.extend(ticks)
            return all_ticks
        
        # Run extraction in parallel (or skip market data)
        if skip_market_data:
            logger.info("Skipping market data extraction (--skip-market-data flag set)")
            all_news_events = await extract_news()
            all_market_ticks: List[MarketTick] = []
        else:
            news_task = asyncio.create_task(extract_news())
            market_task = asyncio.create_task(extract_market())
            all_news_events, all_market_ticks = await asyncio.gather(news_task, market_task)
        
        logger.info(f"Extracted {len(all_news_events)} news events")
        logger.info(f"Extracted {len(all_market_ticks)} market ticks")
        
        # Load data
        logger.info("Loading data to database...")
        
        if all_news_events:
            inserted_news = await self.repository.upsert_news_events(all_news_events)
            logger.info(f"Inserted {inserted_news} news events")
        
        if all_market_ticks:
            inserted_ticks = await self.repository.upsert_market_ticks(all_market_ticks)
            logger.info(f"Inserted {inserted_ticks} market ticks")
        
        logger.info("PARALLEL ETL PIPELINE COMPLETE")

