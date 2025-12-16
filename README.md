# AINewsQuake 🌋

**Quantifying the Seismic Impact of AI News on Stock Market Volatility**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TimescaleDB](https://img.shields.io/badge/database-TimescaleDB-orange.svg)](https://www.timescale.com/)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-red.svg)](https://streamlit.io/)

## 📄 Abstract

AINewsQuake is an event-driven data pipeline that analyzes the causal relationship between AI-related news sentiment and intraday stock market volatility. By merging **"slow data"** (financial news with VADER sentiment analysis) and **"fast data"** (1-minute OHLCV market microstructure), the system quantifies how AI headlines create measurable "earthquakes" in the market.

The project focuses on **10 AI-centric stocks** (NVDA, TSLA, MSFT, GOOGL, AAPL, AMD, PLTR, TSM, SMCI, META) to study sector-specific market reactions to AI news. Using TimescaleDB for time-series optimization and a Repository-Service architecture for clean separation of concerns, AINewsQuake provides an interactive dashboard for exploring news-volatility correlations across the full year of 2025.

**Key Insight:** AI news doesn't just inform markets—it moves them. This project measures exactly how much.

---

## 🎯 Why These Tickers?

We selected **10 stocks deeply embedded in the AI ecosystem**, representing different layers of the AI value chain:

### **Titans (Established AI Leaders)**
- **NVDA** (NVIDIA) - GPU infrastructure, AI chips
- **MSFT** (Microsoft) - Azure AI, OpenAI partnership, Copilot
- **GOOGL** (Alphabet) - DeepMind, Gemini, AI research
- **AAPL** (Apple) - On-device AI, Apple Intelligence
- **META** (Meta) - LLaMA, AI-driven ads, metaverse

### **Challengers (Emerging AI Players)**
- **TSLA** (Tesla) - Autonomous driving, Optimus robotics
- **AMD** - AI chip competitor to NVIDIA
- **PLTR** (Palantir) - AI-powered analytics, government AI
- **TSM** (Taiwan Semi) - Chip manufacturing for AI hardware
- **SMCI** (Super Micro) - AI server infrastructure

**Rationale:** These companies are **AI-native or AI-dependent**, making them highly sensitive to AI news sentiment. Their stock prices react measurably to AI breakthroughs, regulatory changes, and competitive dynamics—perfect for studying news-driven volatility.

---

## 🏗️ Technology Stack

### **Data Sources**
- **Finnhub API** - Historical company news (2025-01-01 to 2025-12-31)
  - *Why?* Free tier supports 60 calls/minute with historical access
  - *Alternative considered:* Alpha Vantage (rejected: only 25 calls/day, no historical depth)
- **Databento API** - 1-minute OHLCV bars (market microstructure)
  - *Why?* Professional-grade tick data with Python SDK
  - *Alternative considered:* Yahoo Finance (rejected: unreliable historical data)

### **Database**
- **TimescaleDB** (PostgreSQL extension)
  - *Why?* Hypertables optimize time-series queries (10x faster than vanilla PostgreSQL)
  - *Design choice:* Separate tables for news (relational) and market ticks (hypertable)
  - *Alternative considered:* InfluxDB (rejected: poor support for complex joins)

### **Backend**
- **Python 3.12** with async/await
- **SQLAlchemy 2.0** - Async ORM for database operations
- **Pydantic** - Type-safe data validation
- **psycopg2** - Synchronous PostgreSQL driver (for Streamlit compatibility)

### **Frontend**
- **Streamlit** - Interactive dashboard
  - *Why?* Rapid prototyping, built-in caching, native Plotly support
  - *Alternative considered:* Dash (rejected: more verbose, slower iteration)
- **Plotly** - Interactive charts (candlestick, scatter, heatmap)

### **Sentiment Analysis**
- **VADER (Valence Aware Dictionary and sEntiment Reasoner)**
  - *Why?* Optimized for financial text, no training required
  - *Output:* Compound score from -1.0 (negative) to +1.0 (positive)
  - *Alternative considered:* FinBERT (rejected: too slow for 30K+ news items)

### **Deployment**
- **Docker Compose** - TimescaleDB containerization
- **uv** - Fast Python package manager (10x faster than pip)

---

## 🧠 Design Choices

### **1. Repository-Service Pattern**
**Why?** Clean separation between data access (repositories) and business logic (services).
- **Repositories:** Handle database CRUD operations
- **Services:** Orchestrate ETL pipeline, coordinate between adapters and repositories
- **Adapters:** Wrap external APIs (Finnhub, Databento)

**Benefit:** Easy to swap data sources without touching business logic.

### **2. Idempotent ETL**
**Why?** Re-running the pipeline doesn't duplicate data.
- **Implementation:** Unique constraints on `event_id` (news) and `(time, ticker)` (market ticks)
- **Upsert logic:** `ON CONFLICT DO NOTHING` for news, `ON CONFLICT DO UPDATE` for market data

**Benefit:** Safe to retry failed runs without data corruption.

### **3. Smart Backfill Strategy**
**Why?** Finnhub returns max 250 news items per request.
- **Implementation:** Work backwards from most recent date, using oldest fetched date as new end date
- **Benefit:** Complete coverage without gaps, even when news volume varies

### **4. Async Database Queries (ETL) + Sync Queries (Dashboard)**
**Why?** Streamlit doesn't play well with asyncio event loops.
- **ETL:** Uses `asyncpg` for concurrent database writes
- **Dashboard:** Uses `psycopg2` for Streamlit compatibility

**Benefit:** Best of both worlds—fast ETL, stable dashboard.

### **5. TimescaleDB Hypertables**
**Why?** Market ticks are time-series data (1-minute granularity).
- **Partitioning:** Automatic time-based partitioning for efficient queries
- **Compression:** Built-in compression for older data
- **Indexing:** Optimized for time-range queries

**Benefit:** 10x faster queries on 1M+ market ticks.

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AINewsQuake Pipeline                    │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Finnhub    │      │  Databento   │      │  TimescaleDB │
│  (News API)  │─────▶│ (Market API) │─────▶│  (Database)  │
└──────────────┘      └──────────────┘      └──────────────┘
       │                     │                      │
       │                     │                      │
       ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│                    ETL Pipeline (main.py)                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │  Adapters  │─▶│  Services  │─▶│    Repositories        │ │
│  │ (API Wrap) │  │ (ETL Logic)│  │ (DB Layer)             │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Streamlit App  │
                  │   (Dashboard)   │
                  └─────────────────┘
```

### **Data Flow**
1. **Extract:** Finnhub client fetches news → VADER calculates sentiment
2. **Extract:** Databento client fetches 1-minute OHLCV bars
3. **Transform:** Services validate data with Pydantic schemas
4. **Load:** Repositories upsert to TimescaleDB (idempotent)
5. **Visualize:** Streamlit queries database → Plotly renders interactive charts

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Finnhub API key ([get one here](https://finnhub.io/register))
- Databento API key ([get one here](https://databento.com/))

### 1. Clone & Setup
```bash
cd AINewsQuake
uv sync
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your API keys
```

**Required variables:**
```bash
FINNHUB_API_KEY=your_finnhub_api_key_here
DATABENTO_API_KEY=your_databento_api_key_here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ainewsquake
```

### 3. Start TimescaleDB
```bash
docker-compose up -d
```

### 4. Initialize Database
```bash
uv run python main.py --init-db --tickers NVDA --from-date 2025-01-01 --to-date 2025-01-01
```

### 5. Run ETL Pipeline
```bash
# Fetch news only (saves Databento API calls)
uv run python main.py --tickers NVDA --from-date 2025-01-01 --to-date 2025-12-31 --news-only

# Fetch news + market data
uv run python main.py --tickers NVDA --from-date 2025-01-01 --to-date 2025-12-31

# Fetch all tickers (will take ~6 hours)
uv run python main.py --from-date 2025-01-01 --to-date 2025-12-31
```

### 6. Launch Dashboard
```bash
uv run streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501)

---

## 📊 Dashboard Features

- **Interactive Candlestick Chart** - Zoom, pan, explore price movements
- **News Markers** - Color-coded by sentiment (🟢 positive, 🔴 negative, 🟡 neutral)
- **Hover Details** - See headline + sentiment score + price on hover
- **Volume Bars** - Trading volume with green/red coloring
- **Sentiment Timeline** - Track sentiment trends over time
- **Ticker Selector** - Switch between 10 AI stocks
- **Date Range Filter** - Focus on specific periods

---

## 🛠️ CLI Usage

```bash
# Show help
uv run python main.py --help

# Fetch specific tickers
uv run python main.py --tickers NVDA,TSLA,MSFT

# Custom date range
uv run python main.py --from-date 2025-06-01 --to-date 2025-06-30

# News only (skip market data)
uv run python main.py --tickers GOOGL --news-only

# Parallel execution (faster)
uv run python main.py --parallel
```

---

## 🗄️ Database Schema

### **`ai_news_events`** (Relational Table)
```sql
event_id        VARCHAR(255) PRIMARY KEY
ticker          VARCHAR(10)
published_at    TIMESTAMP WITH TIME ZONE
headline        TEXT
source          VARCHAR(255)
sentiment_score FLOAT  -- VADER compound score (-1.0 to +1.0)
```

### **`market_ticks`** (TimescaleDB Hypertable)
```sql
time    TIMESTAMP WITH TIME ZONE PRIMARY KEY
ticker  VARCHAR(10) PRIMARY KEY
open    FLOAT
high    FLOAT
low     FLOAT
close   FLOAT
volume  INTEGER
```

**Partitioning:** Automatic time-based partitioning by week  
**Compression:** Enabled for data older than 7 days

---

## 📚 Project Context

**Course:** Data Management (Laurea Magistrale in Data Science)  
**University:** Università degli Studi di Milano-Bicocca  
**Submission Deadline:** January 14, 2026  

**Focus Areas:**
- Heterogeneous data integration (text + time-series)
- Architectural rigor (Repository-Service pattern)
- Storage optimization (TimescaleDB hypertables)
- Real-time analytics (Streamlit dashboard)

---

## 🐛 Troubleshooting

### Database Connection Issues
```bash
docker-compose ps          # Check if running
docker-compose logs        # View logs
docker-compose restart     # Restart container
```

### API Rate Limits
- **Finnhub:** 60 calls/minute (built-in 1-second delay)
- **Databento:** Adjust batch size if hitting limits

### Import Errors
```bash
uv sync --force  # Reinstall dependencies
```

---

## 📄 License

GNU General Public License v3.0 - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Finnhub** - Historical company news API
- **Databento** - Professional market microstructure data
- **TimescaleDB** - Time-series database optimization
- **Streamlit** - Rapid dashboard prototyping
- **VADER** - Financial sentiment analysis

---

**Built with ❤️ to quantify how AI news creates market earthquakes**
