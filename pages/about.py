"""
About Page - Project information in an engaging format.
"""

import streamlit as st

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.navbar import render_navbar

# Page config
st.set_page_config(
    page_title="AINewsQuake",
    page_icon="🌋",
    layout="wide",
)

# Render navbar
render_navbar("About")

# Centered hero section (no title needed)
st.markdown("""
<div style='text-align: center; padding: 0.5rem 0 1.5rem 0;'>
    <h2 style='color: #2d3748; font-size: 2rem; margin-bottom: 1rem;'>Quantifying Market Earthquakes</h2>
    <p style='color: #4a5568; font-size: 1.1rem; max-width: 700px; margin: 0 auto 2rem auto;'>
        AINewsQuake analyzes how AI-related news creates measurable "earthquakes" in the stock market. 
        We merge <strong>news sentiment</strong> with <strong>1-minute market data</strong> to quantify 
        the real impact of headlines on price volatility.
    </p>
</div>
""", unsafe_allow_html=True)

# Perfectly centered metrics using custom HTML grid with equal columns
st.markdown("""
<div style='display: flex; justify-content: space-between; align-items: flex-start; max-width: 900px; margin: 0 auto 2rem auto;'>
    <div style='flex: 1; text-align: center;'>
        <div style='color: #718096; font-size: 0.875rem; margin-bottom: 0.25rem;'>📰 News Events</div>
        <div style='color: #2d3748; font-size: 2rem; font-weight: 600;'>47,071</div>
    </div>
    <div style='flex: 1; text-align: center;'>
        <div style='color: #718096; font-size: 0.875rem; margin-bottom: 0.25rem;'>📊 Market Ticks</div>
        <div style='color: #2d3748; font-size: 2rem; font-weight: 600;'>1.58M</div>
    </div>
    <div style='flex: 1; text-align: center;'>
        <div style='color: #718096; font-size: 0.875rem; margin-bottom: 0.25rem;'>💥 Impact Records</div>
        <div style='color: #2d3748; font-size: 2rem; font-weight: 600;'>28,899</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

st.markdown("---")

# Three columns for key info using native Streamlit cards for perfect structure
col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    with st.container(border=True):
        st.markdown("#### 🎯 Research Question")
        st.markdown('**"How do AI news events impact intraday stock volatility?"**')
        st.caption("We answer this with three metrics:")
        st.markdown("""
        - **Price Impact**: % change in 30 min
        - **Volume Spike**: Trading vs baseline
        - **Volatility**: Price swing magnitude
        """)

with col2:
    with st.container(border=True):
        st.markdown("#### 🏗️ Tech Stack")
        st.markdown("""
        - **Database**: TimescaleDB
        - **Backend**: Python 3.12
        - **ETL**: Pandas
        - **Frontend**: Streamlit + Plotly
        - **APIs**: Finnhub, Databento
        - **Sentiment**: VADER
        """)

with col3:
    with st.container(border=True):
        st.markdown("#### 📊 AI Stocks")
        st.markdown("""
        **Titans:**  
        NVDA, MSFT, GOOGL, AAPL, AMZN, META
        
        **Challengers:**  
        TSLA, AMD, PLTR, TSM, SMCI, BLK
        """)
        st.caption("_Selected for AI-native operations and high sensitivity to AI news_")

st.markdown("---")

# Impact metrics explanation
st.markdown("### 🔬 How We Measure Impact")

tab1, tab2, tab3 = st.tabs(["💰 Price Impact", "📊 Volume Spike", "⚡ Volatility"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        **Formula:**
        ```
        (price_after - price_before) / price_before × 100
        ```
        
        **What it means:**  
        Percentage price change within 30 minutes of news publication
        """)
    with col2:
        st.markdown("""
        **Example:**
        - News at 10:00 AM, price $100
        - Price at 10:30 AM = $102
        - **Impact: +2.0%** ✅
        """)

with tab2:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        **Formula:**
        ```
        volume_30min / avg_volume_2h_baseline
        ```
        
        **What it means:**  
        How much trading volume increased compared to normal activity
        """)
    with col2:
        st.markdown("""
        **Example:**
        - Normal: 10K shares/min
        - After news: 450K in 30 min
        - **Spike: 1.5x** 📈
        """)

with tab3:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        **Formula:**
        ```
        (high_30min - low_30min) / price_at_news × 100
        ```
        
        **What it means:**  
        Price swing magnitude in the 30-minute window after news
        """)
    with col2:
        st.markdown("""
        **Example:**
        - Price at news: $100
        - High: $105, Low: $98
        - **Volatility: 7.0%** ⚡
        """)

st.markdown("---")

# Architecture
st.markdown("### 🏛️ Architecture")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    with st.container(border=True):
        st.markdown("""
        **Repository-Service Pattern**
        
        - **Adapters** → Wrap external APIs (Finnhub)
        - **Services** → Orchestrate ETL pipeline
        - **Repositories** → Handle database operations
        - **Components** → Reusable UI elements
        
        **Why?** Clean separation of concerns, easy to swap data sources
        """)

with col2:
    with st.container(border=True):
        st.markdown("""
        **Key Features**
        
        ✅ Idempotent ETL  
        ✅ Smart backfill  
        ✅ Time-series optimized  
        ✅ Real-time dashboard  
        """)

st.markdown("---")

# Footer
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **📚 Academic Context**
    
    Data Management Course  
    Università Milano-Bicocca  
    Data Science MSc  
    """)

with col2:
    st.markdown("""
    **🙏 Powered By**
    
    Finnhub • Databento  
    TimescaleDB • Streamlit  
    VADER • Plotly  
    """)

with col3:
    st.markdown("""
    **📄 License**
    
    GNU GPL v3.0  
    Open Source  
    """)
