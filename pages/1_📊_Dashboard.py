"""
Page Dashboard - Vue d'ensemble moderne
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.data_loader import load_all_reactions, get_stats
from utils.session import render_client_selector
from utils.database import get_client
from utils.styles import render_page_header, render_metric_card

st.set_page_config(page_title="Dashboard | LeadFlow", page_icon="🚀", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Dashboard",
    f"Vue d'ensemble des performances - {client['name'] if client else ''}"
)

# Charger les donnees (cache par client_id)
@st.cache_data(ttl=300)
def load_data(cid):
    return load_all_reactions(client_id=cid)

df = load_data(client_id)

if df.empty:
    st.markdown("""
        <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 12px; padding: 3rem; text-align: center; margin-top: 2rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
            <div style="font-size: 1.25rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.5rem;">
                Aucune donnee disponible
            </div>
            <div style="color: #94a3b8;">
                Lancez le scraper pour commencer a collecter des prospects
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# Statistiques principales
stats = get_stats(df)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(render_metric_card(
        value=f"{stats['total_prospects']:,}",
        label="Total Prospects",
        delta=f"{stats['relevance_rate']:.1f}% qualifies",
        delta_type="positive"
    ), unsafe_allow_html=True)

with col2:
    st.markdown(render_metric_card(
        value=f"{stats['relevant_prospects']:,}",
        label="Prospects Qualifies"
    ), unsafe_allow_html=True)

with col3:
    st.markdown(render_metric_card(
        value=f"{stats['messages_generated']:,}",
        label="Messages Generes"
    ), unsafe_allow_html=True)

with col4:
    st.markdown(render_metric_card(
        value=f"{stats['avg_score']:.2f}",
        label="Score Moyen"
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Graphiques
col1, col2 = st.columns(2)

# Theme sombre pour les graphiques
chart_template = {
    'layout': {
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#94a3b8'},
        'xaxis': {'gridcolor': 'rgba(255,255,255,0.1)'},
        'yaxis': {'gridcolor': 'rgba(255,255,255,0.1)'}
    }
}

with col1:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">Evolution des Prospects</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if 'post_date' in df.columns and not df['post_date'].isna().all():
        df_chart = df.copy()
        df_chart['date_only'] = df_chart['post_date'].dt.date
        daily_counts = df_chart.groupby('date_only').size().reset_index(name='count')
        daily_counts = daily_counts.sort_values('date_only')

        fig = px.area(daily_counts, x='date_only', y='count',
                     labels={'date_only': '', 'count': 'Prospects'})
        fig.update_traces(
            fill='tozeroy',
            line_color='#6366f1',
            fillcolor='rgba(99, 102, 241, 0.3)'
        )
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Aucune donnee de date disponible")

with col2:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">Repartition par Reaction</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if 'reaction_type' in df.columns:
        reaction_counts = df['reaction_type'].value_counts().reset_index()
        reaction_counts.columns = ['Type', 'Nombre']

        colors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd']
        fig = px.pie(reaction_counts, values='Nombre', names='Type',
                    color_discrete_sequence=colors, hole=0.6)
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2)
        )
        fig.update_traces(textposition='inside', textinfo='percent')
        st.plotly_chart(fig, width="stretch")

st.markdown("<br>", unsafe_allow_html=True)

# Tableau des derniers prospects
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">Derniers Prospects</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Colonnes a afficher (sans photo pour éviter les None)
display_cols = ['reactor_name', 'headline', 'detected_company', 'reaction_type',
                'relevance_score', 'prospect_relevant', 'post_date']

available_cols = [col for col in display_cols if col in df.columns]
recent_df = df[available_cols].head(15).copy()

# Formatage
if 'post_date' in recent_df.columns:
    recent_df['post_date'] = recent_df['post_date'].dt.strftime('%d/%m %H:%M')

if 'prospect_relevant' in recent_df.columns:
    recent_df['prospect_relevant'] = recent_df['prospect_relevant'].map({True: '✓', False: '✗'})

if 'relevance_score' in recent_df.columns:
    recent_df['relevance_score'] = recent_df['relevance_score'].round(2)

# Renommer les colonnes
col_names = {
    'reactor_name': 'Nom',
    'headline': 'Titre',
    'detected_company': 'Entreprise',
    'reaction_type': 'Reaction',
    'relevance_score': 'Score',
    'prospect_relevant': 'Qualifie',
    'post_date': 'Date'
}
recent_df = recent_df.rename(columns=col_names)

st.dataframe(recent_df, use_container_width=True, hide_index=True, height=400)
