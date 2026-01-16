"""
Styles CSS modernes pour l'application SaaS
"""
import base64
from pathlib import Path

LOGO_SVG = """<svg width="160" height="36" viewBox="0 0 160 36" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#6366f1"/>
      <stop offset="100%" style="stop-color:#8b5cf6"/>
    </linearGradient>
    <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#818cf8"/>
      <stop offset="100%" style="stop-color:#a78bfa"/>
    </linearGradient>
  </defs>
  <circle cx="18" cy="18" r="14" fill="url(#grad1)"/>
  <path d="M11 18 L16 13 L16 16 L25 16 L25 20 L16 20 L16 23 Z" fill="white"/>
  <circle cx="25" cy="18" r="3.5" fill="url(#grad2)"/>
  <text x="40" y="24" font-family="Inter, system-ui, sans-serif" font-size="18" font-weight="700" fill="#f8fafc">Lead</text>
  <text x="82" y="24" font-family="Inter, system-ui, sans-serif" font-size="18" font-weight="700" fill="#818cf8">Flow</text>
</svg>"""

MODERN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="st-"]:not([data-testid="stIconMaterial"]) {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Garder les icones Material avec leur police */
[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', sans-serif !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Desactiver le collapse de la sidebar */
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

/* Sidebar toujours visible */
[data-testid="stSidebar"] {
    min-width: 280px !important;
    width: 280px !important;
    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] {
    color: #e2e8f0;
}

/* Cacher la navigation par defaut de Streamlit */
[data-testid="stSidebarNav"] {
    display: none !important;
}

/* Style des liens de navigation personnalises */
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
    color: #94a3b8 !important;
    background: transparent !important;
    border: none !important;
    padding: 0.6rem 0.75rem !important;
    border-radius: 8px !important;
    transition: all 0.15s ease !important;
    font-size: 0.875rem !important;
    text-decoration: none !important;
    margin-bottom: 0.15rem !important;
}

[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
    background: rgba(255,255,255,0.05) !important;
    color: #f1f5f9 !important;
}

[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {
    background: rgba(99, 102, 241, 0.15) !important;
    color: #f1f5f9 !important;
}

/* Logo container */
.logo-wrapper {
    padding: 1.25rem 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 0.5rem;
}

/* Client selector */
.workspace-selector {
    background: rgba(99, 102, 241, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
}

.workspace-label {
    font-size: 0.65rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
    font-weight: 600;
}

/* Navigation */
.nav-section {
    padding: 0.5rem 0.75rem;
    margin-top: 0.5rem;
}

.nav-section-title {
    font-size: 0.65rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.75rem;
    padding-left: 0.5rem;
    font-weight: 600;
}

.nav-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.65rem 0.75rem;
    border-radius: 8px;
    color: #94a3b8;
    text-decoration: none;
    transition: all 0.15s ease;
    margin-bottom: 0.25rem;
    font-size: 0.875rem;
    font-weight: 500;
}

.nav-link:hover {
    background: rgba(255,255,255,0.05);
    color: #f1f5f9;
}

.nav-link.active {
    background: rgba(99, 102, 241, 0.15);
    color: #f1f5f9;
}

.nav-link .nav-icon {
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}

/* Page header */
.page-header {
    margin-bottom: 1.75rem;
}

.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 0.25rem;
    letter-spacing: -0.02em;
}

.page-subtitle {
    font-size: 0.9rem;
    color: #64748b;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.25rem;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.25);
    border-color: rgba(99, 102, 241, 0.25);
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1;
    letter-spacing: -0.02em;
}

.metric-label {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.metric-delta {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    margin-top: 0.6rem;
    font-weight: 500;
}

.metric-delta.positive {
    background: rgba(34, 197, 94, 0.15);
    color: #4ade80;
}

.metric-delta.negative {
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
}

/* Data cards */
.data-card {
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.data-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.data-card-title {
    font-size: 1rem;
    font-weight: 600;
    color: #f1f5f9;
    letter-spacing: -0.01em;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.25rem;
    font-weight: 600;
    font-size: 0.85rem;
    transition: all 0.2s ease;
    letter-spacing: -0.01em;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 16px rgba(99, 102, 241, 0.35);
}

.stButton > button:active {
    transform: translateY(0);
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    color: #f8fafc;
    transition: all 0.2s ease;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

/* Tables */
[data-testid="stDataFrame"] > div {
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem;
    background: transparent;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 0;
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 6px 6px 0 0;
    color: #64748b;
    padding: 0.6rem 1rem;
    font-weight: 500;
    font-size: 0.85rem;
    border-bottom: 2px solid transparent;
}

.stTabs [aria-selected="true"] {
    background: transparent;
    color: #f8fafc;
    border-bottom: 2px solid #6366f1;
}

/* Alerts */
[data-testid="stAlert"] {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 10px;
}

/* Expanders */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
    font-weight: 500;
}

/* Forms */
[data-testid="stForm"] {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.25rem;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
    background: #475569;
}

/* Divider */
.divider {
    height: 1px;
    background: rgba(255,255,255,0.08);
    margin: 1rem 0;
}

/* Version badge */
.version-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    background: rgba(99, 102, 241, 0.15);
    border-radius: 4px;
    font-size: 0.7rem;
    color: #818cf8;
    font-weight: 500;
}

/* Status indicator */
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
}

.status-dot.online {
    background: #22c55e;
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

/* Quick action cards */
.action-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.2s ease;
    cursor: pointer;
}

.action-card:hover {
    background: rgba(99, 102, 241, 0.08);
    border-color: rgba(99, 102, 241, 0.25);
    transform: translateY(-2px);
}

.action-card-icon {
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
}

.action-card-title {
    font-weight: 600;
    color: #f1f5f9;
    font-size: 0.9rem;
}

.action-card-desc {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.25rem;
}
</style>
"""


def inject_modern_css():
    """Injecte les styles CSS modernes dans la page"""
    import streamlit as st
    st.markdown(MODERN_CSS, unsafe_allow_html=True)


def render_logo():
    """Affiche le logo SVG dans la sidebar"""
    import streamlit as st
    st.markdown(f"""
        <div class="logo-wrapper">
            {LOGO_SVG}
        </div>
    """, unsafe_allow_html=True)


def render_nav_menu(current_page=""):
    """Affiche le menu de navigation dans la sidebar"""
    import streamlit as st

    pages = [
        {"icon": "🏠", "label": "Accueil", "page": "app"},
        {"icon": "📊", "label": "Dashboard", "page": "Dashboard"},
        {"icon": "👥", "label": "Prospects", "page": "Prospects"},
        {"icon": "💬", "label": "Messages", "page": "Messages"},
        {"icon": "🎯", "label": "Scraper", "page": "Scraper"},
        {"icon": "📈", "label": "Statistiques", "page": "Statistiques"},
        {"icon": "⚙️", "label": "Configuration", "page": "Configuration"},
    ]

    nav_html = '<div class="nav-section"><div class="nav-section-title">Menu</div>'

    for p in pages:
        active_class = "active" if current_page == p["page"] else ""
        nav_html += f'''
            <div class="nav-link {active_class}">
                <span class="nav-icon">{p["icon"]}</span>
                <span>{p["label"]}</span>
            </div>
        '''

    nav_html += '</div>'
    st.markdown(nav_html, unsafe_allow_html=True)


def render_metric_card(value, label, delta=None, delta_type="positive"):
    """Affiche une carte metrique stylisee"""
    delta_html = ""
    if delta:
        delta_class = "positive" if delta_type == "positive" else "negative"
        arrow = "+" if delta_type == "positive" else ""
        delta_html = f'<div class="metric-delta {delta_class}">{arrow}{delta}</div>'

    return f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {delta_html}
        </div>
    """


def render_page_header(title, subtitle=""):
    """Affiche l'en-tete de page stylise"""
    import streamlit as st
    st.markdown(f"""
        <div class="page-header">
            <div class="page-title">{title}</div>
            <div class="page-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)


def render_empty_state(title, message, icon="📭"):
    """Affiche un etat vide stylise"""
    import streamlit as st
    st.markdown(f"""
        <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2);
                    border-radius: 14px; padding: 3rem; text-align: center; margin: 2rem 0;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem; opacity: 0.8;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.5rem;">
                {title}
            </div>
            <div style="color: #64748b; font-size: 0.9rem;">
                {message}
            </div>
        </div>
    """, unsafe_allow_html=True)
