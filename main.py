"""
AINewsQuake ETL Pipeline Entry Point.

Runs the complete ETL pipeline to extract news and market data,
transform it, and load it into TimescaleDB.
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime
from typing import List

from dotenv import load_dotenv

from src.adapters.finnhub_client import FinnhubClient
from src.adapters.databento_client import DatabentoClient
from src.repositories.timescale_repo import TimescaleRepository
from src.services.pipeline_service import PipelineService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etl_pipeline.log"),
    ],
)

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="AINewsQuake ETL Pipeline - Extract, Transform, Load AI news and market data"
    )
    
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers (default: from .env TARGET_TICKERS)",
    )
    
    parser.add_argument(
        "--from-date",
        type=str,
        help="Start date in YYYY-MM-DD format (default: from .env ETL_START_DATE)",
    )
    
    parser.add_argument(
        "--to-date",
        type=str,
        help="End date in YYYY-MM-DD format (default: from .env ETL_END_DATE)",
    )
    
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database schema before running ETL",
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run ETL in parallel mode for better performance",
    )
    
    parser.add_argument(
        "--skip-market-data",
        action="store_true",
        help="Skip fetching market data (only fetch news) - saves Databento API calls",
    )
    
    parser.add_argument(
        "--news-only",
        action="store_true",
        help="Alias for --skip-market-data",
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main entry point for the ETL pipeline."""
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    args = parse_arguments()
    
    # Get configuration from environment or arguments
    finnhub_api_key = os.getenv("FINNHUB_API_KEY")
    databento_api_key = os.getenv("DATABENTO_API_KEY")
    database_url = os.getenv("DATABASE_URL")
    
    if not finnhub_api_key:
        logger.error("FINNHUB_API_KEY not found in environment")
        sys.exit(1)
    
    if not databento_api_key:
        logger.error("DATABENTO_API_KEY not found in environment")
        sys.exit(1)
    
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        sys.exit(1)
    
    # Get tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers_str = os.getenv("TARGET_TICKERS", "NVDA,MSFT,AAPL,GOOGL,TSLA,AMD,PLTR,TSM,SMCI,META")
        tickers = [t.strip().upper() for t in tickers_str.split(",")]
    
    # Get date range
    if args.from_date:
        from_date = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    else:
        from_date_str = os.getenv("ETL_START_DATE", "2025-01-01")
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
    
    if args.to_date:
        to_date = datetime.strptime(args.to_date, "%Y-%m-%d").date()
    else:
        to_date_str = os.getenv("ETL_END_DATE", "2025-12-31")
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
    
    # Initialize clients and repository
    logger.info("Initializing clients and repository...")
    
    finnhub_client = FinnhubClient(
        api_key=finnhub_api_key,
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
    )
    
    databento_client = DatabentoClient(
        api_key=databento_api_key,
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
    )
    
    repository = TimescaleRepository(database_url=database_url, async_mode=True)
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database schema...")
        await repository.init_db()
    
    # Create pipeline service
    pipeline = PipelineService(
        finnhub_client=finnhub_client,
        databento_client=databento_client,
        repository=repository,
    )
    
    # Run ETL pipeline
    try:
        logger.info("=" * 80)
        logger.info("STARTING ETL PIPELINE")
        logger.info("=" * 80)
        logger.info(f"Tickers: {', '.join(tickers)}")
        logger.info(f"Date Range: {from_date} to {to_date}")
        logger.info(f"Parallel Mode: {args.parallel}")
        skip_market = args.skip_market_data or args.news_only
        logger.info(f"Skip Market Data: {skip_market}")
        logger.info("=" * 80)
        
        if args.parallel:
            await pipeline.run_etl_parallel(tickers, from_date, to_date, skip_market_data=skip_market)
        else:
            await pipeline.run_etl(tickers, from_date, to_date, skip_market_data=skip_market)
        
        logger.info("ETL pipeline completed successfully!")
        
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        # Cleanup
        finnhub_client.close()
        databento_client.close()
        await repository.close()


if __name__ == "__main__":
    asyncio.run(main())
