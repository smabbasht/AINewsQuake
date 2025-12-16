"""
Alpha Vantage API client.

Fetches news with pre-calculated sentiment scores using the NEWS_SENTIMENT endpoint.
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.domain.schemas import NewsEvent

logger = logging.getLogger(__name__)


class AlphaVantageClient:
    """
    Client for Alpha Vantage NEWS_SENTIMENT API.
    
    Fetches news with pre-calculated sentiment and relevance scores.
    Free tier: 25 requests per day.
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Alpha Vantage client.
        
        Args:
            api_key: Alpha Vantage API key
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.max_retries = max_retries
        
        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _parse_av_time(self, time_str: str) -> datetime:
        """
        Parse Alpha Vantage timestamp format.
        
        Args:
            time_str: Timestamp in format "20250410T153000"
            
        Returns:
            UTC datetime object
        """
        try:
            # Format: "20250410T153000"
            dt = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
            # Assume UTC
            return dt.replace(tzinfo=timezone.utc).replace(tzinfo=None)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{time_str}': {e}")
            return datetime.now(timezone.utc).replace(tzinfo=None)
    
    def _generate_event_id(self, ticker: str, published_at: datetime, title: str) -> str:
        """
        Generate a unique event ID.
        
        Args:
            ticker: Stock ticker
            published_at: Publication timestamp
            title: News title
            
        Returns:
            Unique event ID
        """
        import hashlib
        content = f"{ticker}_{published_at.isoformat()}_{title}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        date_str = published_at.strftime("%Y%m%d")
        return f"av_{ticker.lower()}_{date_str}_{hash_suffix}"
    
    def fetch_news(
        self,
        ticker: str,
        limit: int = 1000,
        topics: Optional[str] = None,
    ) -> List[NewsEvent]:
        """
        Fetch news with sentiment scores for a ticker.
        
        NOTE: Free tier limit is 25 requests/day. Use carefully.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of news items (default: 1000)
            topics: Optional topics filter (e.g., "technology,earnings")
            
        Returns:
            List of NewsEvent objects with sentiment scores
        """
        logger.info(f"Fetching news with sentiment for {ticker} (limit={limit})")
        
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "limit": limit,
            "sort": "LATEST",
            "apikey": self.api_key,
        }
        
        if topics:
            params["topics"] = topics
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return []
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage API limit: {data['Note']}")
                return []
            
            if "feed" not in data:
                logger.warning(f"No feed data for {ticker}: {data}")
                return []
            
            events: List[NewsEvent] = []
            
            for item in data.get("feed", []):
                # Extract ticker-specific sentiment
                # News might mention multiple stocks, we want the score for our ticker
                ticker_sentiment = next(
                    (t for t in item.get("ticker_sentiment", []) if t["ticker"] == ticker),
                    None
                )
                
                # Use ticker-specific sentiment if available, otherwise overall sentiment
                if ticker_sentiment:
                    sentiment_score = float(ticker_sentiment.get("ticker_sentiment_score", 0.0))
                else:
                    sentiment_score = float(item.get("overall_sentiment_score", 0.0))
                
                # Parse timestamp
                time_published = item.get("time_published", "")
                published_at = self._parse_av_time(time_published)
                
                title = item.get("title", "")
                
                event = NewsEvent(
                    event_id=self._generate_event_id(ticker, published_at, title),
                    ticker=ticker,
                    published_at=published_at,
                    headline=title,
                    source=item.get("source", "Alpha Vantage"),
                    sentiment_score=sentiment_score,
                )
                
                events.append(event)
            
            logger.info(f"Fetched {len(events)} news items with sentiment for {ticker}")
            
            # Rate limiting - be conservative with free tier
            time.sleep(12)  # 5 requests per minute max (25/day = very limited)
            
            return events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            return []
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
