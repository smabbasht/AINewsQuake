"""
Finnhub API client.

Fetches historical company news and calculates sentiment using VADER.
"""

import logging
import time
from datetime import date, datetime, timezone
from typing import List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.domain.schemas import NewsEvent

logger = logging.getLogger(__name__)


class FinnhubClient:
    """
    Client for Finnhub company news API.
    
    Fetches historical news and calculates sentiment using VADER.
    Free tier: 60 calls/minute, 30 calls/second.
    """
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Finnhub client.
        
        Args:
            api_key: Finnhub API key
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.max_retries = max_retries
        
        # Initialize VADER sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
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
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score using VADER.
        
        Args:
            text: Text to analyze
            
        Returns:
            Compound sentiment score (-1.0 to 1.0)
        """
        if not text:
            return 0.0
        
        scores = self.sentiment_analyzer.polarity_scores(text)
        return scores['compound']  # Returns -1.0 to 1.0
    
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
        import hashlib
        content = f"{ticker}_{published_at.isoformat()}_{headline}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        date_str = published_at.strftime("%Y%m%d")
        return f"fh_{ticker.lower()}_{date_str}_{hash_suffix}"
    
    def fetch_company_news(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
    ) -> List[NewsEvent]:
        """
        Fetch company news for a ticker within a date range.
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            
        Returns:
            List of NewsEvent objects with VADER sentiment scores
        """
        logger.info(f"Fetching company news for {ticker} from {from_date} to {to_date}")
        
        url = f"{self.BASE_URL}/company-news"
        params = {
            "symbol": ticker,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "token": self.api_key,
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
                # Parse timestamp (Unix timestamp in seconds)
                timestamp = item.get("datetime", 0)
                published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(
                    tzinfo=None
                )
                
                headline = item.get("headline", "")
                summary = item.get("summary", "")
                
                # Calculate sentiment using VADER
                # Use headline + summary for better sentiment analysis
                text_for_sentiment = f"{headline}. {summary}"
                sentiment_score = self._calculate_sentiment(text_for_sentiment)
                
                event = NewsEvent(
                    event_id=self._generate_event_id(ticker, published_at, headline),
                    ticker=ticker,
                    published_at=published_at,
                    headline=headline,
                    source=item.get("source", "Finnhub"),
                    sentiment_score=sentiment_score,
                )
                
                events.append(event)
            
            logger.info(f"Fetched {len(events)} news items for {ticker} with VADER sentiment")
            
            # Rate limiting - conservative for free tier
            time.sleep(1)  # 60 calls/minute = 1 call per second
            
            return events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
    def fetch_company_news_batch(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
    ) -> List[NewsEvent]:
        """
        Fetch company news using smart backfill strategy.
        
        Works backwards from most recent data, using the oldest fetched date
        as the new end date for the next batch. This ensures complete coverage
        without gaps, even when news volume varies.
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date (inclusive) - target earliest date
            to_date: End date (inclusive) - start from here and work backwards
            
        Returns:
            List of NewsEvent objects with VADER sentiment scores
        """
        from datetime import timedelta
        
        all_events: List[NewsEvent] = []
        current_end_date = to_date
        iteration = 0
        max_iterations = 100  # Safety limit to prevent infinite loops
        
        logger.info(
            f"Starting smart backfill for {ticker} from {to_date} backwards to {from_date}"
        )
        
        try:
            while current_end_date >= from_date and iteration < max_iterations:
                iteration += 1
                
                # Fetch news for current batch
                logger.info(
                    f"Batch {iteration}: Fetching {ticker} from {from_date} to {current_end_date}"
                )
                
                try:
                    batch_events = self.fetch_company_news(ticker, from_date, current_end_date)
                    
                    if not batch_events:
                        logger.info(f"No more news found for {ticker}, stopping backfill")
                        break
                    
                    # Filter events to only include those within our target date range
                    filtered_events = [
                        event for event in batch_events
                        if from_date <= event.published_at.date() <= to_date
                    ]
                    
                    if not filtered_events:
                        logger.info(
                            f"No events in target range {from_date} to {to_date}, stopping backfill"
                        )
                        break
                    
                    all_events.extend(filtered_events)
                    
                    # Find the oldest date in this batch (within our target range)
                    oldest_date = min(event.published_at.date() for event in filtered_events)
                    logger.info(
                        f"Fetched {len(batch_events)} items, {len(filtered_events)} in range. "
                        f"Oldest date in range: {oldest_date}"
                    )
                    
                    # If the oldest date in this batch is at or before our target start date,
                    # we've covered the entire range
                    if oldest_date <= from_date:
                        logger.info(
                            f"Reached target start date {from_date}, backfill complete"
                        )
                        break
                    
                    # Set new end date to one day before the oldest date we just fetched
                    # Make sure it's still within our target range
                    new_end_date = oldest_date - timedelta(days=1)
                    
                    if new_end_date < from_date:
                        logger.info(
                            f"Next batch would be before target start date {from_date}, stopping"
                        )
                        break
                    
                    current_end_date = new_end_date
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 403:
                        logger.error(
                            f"⚠️  API QUOTA EXCEEDED or FORBIDDEN (403) for {ticker}\n"
                            f"Last successfully fetched date: {current_end_date}\n"
                            f"Total news items collected so far: {len(all_events)}\n"
                            f"To resume, run with: --from-date {from_date} --to-date {current_end_date}"
                        )
                        break
                    elif e.response.status_code == 429:
                        logger.error(
                            f"⚠️  RATE LIMIT EXCEEDED (429) for {ticker}\n"
                            f"Last successfully fetched date: {current_end_date}\n"
                            f"Total news items collected so far: {len(all_events)}\n"
                            f"Please wait and retry with: --from-date {from_date} --to-date {current_end_date}"
                        )
                        break
                    else:
                        raise
                
        except Exception as e:
            logger.error(
                f"⚠️  ERROR during backfill for {ticker}: {e}\n"
                f"Last successfully fetched date: {current_end_date}\n"
                f"Total news items collected so far: {len(all_events)}\n"
                f"To resume, run with: --from-date {from_date} --to-date {current_end_date}"
            )
        
        logger.info(
            f"Backfill complete for {ticker}: {len(all_events)} total news items "
            f"({iteration} batches)"
        )
        return all_events
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()



