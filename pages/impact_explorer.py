"""
Impact Explorer - Streamlit page for analyzing news impact metrics.

Features:
- Most Impactful News panel
- News Search & Impact Lookup
- Impact Distribution charts
"""

import os
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.components.navbar import render_navbar

# Page config
st.set_page_config(
    page_title="Impact Explorer - AINewsQuake",
    page_icon="💥",
    layout="wide",
)

# Load environment
load_dotenv()


# Render navbar
render_navbar("Impact")


@st.cache_resource
def get_db_connection():
    """Get database connection (cached)."""
    import psycopg2
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        st.error("❌ DATABASE_URL not found in environment")
        st.stop()
    
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(database_url)


def load_impact_data(
    ticker: str = None,
    from_date: date = None,
    to_date: date = None,
    min_impact: float = None,
    search_text: str = None
) -> pd.DataFrame:
    """Load impact analysis data with filters."""
    conn = get_db_connection()
    
    # Build query with filters
    query = """
        SELECT 
            impact_id,
            event_id,
            ticker,
            published_at,
            headline,
            sentiment_score,
            source,
            price_at_news,
            price_30min_after,
            price_impact_pct,
            volume_spike_ratio,
            volatility_impact_pct,
            high_30min,
            low_30min
        FROM news_impact_analysis
        WHERE 1=1
    """
    
    params = []
    
    if ticker and ticker != "All":
        query += " AND ticker = %s"
        params.append(ticker)
    
    if from_date:
        query += " AND published_at >= %s"
        params.append(datetime.combine(from_date, datetime.min.time()))
    
    if to_date:
        query += " AND published_at <= %s"
        params.append(datetime.combine(to_date, datetime.max.time()))
    
    if min_impact is not None:
        query += " AND ABS(price_impact_pct) >= %s"
        params.append(min_impact)
    
    if search_text:
        query += " AND headline ILIKE %s"
        params.append(f"%{search_text}%")
    
    query += " ORDER BY published_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params if params else None)
    df['published_at'] = pd.to_datetime(df['published_at'])
    
    return df


def main():
    """Main application."""
    
    # Page title
    st.title("💥 Impact Explorer")
    st.markdown("Discover how news moves markets")
    
    # Collapsible filters
    with st.expander("⚙️ Filter & Sort", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            all_tickers = ["All", "NVDA", "TSLA", "MSFT", "GOOGL", "AAPL", "AMZN", "AMD", "PLTR", "TSM", "SMCI", "META", "BLK"]
            selected_ticker = st.selectbox("Select Ticker", all_tickers, index=0)
        with col2:
            default_end = date(2025, 12, 15)
            default_start = date(2025, 1, 1)
            from_date = st.date_input("From Date", value=default_start, min_value=date(2025, 1, 1), max_value=default_end)
        with col3:
            to_date = st.date_input("To Date", value=default_end, min_value=from_date, max_value=default_end)
            
        col1, col2 = st.columns([1, 2])
        with col1:
             impact_type = st.radio("Impact Metric", ["Price Impact", "Volume Spike", "Volatility"], index=0, horizontal=True)
        with col2:
             min_impact = st.slider("Min Price Impact (%)", 0.0, 5.0, 0.0, 0.1, help="Filter news with at least this % price change")
    
    # Load data
    with st.spinner("Loading impact data..."):
        impact_df = load_impact_data(
            ticker=selected_ticker if selected_ticker != "All" else None,
            from_date=from_date,
            to_date=to_date,
            min_impact=min_impact if min_impact > 0 else None
        )
    
    if impact_df.empty:
        st.warning("⚠️ No impact data found for the selected filters.")
        st.stop()
    
    # Tab layout - Recent News as default (index 1)
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Search News", "📋 Recent News", "🔥 Most Impactful", "📊 Distributions"])
    
    # Tab 1: Search News
    with tab1:
        st.subheader("Search News & View Impact")
        
        search_text = st.text_input(
            "🔎 Search headlines",
            placeholder="e.g., 'LLM', 'AI', 'chip', 'earnings'",
            help="Search for keywords in news headlines"
        )
        
        if search_text:
            search_results = load_impact_data(
                ticker=selected_ticker if selected_ticker != "All" else None,
                from_date=from_date,
                to_date=to_date,
                search_text=search_text
            )
            
            if search_results.empty:
                st.info(f"No results found for '{search_text}'")
            else:
                st.success(f"Found {len(search_results)} news events matching '{search_text}'")
                
                # Display results
                display_search = search_results.copy()
                display_search['published_at'] = display_search['published_at'].dt.strftime('%Y-%m-%d %H:%M')
                display_search['sentiment_label'] = display_search['sentiment_score'].apply(
                    lambda x: '🟢 Positive' if x > 0.05 else ('🔴 Negative' if x < -0.05 else '🟡 Neutral')
                )
                
                st.dataframe(
                    display_search[[
                        'published_at', 'ticker', 'headline', 'sentiment_label',
                        'price_impact_pct', 'volume_spike_ratio', 'volatility_impact_pct'
                    ]],
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "published_at": "Date & Time",
                        "ticker": "Ticker",
                        "headline": st.column_config.TextColumn("Headline", width="large"),
                        "sentiment_label": "Sentiment",
                        "price_impact_pct": st.column_config.NumberColumn("Price Impact (%)", format="%.2f"),
                        "volume_spike_ratio": st.column_config.NumberColumn("Volume Spike (x)", format="%.2f"),
                        "volatility_impact_pct": st.column_config.NumberColumn("Volatility (%)", format="%.2f"),
                    }
                )
        else:
            st.info("👆 Enter a search term to find news events")
    
    # Tab 2: Recent News (DEFAULT)
    with tab2:
        st.subheader("Recent News Events")
        
        # Display most recent 50 news
        recent_df = impact_df.sort_values('published_at', ascending=False).head(50)
        display_recent = recent_df.copy()
        display_recent['published_at'] = display_recent['published_at'].dt.strftime('%Y-%m-%d %H:%M')
        display_recent['sentiment_label'] = display_recent['sentiment_score'].apply(
            lambda x: '🟢 Positive' if x > 0.05 else ('🔴 Negative' if x < -0.05 else '🟡 Neutral')
        )
        
        st.dataframe(
            display_recent[[
                'published_at', 'ticker', 'headline', 'sentiment_label',
                'price_impact_pct', 'volume_spike_ratio', 'volatility_impact_pct'
            ]],
            width='stretch',
            hide_index=True,
            column_config={
                "published_at": "Date & Time",
                "ticker": "Ticker",
                "headline": st.column_config.TextColumn("Headline", width="large"),
                "sentiment_label": "Sentiment",
                "price_impact_pct": st.column_config.NumberColumn("Price Impact (%)", format="%.2f"),
                "volume_spike_ratio": st.column_config.NumberColumn("Volume Spike (x)", format="%.2f"),
                "volatility_impact_pct": st.column_config.NumberColumn("Volatility (%)", format="%.2f"),
            }
        )
    
    # Tab 3: Most Impactful News
    with tab3:
        st.subheader("Most Impactful News Events")
        
        # Sort by selected impact type
        if impact_type == "Price Impact":
            sorted_df = impact_df.sort_values('price_impact_pct', key=abs, ascending=False)
            metric_col = 'price_impact_pct'
            metric_label = 'Price Impact (%)'
        elif impact_type == "Volume Spike":
            sorted_df = impact_df.sort_values('volume_spike_ratio', ascending=False)
            metric_col = 'volume_spike_ratio'
            metric_label = 'Volume Spike (x)'
        else:  # Volatility
            sorted_df = impact_df.sort_values('volatility_impact_pct', ascending=False)
            metric_col = 'volatility_impact_pct'
            metric_label = 'Volatility (%)'
        
        # Display top 20
        display_df = sorted_df.head(20).copy()
        display_df['published_at'] = display_df['published_at'].dt.strftime('%Y-%m-%d %H:%M')
        display_df['sentiment_label'] = display_df['sentiment_score'].apply(
            lambda x: '🟢 Positive' if x > 0.05 else ('🔴 Negative' if x < -0.05 else '🟡 Neutral')
        )
        
        st.dataframe(
            display_df[[
                'published_at', 'ticker', 'headline', 'sentiment_label',
                'price_impact_pct', 'volume_spike_ratio', 'volatility_impact_pct'
            ]],
            width='stretch',
            hide_index=True,
            column_config={
                "published_at": "Date & Time",
                "ticker": "Ticker",
                "headline": st.column_config.TextColumn("Headline", width="large"),
                "sentiment_label": "Sentiment",
                "price_impact_pct": st.column_config.NumberColumn("Price Impact (%)", format="%.2f"),
                "volume_spike_ratio": st.column_config.NumberColumn("Volume Spike (x)", format="%.2f"),
                "volatility_impact_pct": st.column_config.NumberColumn("Volatility (%)", format="%.2f"),
            }
        )
    
    # Tab 4: Distributions
    with tab4:
        st.subheader("Impact Distribution Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Price impact histogram
            fig_price = px.histogram(
                impact_df,
                x='price_impact_pct',
                nbins=50,
                title="Price Impact Distribution",
                labels={'price_impact_pct': 'Price Impact (%)'},
                color_discrete_sequence=['#667eea']
            )
            fig_price.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig_price, use_container_width=True)
        
        with col2:
            # Sentiment vs Price Impact scatter
            fig_scatter = px.scatter(
                impact_df,
                x='sentiment_score',
                y='price_impact_pct',
                color='ticker',
                title="Sentiment vs Price Impact",
                labels={
                    'sentiment_score': 'Sentiment Score',
                    'price_impact_pct': 'Price Impact (%)'
                },
                hover_data=['headline']
            )
            fig_scatter.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Volatility by ticker
        fig_vol = px.box(
            impact_df,
            x='ticker',
            y='volatility_impact_pct',
            title="Volatility Impact by Ticker",
            labels={'volatility_impact_pct': 'Volatility Impact (%)'},
            color='ticker'
        )
        fig_vol.update_layout(template='plotly_white', height=400)
        st.plotly_chart(fig_vol, use_container_width=True)


if __name__ == "__main__":
    main()
