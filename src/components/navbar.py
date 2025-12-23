"""
Shared navigation component for AINewsQuake dashboard.

Modern light mode design with clean white background.
"""

import streamlit as st


def render_navbar(current_page: str = "Chart"):
    """
    Render custom navigation bar.
    
    Args:
        current_page: Name of current page for highlighting
    """
    
    # Light mode styling with white background everywhere
    st.markdown(
        """
        <style>
        /* Hide Streamlit branding - use display:none to remove layout space */
        #MainMenu {display: none !important;}
        header {display: none !important;}
        footer {display: none !important;}
        
        /* Force white background everywhere */
        .main {
            background-color: #ffffff !important;
        }
        
        .stApp {
            background-color: #ffffff !important;
        }
        
        /* Sidebar styling - KILL IT */
        [data-testid="stSidebar"] {
            display: none !important;
            width: 0px !important;
        }
        
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Expand main content to full width */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 5rem !important;
            padding-right: 5rem !important;
        }
        
        /* Modern transparent navbar */
        .custom-navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 70px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(102, 126, 234, 0.15);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2.5rem;
            z-index: 999;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
        }
        
        /* Logo section */
        .navbar-logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        
        .navbar-logo-icon {
            font-size: 2rem;
        }
        
        .navbar-logo-text {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Navigation buttons - NO underlines */
        .navbar-center {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }
        
        .nav-button {
            background: transparent;
            border: none;
            color: #4a5568;
            padding: 0.6rem 1.5rem;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none !important;
            display: inline-block;
        }
        
        .nav-button:hover {
            background: rgba(102, 126, 234, 0.08);
            color: #667eea;
            text-decoration: none !important;
        }
        
        .nav-button.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            text-decoration: none !important;
        }
        
        /* Precise Content Alignment */
        .main .block-container {
            padding-top: 72px !important; /* 70px navbar + 2px buffer */
            padding-bottom: 2rem;
            background-color: #ffffff !important;
            max-width: 100% !important;
        }
        
        /* Title styling */
        h1 {
            padding-top: 0 !important;
            margin-top: 0 !important;
            color: #2d3748;
        }
        
        /* Subtitle/markdown text */
        p {
            margin-top: 0 !important;
        }
        
        h2, h3, h4, h5, h6 {
            color: #2d3748;
        }
        
        /* Fix tab button padding and overlap */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.75rem;
            padding: 0.5rem 0;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 10px;
            color: #4a5568;
            font-weight: 500;
            padding: 0.75rem 1.5rem !important;
            margin: 0 !important;
            white-space: nowrap;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(102, 126, 234, 0.08);
            color: #667eea;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        
        .stTabs [aria-selected="true"] * {
            color: white !important;
        }
        
        /* Metric styling */
        [data-testid="stMetricValue"] {
            color: #667eea;
        }
        
        /* Text color */
        p, span, div {
            color: #2d3748;
        }
        
        /* Dataframe styling */
        .stDataFrame {
            background-color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Navbar HTML
    pages = {
        "Chart": "/",
        "Impact": "/impact_explorer",
        "Analytics": "/analytics",
        "About": "/about"
    }
    
    nav_buttons = ""
    for page_name, page_route in pages.items():
        active_class = "active" if page_name == current_page else ""
        nav_buttons += f'<a href="{page_route}" target="_self" class="nav-button {active_class}">{page_name}</a>'
    
    navbar_html = f"""
    <div class="custom-navbar">
        <div class="navbar-logo">
            <span class="navbar-logo-icon">🌋</span>
            <span class="navbar-logo-text">AINewsQuake</span>
        </div>
        <div class="navbar-center">
            {nav_buttons}
        </div>
        <div style="width: 100px;"></div>
    </div>
    """
    
    st.markdown(navbar_html, unsafe_allow_html=True)
