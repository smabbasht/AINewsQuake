"""
FMP (Financial Modeling Prep) API client.

Fetches stock news with AI-related keyword filtering and timezone conversion.
"""

import hashlib
import logging
import time
from datetime import date, datetime, timezone
from typing import List, Optional, Set

import requests
import pytz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.domain.schemas import NewsEvent

logger = logging.getLogger(__name__)


class FMPClient:
    """
    Client for Financial Modeling Prep API.
    
    Fetches stock news with keyword filtering and rate limiting.
    """
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(
        self,
        api_key: str,
        keywords: Optional[Set[str]] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> None:
        """
        Initialize FMP client.
        
        Args:
            api_key: FMP API key
            keywords: Set of keywords to filter news (case-insensitive)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key
        self.keywords = keywords or {
            "AI",
            "GPU",
            "Blackwell",
            "LLM",
            "Generative",
            "Machine Learning",
            "Neural Network",
            "Deep Learning",
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
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
    
    def _contains_keywords(self, text: str) -> bool:
        """
        Check if text contains any of the configured keywords.
        
        Args:
            text: Text to check
            
        Returns:
            True if any keyword is found (case-insensitive)
        """
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)
    
    def _convert_to_utc(self, timestamp_str: str) -> datetime:
        """
        Convert FMP timestamp to UTC.
        
        FMP timestamps are typically in EST/EDT. This function handles the conversion.
        
        Args:
            timestamp_str: Timestamp string from FMP API
            
        Returns:
            UTC datetime object
        """
        try:
            # Try parsing ISO format first
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            
            # If no timezone info, assume EST
            if dt.tzinfo is None:
                est = pytz.timezone("US/Eastern")
                dt = est.localize(dt)
            
            # Convert to UTC
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            # Fallback to current time
            return datetime.now(timezone.utc).replace(tzinfo=None)
    
    def _generate_event_id(self, ticker: str, published_at: datetime, headline: str) -> str:
        """
        Generate a unique event ID.
        
        Args:
            ticker: Stock ticker
            published_at: Publication timestamp
            headline: News headline
            
        Returns:
            Unique event ID
        """
        # Create hash from ticker + timestamp + headline
        content = f"{ticker}_{published_at.isoformat()}_{headline}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        date_str = published_at.strftime("%Y%m%d")
        return f"fmp_{ticker.lower()}_{date_str}_{hash_suffix}"
    
    def fetch_stock_news(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
    ) -> List[NewsEvent]:
        """
        Fetch press releases for a ticker within a date range.
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            
        Returns:
            List of NewsEvent objects filtered by keywords
        """
        logger.info(f"Fetching press releases for {ticker} from {from_date} to {to_date}")
        
        # Use press-releases endpoint (available on free tier)
        url = f"{self.BASE_URL}/press-releases/{ticker}"
        params = {
            "page": 0,
            "apikey": self.api_key,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                logger.warning(f"Unexpected response format for {ticker}: {type(data)}")
                return []
            
            events: List[NewsEvent] = []
            
            for item in data:
                # Parse date
                date_str = item.get("date", "")
                if not date_str:
                    continue
                
                try:
                    # Parse date and check if in range
                    item_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if item_date.date() < from_date or item_date.date() > to_date:
                        continue
                except Exception:
                    continue
                
                title = item.get("title", "")
                text = item.get("text", "")
                
                # Filter by keywords
                if not self._contains_keywords(title) and not self._contains_keywords(text):
                    continue
                
                published_at = self._convert_to_utc(date_str)
                
                event = NewsEvent(
                    event_id=self._generate_event_id(ticker, published_at, title),
                    ticker=ticker,
                    published_at=published_at,
                    headline=title,
                    source="FMP Press Release",
                    sentiment_score=None,
                )
                
                events.append(event)
            
            logger.info(
                f"Fetched {len(events)} AI-related press releases for {ticker} "
                f"(filtered from {len(data)} total)"
            )
            
            # Rate limiting
            time.sleep(0.5)  # 2 requests per second max
            
            return events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch press releases for {ticker}: {e}")
            return []
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

