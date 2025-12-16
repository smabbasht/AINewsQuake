# AINewsQuake Architecture Diagram

```mermaid
graph TB
    subgraph "External APIs"
        FMP[FMP API<br/>Financial News]
        DB[Databento API<br/>Market Data OHLCV]
    end
    
    subgraph "Adapter Layer"
        FMPClient[FMP Client<br/>- Keyword filtering<br/>- EST→UTC conversion<br/>- Rate limiting]
        DBClient[Databento Client<br/>- 1-min bars<br/>- Batch processing<br/>- Rate limiting]
    end
    
    subgraph "Domain Layer"
        NewsEvent[NewsEvent Schema<br/>- event_id<br/>- ticker<br/>- published_at<br/>- headline]
        MarketTick[MarketTick Schema<br/>- time<br/>- ticker<br/>- OHLCV<br/>- volume]
        VolImpact[VolatilityImpact Schema<br/>- volatility_15min<br/>- volume_spike]
    end
    
    subgraph "Service Layer"
        Pipeline[Pipeline Service<br/>- ETL orchestration<br/>- Sequential/Parallel modes<br/>- Progress tracking]
    end
    
    subgraph "Repository Layer"
        Repo[TimescaleDB Repository<br/>- Async SQLAlchemy<br/>- Idempotent upserts<br/>- Hypertable management]
    end
    
    subgraph "Database"
        NewsTable[(ai_news_events<br/>Relational Table)]
        TicksTable[(market_ticks<br/>Hypertable)]
        View[(volatility_impact<br/>View)]
    end
    
    subgraph "Application Layer"
        CLI[main.py<br/>ETL Pipeline CLI<br/>- Date ranges<br/>- Ticker selection<br/>- Init DB]
        Dashboard[app.py<br/>Streamlit Dashboard<br/>- Interactive filters<br/>- Visualizations<br/>- Metrics]
    end
    
    FMP --> FMPClient
    DB --> DBClient
    
    FMPClient --> NewsEvent
    DBClient --> MarketTick
    
    NewsEvent --> Pipeline
    MarketTick --> Pipeline
    
    Pipeline --> Repo
    
    Repo --> NewsTable
    Repo --> TicksTable
    
    NewsTable --> View
    TicksTable --> View
    
    View --> VolImpact
    
    CLI --> Pipeline
    Dashboard --> Repo
    
    VolImpact --> Dashboard
    
    style FMP fill:#667eea
    style DB fill:#667eea
    style FMPClient fill:#764ba2
    style DBClient fill:#764ba2
    style Pipeline fill:#f093fb
    style Repo fill:#4facfe
    style NewsTable fill:#43e97b
    style TicksTable fill:#43e97b
    style View fill:#fa709a
    style CLI fill:#fee140
    style Dashboard fill:#fee140
```

## Data Flow

### ETL Pipeline (main.py)

```mermaid
sequenceDiagram
    participant CLI as main.py
    participant PS as Pipeline Service
    participant FMP as FMP Client
    participant DB as Databento Client
    participant Repo as Repository
    participant TSDB as TimescaleDB
    
    CLI->>PS: run_etl(tickers, dates)
    
    Note over PS,FMP: Step 1: Extract News
    loop For each ticker
        PS->>FMP: fetch_stock_news()
        FMP-->>PS: NewsEvent[]
    end
    
    Note over PS,Repo: Step 2: Load News
    PS->>Repo: upsert_news_events()
    Repo->>TSDB: INSERT ON CONFLICT DO NOTHING
    TSDB-->>Repo: Inserted count
    Repo-->>PS: Success
    
    Note over PS,DB: Step 3: Extract Market Data
    loop For each ticker
        PS->>DB: fetch_ohlcv_bars_batch()
        DB-->>PS: MarketTick[]
    end
    
    Note over PS,Repo: Step 4: Load Market Data
    PS->>Repo: upsert_market_ticks()
    Repo->>TSDB: Batch INSERT
    TSDB-->>Repo: Inserted count
    Repo-->>PS: Success
    
    PS-->>CLI: ETL Complete
```

### Dashboard Query Flow (app.py)

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Repo as Repository
    participant TSDB as TimescaleDB
    
    User->>UI: Select ticker & date range
    UI->>Repo: get_volatility_impact(ticker, dates)
    Repo->>TSDB: SELECT FROM volatility_impact
    TSDB-->>Repo: VolatilityImpact[]
    Repo-->>UI: Data
    UI->>UI: Create visualizations
    UI-->>User: Display dashboard
```

## Technology Stack

```mermaid
graph LR
    subgraph "Language & Runtime"
        Python[Python 3.10+<br/>Type Hints<br/>Async/Await]
    end
    
    subgraph "Data Validation"
        Pydantic[Pydantic 2.5+<br/>Schema Validation<br/>Type Coercion]
    end
    
    subgraph "Database"
        TimescaleDB[TimescaleDB<br/>PostgreSQL 15<br/>Hypertables]
        SQLAlchemy[SQLAlchemy 2.0<br/>Async ORM<br/>Migrations]
    end
    
    subgraph "API Clients"
        Requests[Requests<br/>Retry Logic<br/>Rate Limiting]
        HTTPX[HTTPX<br/>Async Support]
    end
    
    subgraph "Visualization"
        Streamlit[Streamlit<br/>Interactive UI]
        Plotly[Plotly<br/>Rich Charts]
    end
    
    subgraph "Infrastructure"
        Docker[Docker Compose<br/>Container Orchestration]
        UV[UV<br/>Fast Package Manager]
    end
    
    Python --> Pydantic
    Python --> SQLAlchemy
    SQLAlchemy --> TimescaleDB
    Python --> Requests
    Python --> HTTPX
    Python --> Streamlit
    Streamlit --> Plotly
    TimescaleDB --> Docker
    Python --> UV
```

## Design Patterns

### Repository Pattern
```
┌─────────────────────────────────────────┐
│         Service Layer                   │
│  (Business Logic - Pipeline Service)    │
└─────────────────┬───────────────────────┘
                  │ Depends on
                  ▼
┌─────────────────────────────────────────┐
│      Repository Interface                │
│  (Abstract CRUD Operations)              │
└─────────────────┬───────────────────────┘
                  │ Implements
                  ▼
┌─────────────────────────────────────────┐
│   TimescaleDB Repository                 │
│  (Concrete Implementation)               │
└─────────────────┬───────────────────────┘
                  │ Accesses
                  ▼
┌─────────────────────────────────────────┐
│         Database                         │
│  (TimescaleDB - Data Storage)            │
└─────────────────────────────────────────┘
```

### Dependency Injection
```python
# Service accepts dependencies
pipeline = PipelineService(
    fmp_client=FMPClient(api_key),      # Injected
    databento_client=DatabentoClient(api_key),  # Injected
    repository=TimescaleRepository(db_url)      # Injected
)

# Easy to test with mocks
pipeline_test = PipelineService(
    fmp_client=MockFMPClient(),
    databento_client=MockDatabentoClient(),
    repository=MockRepository()
)
```

## Key Features

### Idempotency
```sql
-- News events: unique constraint prevents duplicates
INSERT INTO ai_news_events (...)
ON CONFLICT (ticker, published_at, headline)
DO NOTHING;

-- Market ticks: primary key prevents duplicates
INSERT INTO market_ticks (...)
ON CONFLICT (time, ticker)
DO NOTHING;
```

### Time-Series Optimization
```sql
-- Convert to hypertable (automatic partitioning)
SELECT create_hypertable(
    'market_ticks',
    'time',
    chunk_time_interval => INTERVAL '1 day'
);

-- Efficient time-range queries
SELECT * FROM market_ticks
WHERE time BETWEEN '2025-01-01' AND '2025-01-31'
  AND ticker = 'NVDA';
```

### Volatility Calculation
```sql
-- 15-minute window after news event
SELECT
    ne.event_id,
    MAX(mt.high) - MIN(mt.low) AS volatility_15min
FROM ai_news_events ne
LEFT JOIN market_ticks mt
    ON ne.ticker = mt.ticker
    AND mt.time BETWEEN ne.published_at 
                    AND ne.published_at + INTERVAL '15 minutes'
GROUP BY ne.event_id;
```

---

**Architecture designed for scalability, maintainability, and type safety** 🏗️
