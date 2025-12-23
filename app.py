"""
AINewsQuake Interactive Dashboard.

Modern dashboard for exploring AI news impact on stock volatility.
"""

import os
from datetime import date, datetime, timedelta
from typing import Tuple
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.components.navbar import render_navbar

# Page configuration
st.set_page_config(
    page_title="Price Chart - AINewsQuake",
    page_icon="📊",
    layout="wide",
)

# Load environment variables
load_dotenv()


# Render navbar
render_navbar("Chart")


@st.cache_resource
def get_db_connection():
    """Get database connection (cached)."""
    import psycopg2
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        st.error("❌ DATABASE_URL not found in environment")
        st.stop()
    
    # Convert asyncpg URL to psycopg2 URL
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    return psycopg2.connect(database_url)


def fetch_news_and_market_data(
    ticker: str,
    from_date: date,
    to_date: date,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch news events and market ticks for a ticker."""
    conn = get_db_connection()
    
    # Fetch news events
    news_query = """
        SELECT 
            event_id,
            ticker,
            published_at,
            headline,
            source,
            sentiment_score
        FROM ai_news_events
        WHERE ticker = %s
        AND published_at >= %s
        AND published_at <= %s
        ORDER BY published_at ASC
    """
    
    news_df = pd.read_sql_query(
        news_query,
        conn,
        params=(ticker, datetime.combine(from_date, datetime.min.time()), 
                datetime.combine(to_date, datetime.max.time()))
    )
    
    # Fetch market ticks
    market_query = """
        SELECT 
            ticker,
            time,
            open,
            high,
            low,
            close,
            volume
        FROM market_ticks
        WHERE ticker = %s
        AND time >= %s
        AND time <= %s
        ORDER BY time ASC
    """
    
    market_df = pd.read_sql_query(
        market_query,
        conn,
        params=(ticker, datetime.combine(from_date, datetime.min.time()),
                datetime.combine(to_date, datetime.max.time()))
    )
    
    return news_df, market_df


def create_price_chart_with_news(news_df: pd.DataFrame, market_df: pd.DataFrame, ticker: str):
    """Create interactive price chart with news annotations."""
    
    # Resample market data to hourly for cleaner visualization
    market_df['time'] = pd.to_datetime(market_df['time'])
    market_df = market_df.set_index('time')
    hourly = market_df.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    hourly = hourly.reset_index()
    
    # Create subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{ticker} Price Chart with News Events', 'Volume', 'Sentiment Timeline'),
        row_heights=[0.6, 0.2, 0.2],
    )
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=hourly['time'],
            open=hourly['open'],
            high=hourly['high'],
            low=hourly['low'],
            close=hourly['close'],
            name='Price',
            increasing_line_color='#48bb78',
            decreasing_line_color='#f56565',
        ),
        row=1, col=1
    )
    
    # Add news markers on price chart
    if not news_df.empty:
        news_df['published_at'] = pd.to_datetime(news_df['published_at'])
        
        # Merge news with closest market price
        news_with_price = pd.merge_asof(
            news_df.sort_values('published_at'),
            hourly[['time', 'close']].rename(columns={'time': 'published_at'}),
            on='published_at',
            direction='nearest'
        )
        
        # Categorize by sentiment
        positive_news = news_with_price[news_with_price['sentiment_score'] > 0.05]
        negative_news = news_with_price[news_with_price['sentiment_score'] < -0.05]
        neutral_news = news_with_price[
            (news_with_price['sentiment_score'] >= -0.05) & 
            (news_with_price['sentiment_score'] <= 0.05)
        ]
        
        # Add positive news markers
        if not positive_news.empty:
            fig.add_trace(
                go.Scatter(
                    x=positive_news['published_at'],
                    y=positive_news['close'],
                    mode='markers',
                    name='Positive News',
                    marker=dict(
                        symbol='triangle-up',
                        size=12,
                        color='#48bb78',
                        line=dict(width=1, color='white')
                    ),
                    text=positive_news['headline'],
                    customdata=positive_news['sentiment_score'],
                    hovertemplate='<b>%{text}</b><br>Sentiment: %{customdata:.3f}<br>Price: $%{y:.2f}<extra></extra>',
                ),
                row=1, col=1
            )
        
        # Add negative news markers
        if not negative_news.empty:
            fig.add_trace(
                go.Scatter(
                    x=negative_news['published_at'],
                    y=negative_news['close'],
                    mode='markers',
                    name='Negative News',
                    marker=dict(
                        symbol='triangle-down',
                        size=12,
                        color='#f56565',
                        line=dict(width=1, color='white')
                    ),
                    text=negative_news['headline'],
                    customdata=negative_news['sentiment_score'],
                    hovertemplate='<b>%{text}</b><br>Sentiment: %{customdata:.3f}<br>Price: $%{y:.2f}<extra></extra>',
                ),
                row=1, col=1
            )
        
        # Add neutral news markers
        if not neutral_news.empty:
            fig.add_trace(
                go.Scatter(
                    x=neutral_news['published_at'],
                    y=neutral_news['close'],
                    mode='markers',
                    name='Neutral News',
                    marker=dict(
                        symbol='circle',
                        size=10,
                        color='#ed8936',
                        line=dict(width=1, color='white')
                    ),
                    text=neutral_news['headline'],
                    customdata=neutral_news['sentiment_score'],
                    hovertemplate='<b>%{text}</b><br>Sentiment: %{customdata:.3f}<br>Price: $%{y:.2f}<extra></extra>',
                ),
                row=1, col=1
            )
    
    # Add volume bars
    colors = ['#48bb78' if close >= open else '#f56565' 
              for close, open in zip(hourly['close'], hourly['open'])]
    
    fig.add_trace(
        go.Bar(
            x=hourly['time'],
            y=hourly['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7,
        ),
        row=2, col=1
    )
    
    # Add sentiment timeline
    if not news_df.empty:
        news_df_sorted = news_df.sort_values('published_at')
        fig.add_trace(
            go.Scatter(
                x=news_df_sorted['published_at'],
                y=news_df_sorted['sentiment_score'],
                mode='markers+lines',
                name='Sentiment',
                marker=dict(
                    size=8,
                    color=news_df_sorted['sentiment_score'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(
                        title="Sentiment",
                        y=0.15,
                        len=0.2,
                    ),
                ),
                line=dict(color='rgba(102, 126, 234, 0.3)', width=1),
                text=news_df_sorted['headline'],
                hovertemplate='<b>%{text}</b><br>Sentiment: %{y:.3f}<extra></extra>',
            ),
            row=3, col=1
        )
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=3, col=1)
    
    # Update layout
    fig.update_layout(
        height=900,
        template='plotly_white',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis3_title="Date",
        yaxis_title="Price ($)",
        yaxis2_title="Volume",
        yaxis3_title="Sentiment",
        margin=dict(l=60, r=60, t=80, b=60),
    )
    
    # Remove rangeslider
    fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
    
    return fig


def main():
    """Main Streamlit application."""
    
    # Page title
    st.title("📊 Price Chart with News Annotations")
    st.markdown("Interactive candlestick chart showing news sentiment markers")
    
    # Collapsible filters
    all_tickers = ["NVDA", "TSLA", "MSFT", "GOOGL", "AAPL", "AMZN", "AMD", "PLTR", "TSM", "SMCI", "META", "BLK"]
    default_end = date(2025, 12, 15)
    default_start = date(2025, 1, 1)

    with st.expander("⚙️ Chart Configuration", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            selected_ticker = st.selectbox("Select Ticker", all_tickers, index=0)
        with f_col2:
            from_date = st.date_input("From Date", value=default_start, min_value=date(2025, 1, 1), max_value=default_end)
        with f_col3:
            to_date = st.date_input("To Date", value=default_end, min_value=from_date, max_value=default_end)
    
    # Fetch data
    with st.spinner(f"Loading data for {selected_ticker}..."):
        try:
            news_df, market_df = fetch_news_and_market_data(selected_ticker, from_date, to_date)
        except Exception as e:
            st.error(f"❌ Failed to fetch data: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()
    
    if news_df.empty and market_df.empty:
        st.warning(f"⚠️ No data found for {selected_ticker} in the selected date range.")
        st.stop()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📰 News Events",
            f"{len(news_df):,}",
            help="Total news events with sentiment scores"
        )
    
    with col2:
        if not news_df.empty:
            avg_sentiment = news_df['sentiment_score'].mean()
            st.metric(
                "🙃 Avg Sentiment",
                f"{avg_sentiment:.3f}",
                delta=f"{'Bullish' if avg_sentiment > 0 else 'Bearish'}",
                help="Average sentiment score (-1 to +1)"
            )
        else:
            st.metric("🙃 Avg Sentiment", "N/A")
    
    with col3:
        if not market_df.empty:
            price_change = ((market_df['close'].iloc[-1] - market_df['close'].iloc[0]) / 
                           market_df['close'].iloc[0] * 100)
            st.metric(
                "💹 Price Change",
                f"{price_change:+.2f}%",
                help="Total price change in selected period"
            )
        else:
            st.metric("💹 Price Change", "N/A")
    
    with col4:
        if not market_df.empty:
            total_volume = market_df['volume'].sum()
            st.metric(
                "📈 Total Volume",
                f"{total_volume/1e6:.1f}M",
                help="Total trading volume"
            )
        else:
            st.metric("📈 Total Volume", "N/A")
    
    # Main chart
    if not market_df.empty:
        fig = create_price_chart_with_news(news_df, market_df, selected_ticker)
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("📊 No market data available for visualization.")


if __name__ == "__main__":
    main()
