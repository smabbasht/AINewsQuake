# AINewsQuake Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Python 3.10+
- Docker Desktop running
- API keys from FMP and Databento

### Step 1: Setup Environment
```bash
# Navigate to project
cd AINewsQuake

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Step 2: Start Database
```bash
# Start TimescaleDB
docker-compose up -d

# Verify it's running
docker-compose ps
```

### Step 3: Initialize Database
```bash
# Create tables and hypertables
uv run python main.py --init-db --tickers NVDA --from-date 2025-01-02 --to-date 2025-01-02
```

### Step 4: Run ETL Pipeline
```bash
# Test with single ticker, single day
uv run python main.py --tickers NVDA --from-date 2025-01-02 --to-date 2025-01-02
```

### Step 5: Launch Dashboard
```bash
# Start Streamlit
uv run streamlit run app.py
```

Open browser to http://localhost:8501

---

## 📋 Common Commands

### ETL Pipeline

```bash
# Full year, all tickers (will take hours!)
uv run python main.py

# Specific date range
uv run python main.py --from-date 2025-01-01 --to-date 2025-01-31

# Specific tickers
uv run python main.py --tickers NVDA,MSFT,AAPL

# Parallel mode (faster)
uv run python main.py --parallel

# Help
uv run python main.py --help
```

### Database Management

```bash
# Start database
docker-compose up -d

# Stop database
docker-compose down

# View logs
docker-compose logs -f timescaledb

# Connect to database
docker exec -it ainewsquake-timescaledb psql -U postgres -d ainewsquake

# Backup database
docker exec ainewsquake-timescaledb pg_dump -U postgres ainewsquake > backup.sql
```

### Dashboard

```bash
# Start dashboard
uv run streamlit run app.py

# Start on different port
uv run streamlit run app.py --server.port 8502
```

---

## 🔧 Troubleshooting

### Docker Not Running
```bash
# Error: Cannot connect to Docker daemon
# Solution: Start Docker Desktop
```

### API Rate Limits
```bash
# Error: 429 Too Many Requests
# Solution: Reduce batch size or add delays in client code
```

### Database Connection Error
```bash
# Error: Connection refused
# Solution: Check if TimescaleDB is running
docker-compose ps
docker-compose restart timescaledb
```

### Import Errors
```bash
# Error: ModuleNotFoundError
# Solution: Reinstall dependencies
uv sync --force
```

---

## 📊 Expected Data Volumes

### Full Year 2025 (10 tickers)

**News Events:**
- Estimated: 5,000 - 10,000 events
- Storage: ~5-10 MB

**Market Ticks (1-minute bars):**
- Trading days: ~252
- Minutes per day: ~390 (6.5 hours)
- Total ticks: 252 × 390 × 10 = ~982,800
- Storage: ~100-200 MB

**Total Database Size:** ~200-300 MB

---

## 🎯 Target Tickers

**Titans:**
- NVDA (NVIDIA)
- MSFT (Microsoft)
- AAPL (Apple)
- GOOGL (Alphabet)
- TSLA (Tesla)

**Challengers:**
- AMD (Advanced Micro Devices)
- PLTR (Palantir)
- TSM (Taiwan Semiconductor)
- SMCI (Super Micro Computer)
- META (Meta Platforms)

---

## 📈 Dashboard Features

- **News Timeline**: Scatter plot with volatility and volume spikes
- **Volatility Heatmap**: Daily average by ticker
- **Volume Distribution**: Histogram of volume spikes
- **Top 10 Events**: Highest impact news events
- **Filters**: Ticker selection and date range

---

## 🔑 Environment Variables

Required in `.env`:
```bash
FMP_API_KEY=your_key_here
DATABENTO_API_KEY=your_key_here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ainewsquake
```

Optional (with defaults):
```bash
BATCH_SIZE=1000
MAX_RETRIES=3
RETRY_DELAY=5
ETL_START_DATE=2025-01-01
ETL_END_DATE=2025-12-31
TARGET_TICKERS=NVDA,MSFT,AAPL,GOOGL,TSLA,AMD,PLTR,TSM,SMCI,META
NEWS_KEYWORDS=AI,GPU,Blackwell,LLM,Generative,Machine Learning,Neural Network,Deep Learning
```

---

## 📚 File Structure

```
AINewsQuake/
├── src/                    # Source code
│   ├── adapters/          # API clients
│   ├── domain/            # Data models
│   ├── repositories/      # Database layer
│   └── services/          # Business logic
├── app.py                 # Streamlit dashboard
├── main.py                # ETL pipeline
├── docker-compose.yaml    # Database setup
├── pyproject.toml         # Dependencies
├── .env                   # Your configuration (not in git)
├── .env.example           # Template
└── README.md              # Full documentation
```

---

## 🎓 Course Requirements Met

✅ **Data Integration**: FMP + Databento  
✅ **Architectural Rigor**: Repository-Service pattern  
✅ **Heterogeneous Data**: Text (news) + Time Series (OHLCV)  
✅ **Storage Strategy**: TimescaleDB hypertables  
✅ **Type Safety**: Pydantic + SQLAlchemy  
✅ **Idempotency**: Upsert logic  

---

## 📞 Support

For issues or questions:
1. Check the [README.md](README.md)
2. Review the [walkthrough.md](walkthrough.md)
3. Check logs: `etl_pipeline.log`
4. Verify Docker: `docker-compose ps`

---

**Happy Data Mining! 🌊📊**
