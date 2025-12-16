# PROJECT CONTEXT: AINewsQuake

## 1. Project Metadata
* **Project Name:** AINewsQuake
* **Subtitle:** An Event-Driven Data Pipeline for Quantifying Market Reaction to AI Headlines.
* **Course:** Data Management (Laurea Magistrale in Data Science).
* **Submission Deadline:** January 14, 2026.
* **Instructor Focus:** Data integration, architectural rigour, handling heterogeneous data (Text + Time Series), and "reasonable" storage strategies.

## 2. Core Objective
To merge "Slow Data" (Financial News) with "Fast Data" (Market Microstructure) to analyze the volatility impact of AI-related headlines on the top 10 AI stocks.
* **The Metaphor:** The "Seismograph." News is the *Epicenter* (Event), and Market Volatility is the *Shockwave* (Reaction).
* **Scope:** Full year 2025 (Jan 1 - Dec 31).
* **Target Tickers (The AI 10):**
    1.  **Titans:** NVDA, MSFT, AAPL, GOOGL, TSLA
    2.  **Challengers:** AMD, PLTR, TSM, SMCI, META

## 3. Technology Stack
* **Language:** Python 3.10+, using uv for managing environment.
* **IDE:** Google Antigravity (Agentic Workflow).
* **Database:** TimescaleDB (PostgreSQL extension) run via Docker.
* **ORM:** SQLAlchemy (Async preferred, or standard).
* **Data Processing:** Pandas.
* **Visualization:** Streamlit.
* **Data Sources:**
    * **FMP (Financial Modeling Prep):** * PRIMARY: `v3/press-releases` (Official Corporate Events).
    * **Databento:** For 1-minute OHLCV bars (Nasdaq/XNAS).

## 4. Architectural Pattern: Repository-Service
We strictly adhere to the **Repository-Service Pattern** to separate concerns and ensure testability. Do not write monolithic scripts.

### Folder Structure
```text
ainewsquake/
├── src/
│   ├── adapters/           # External API Communication
│   │   ├── fmp_client.py
│   │   └── databento_client.py
│   ├── domain/             # Data Classes (DTOs)
│   │   └── schemas.py      # Pydantic models for NewsEvent, MarketTick
│   ├── repositories/       # Database Logic (SQLAlchemy)
│   │   └── timescale_repo.py
│   └── services/           # Business Logic (The Merge)
│       └── pipeline_service.py
├── app.py                  # Streamlit Dashboard Entry
├── main.py                 # ETL Pipeline Entry Point
├── docker-compose.yaml     # Infrastructure
└── requirements.txt
```

### Design Rules for the Agent

1.  **Dependency Injection:** Services should accept Repositories as arguments.
2.  **Type Hinting:** All Python code must use strict type hints (`typing.List`, `typing.Optional`, etc.).
3.  **Environment Variables:** Never hardcode API keys. Use `python-dotenv` and `.env`.
4.  **Idempotency:** The ETL pipeline must be runnable multiple times without duplicating data in the database (use `ON CONFLICT DO NOTHING` or Upserts).

## 5. Data Pipeline Specification (ETL)

1.  **Extract (Ingestion):**
      * Fetch full-year 2025 news from FMP (Filter for keywords: "AI", "GPU", "Blackwell", "LLM", "Generative").
      * Fetch full-year 2025 OHLCV-1m data from Databento.
2.  **Transform (Processing):**
      * **Time Alignment:** Convert FMP timestamps (often EST) to UTC to match Databento.
      * **Tagging:** Create a binary flag or event ID in the time-series data linking it to a specific news headline.
3.  **Load (Storage):**
      * **Hypertable:** Store market data in a TimescaleDB Hypertable partitioned by time.
      * **Relational:** Store News Events in a standard Postgres table, linked by Ticker and Time window.

## 6. Database Schema Strategy

  * **Table `ai_news_events`:** `event_id` (PK), `ticker`, `published_at` (UTC), `headline`, `source`, `sentiment_score`.
  * **Table `market_ticks` (Hypertable):** `time` (PK, Partition Key), `ticker` (PK), `open`, `high`, `low`, `close`, `volume`.
  * **View `volatility_impact`:** A joined view calculating volatility (High-Low) in the 15-minute window following an `ai_news_event`.
