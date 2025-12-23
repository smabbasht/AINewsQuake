"""
Analytics Page - Advanced analysis and insights.
"""

import os
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.navbar import render_navbar

# Load environment
load_dotenv()

# Page config
st.set_page_config(
    page_title="Analytics - AINewsQuake",
    page_icon="📈",
    layout="wide",
)

# Render navbar
render_navbar("Analytics")

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


def load_analytics_data():
    """Load data for analytics."""
    conn = get_db_connection()
    
    query = """
        SELECT 
            ticker,
            published_at,
            sentiment_score,
            price_impact_pct,
            volume_spike_ratio,
            volatility_impact_pct,
            EXTRACT(HOUR FROM published_at) as hour_of_day,
            EXTRACT(DOW FROM published_at) as day_of_week
        FROM news_impact_analysis
        WHERE price_impact_pct IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    df['published_at'] = pd.to_datetime(df['published_at'])
    
    return df


# Main content
st.title("📈 Analytics & Insights")
st.markdown("Advanced analysis of news impact patterns")

# Load data
with st.spinner("Loading analytics data..."):
    df = load_analytics_data()

if df.empty:
    st.warning("No data available for analytics")
    st.stop()

# Collapsible filters
with st.expander("⚙️ Analytics Filters", expanded=False):
    selected_tickers = st.multiselect(
        "Select Tickers",
        options=sorted(df['ticker'].unique()),
        default=sorted(df['ticker'].unique())[:3]
    )

if selected_tickers:
    df = df[df['ticker'].isin(selected_tickers)]

# Tab layout - directly below subtitle
tab1, tab2, tab3 = st.tabs(["⏰ Time Analysis", "🔗 Correlations", "📊 Ticker Comparison"])

# Tab 1: Time Analysis
with tab1:
    st.subheader("Impact by Time of Day")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Hour of day analysis
        hourly_impact = df.groupby('hour_of_day').agg({
            'price_impact_pct': ['mean', 'count'],
            'volatility_impact_pct': 'mean'
        }).reset_index()
        
        hourly_impact.columns = ['hour', 'avg_price_impact', 'count', 'avg_volatility']
        
        fig_hour = go.Figure()
        fig_hour.add_trace(go.Bar(
            x=hourly_impact['hour'],
            y=hourly_impact['avg_price_impact'],
            name='Avg Price Impact',
            marker_color='#667eea'
        ))
        
        fig_hour.update_layout(
            title="Average Price Impact by Hour",
            xaxis_title="Hour of Day (ET)",
            yaxis_title="Avg Price Impact (%)",
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(fig_hour, use_container_width=True)
    
    with col2:
        # Day of week analysis
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_impact = df.groupby('day_of_week').agg({
            'price_impact_pct': 'mean',
            'volume_spike_ratio': 'mean'
        }).reset_index()
        
        daily_impact['day_name'] = daily_impact['day_of_week'].apply(lambda x: day_names[int(x)])
        
        fig_day = go.Figure()
        fig_day.add_trace(go.Bar(
            x=daily_impact['day_name'],
            y=daily_impact['price_impact_pct'],
            marker_color='#f093fb'
        ))
        
        fig_day.update_layout(
            title="Average Price Impact by Day of Week",
            xaxis_title="Day",
            yaxis_title="Avg Price Impact (%)",
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(fig_day, use_container_width=True)

# Tab 2: Correlations
with tab2:
    st.subheader("Correlation Analysis")
    
    # Sentiment vs Impact scatter
    fig_corr = px.scatter(
        df,
        x='sentiment_score',
        y='price_impact_pct',
        color='ticker',
        size='volatility_impact_pct',
        title="Sentiment vs Price Impact (size = volatility)",
        labels={
            'sentiment_score': 'Sentiment Score',
            'price_impact_pct': 'Price Impact (%)',
            'volatility_impact_pct': 'Volatility (%)'
        },
        trendline="ols"
    )
    fig_corr.update_layout(template='plotly_white', height=500)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # Correlation matrix
    st.subheader("Correlation Matrix")
    corr_df = df[['sentiment_score', 'price_impact_pct', 'volume_spike_ratio', 'volatility_impact_pct']].corr()
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=corr_df.values,
        x=['Sentiment', 'Price Impact', 'Volume Spike', 'Volatility'],
        y=['Sentiment', 'Price Impact', 'Volume Spike', 'Volatility'],
        colorscale='RdBu',
        zmid=0,
        text=corr_df.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 14},
        colorbar=dict(title="Correlation")
    ))
    
    fig_heatmap.update_layout(
        title="Metric Correlations",
        template='plotly_white',
        height=400
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)

# Tab 3: Ticker Comparison
with tab3:
    st.subheader("Ticker Comparison")
    
    # Average metrics by ticker
    ticker_stats = df.groupby('ticker').agg({
        'price_impact_pct': ['mean', 'std'],
        'volume_spike_ratio': 'mean',
        'volatility_impact_pct': 'mean',
        'sentiment_score': 'mean'
    }).reset_index()
    
    ticker_stats.columns = ['ticker', 'avg_price_impact', 'std_price_impact', 
                            'avg_volume_spike', 'avg_volatility', 'avg_sentiment']
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_ticker_impact = px.bar(
            ticker_stats.sort_values('avg_price_impact'),
            x='avg_price_impact',
            y='ticker',
            orientation='h',
            title="Average Price Impact by Ticker",
            labels={'avg_price_impact': 'Avg Price Impact (%)'},
            color='avg_price_impact',
            color_continuous_scale='RdYlGn'
        )
        fig_ticker_impact.update_layout(template='plotly_white', height=400)
        st.plotly_chart(fig_ticker_impact, use_container_width=True)
    
    with col2:
        fig_ticker_vol = px.bar(
            ticker_stats.sort_values('avg_volatility', ascending=False),
            x='ticker',
            y='avg_volatility',
            title="Average Volatility by Ticker",
            labels={'avg_volatility': 'Avg Volatility (%)'},
            color='avg_volatility',
            color_continuous_scale='Reds'
        )
        fig_ticker_vol.update_layout(template='plotly_white', height=400)
        st.plotly_chart(fig_ticker_vol, use_container_width=True)
