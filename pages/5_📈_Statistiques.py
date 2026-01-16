"""
Page Statistiques - Graphiques et analyses
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.data_loader import load_all_reactions, get_stats
from utils.session import render_client_selector
from utils.database import get_client, get_reactions, get_radars
from utils.styles import render_page_header, render_metric_card, render_empty_state

st.set_page_config(page_title="Statistiques | LeadFlow", page_icon="📈", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Statistiques",
    f"Analyses et graphiques - {client['name'] if client else ''}"
)

# Charger les donnees (cache par client_id)
@st.cache_data(ttl=300)
def load_data(cid):
    return load_all_reactions(client_id=cid)

df = load_data(client_id)

if df.empty:
    render_empty_state(
        "Aucune donnee",
        "Lancez le scraper pour commencer a collecter des prospects",
        "📈"
    )
    st.stop()

stats = get_stats(df)

# ============== MÉTRIQUES PRINCIPALES ==============
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(render_metric_card(
        f"{stats['total_prospects']:,}",
        "Total Prospects",
        f"{stats['relevance_rate']:.1f}% qualifies",
        "positive"
    ), unsafe_allow_html=True)

with col2:
    st.markdown(render_metric_card(
        f"{stats['relevant_prospects']:,}",
        "Prospects Qualifies"
    ), unsafe_allow_html=True)

with col3:
    messages_count = len(df[df.get('personalized_message', '').astype(str).str.strip() != '']) if not df.empty else 0
    st.markdown(render_metric_card(
        f"{messages_count:,}",
        "Messages Generes"
    ), unsafe_allow_html=True)

with col4:
    avg_score = df['relevance_score'].mean() if 'relevance_score' in df.columns and not df.empty else 0.0
    st.markdown(render_metric_card(
        f"{avg_score:.2f}",
        "Score Moyen"
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============== SUIVI TEMPOREL GLOBAL ==============
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">📊 Evolution du Nombre de Prospects Scrapés (Jour après Jour)</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Utiliser created_at si disponible, sinon post_date
if 'created_at' in df.columns:
    df['date'] = pd.to_datetime(df['created_at'], errors='coerce')
elif 'post_date' in df.columns:
    df['date'] = pd.to_datetime(df['post_date'], errors='coerce')
else:
    df['date'] = pd.to_datetime('today')

# Filtrer les dates valides
df_valid_dates = df[df['date'].notna()].copy()
df_valid_dates['date_only'] = df_valid_dates['date'].dt.date

if not df_valid_dates.empty:
    # Compter par jour
    daily_counts = df_valid_dates.groupby('date_only').size().reset_index(name='count')
    daily_counts = daily_counts.sort_values('date_only')
    
    # Calculer le total cumulé
    daily_counts['total_cumulatif'] = daily_counts['count'].cumsum()
    
    # Créer le graphique avec deux axes Y
    fig = go.Figure()
    
    # Barres pour le nombre journalier
    fig.add_trace(go.Bar(
        x=daily_counts['date_only'],
        y=daily_counts['count'],
        name='Prospects par jour',
        marker_color='#6366f1',
        opacity=0.7
    ))
    
    # Ligne pour le total cumulatif
    fig.add_trace(go.Scatter(
        x=daily_counts['date_only'],
        y=daily_counts['total_cumulatif'],
        name='Total cumulatif',
        mode='lines+markers',
        line=dict(color='#22c55e', width=3),
        marker=dict(size=6),
        yaxis='y2'
    ))
    
    fig.update_layout(
        height=400,
        margin=dict(l=0, r=50, t=20, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.05)',
            title='Date'
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.05)',
            title='Prospects par jour',
            side='left'
        ),
        yaxis2=dict(
            title='Total cumulatif',
            overlaying='y',
            side='right',
            gridcolor='rgba(255,255,255,0.05)'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Afficher les stats rapides
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Aujourd'hui", f"{daily_counts.iloc[-1]['count'] if len(daily_counts) > 0 else 0}")
    with col2:
        avg_per_day = daily_counts['count'].mean() if len(daily_counts) > 0 else 0
        st.metric("Moyenne/jour", f"{avg_per_day:.1f}")
    with col3:
        max_day = daily_counts['count'].max() if len(daily_counts) > 0 else 0
        st.metric("Meilleur jour", f"{max_day}")
    with col4:
        st.metric("Total", f"{len(df_valid_dates):,}")
else:
    st.info("Aucune donnée de date disponible")

st.markdown("<br>", unsafe_allow_html=True)

# ============== SUIVI PAR RADAR/SOURCE ==============
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">🎯 Evolution par Radar/Source</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Utiliser company_name/keyword comme source (proxy pour le radar)
    if 'company_name' in df_valid_dates.columns and not df_valid_dates.empty:
        # Créer une colonne source
        df_valid_dates['source'] = df_valid_dates['company_name'].fillna('Autre')
        
        # Grouper par source et date
        source_daily = df_valid_dates.groupby(['source', 'date_only']).size().reset_index(name='count')
        source_daily = source_daily.sort_values(['source', 'date_only'])
        
        # Calculer le cumulatif par source
        source_daily['cumulatif'] = source_daily.groupby('source')['count'].cumsum()
        
        # Graphique en lignes pour chaque source
        fig = px.line(
            source_daily,
            x='date_only',
            y='cumulatif',
            color='source',
            labels={'date_only': 'Date', 'cumulatif': 'Total cumulatif', 'source': 'Source/Radar'},
            title=''
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée de source disponible")

with col2:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">📊 Répartition par Source/Radar</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if 'company_name' in df.columns and not df.empty:
        source_counts = df['company_name'].value_counts().head(10).reset_index()
        source_counts.columns = ['Source', 'Nombre']
        
        fig = px.bar(
            source_counts,
            x='Nombre',
            y='Source',
            orientation='h',
            labels={'Nombre': 'Nombre de prospects', 'Source': 'Source/Radar'},
            title=''
        )
        
        fig.update_traces(marker_color='#6366f1')
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

st.markdown("<br>", unsafe_allow_html=True)

# ============== STATISTIQUES D'OUTREACH ==============
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">💬 Statistiques d'Outreach</div>
        </div>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Taux de qualification
    total = len(df) if not df.empty else 0
    qualified = len(df[df.get('prospect_relevant', False) == True]) if not df.empty else 0
    qualification_rate = (qualified / total * 100) if total > 0 else 0
    st.metric("Taux de Qualification", f"{qualification_rate:.1f}%", f"{qualified}/{total}")

with col2:
    # Taux de messages générés
    messages_gen = len(df[df.get('personalized_message', '').astype(str).str.strip() != '']) if not df.empty else 0
    message_rate = (messages_gen / qualified * 100) if qualified > 0 else 0
    st.metric("Taux de Messages", f"{message_rate:.1f}%", f"{messages_gen}/{qualified}")

with col3:
    # Score moyen des qualifiés
    if not df.empty and 'relevance_score' in df.columns:
        qualified_scores = df[df.get('prospect_relevant', False) == True]['relevance_score']
        avg_qualified_score = qualified_scores.mean() if len(qualified_scores) > 0 else 0.0
        st.metric("Score Moyen (Qualifiés)", f"{avg_qualified_score:.2f}")
    else:
        st.metric("Score Moyen (Qualifiés)", "0.00")

with col4:
    # Évolution du taux de qualification dans le temps
    if not df_valid_dates.empty and 'prospect_relevant' in df_valid_dates.columns:
        daily_qualification = df_valid_dates.groupby('date_only').agg({
            'prospect_relevant': ['sum', 'count']
        }).reset_index()
        daily_qualification.columns = ['date', 'qualified', 'total']
        daily_qualification['rate'] = (daily_qualification['qualified'] / daily_qualification['total'] * 100).fillna(0)
        latest_rate = daily_qualification['rate'].iloc[-1] if len(daily_qualification) > 0 else 0
        prev_rate = daily_qualification['rate'].iloc[-2] if len(daily_qualification) > 1 else 0
        delta = latest_rate - prev_rate
        st.metric("Taux Qualif. (7j)", f"{daily_qualification['rate'].tail(7).mean():.1f}%", f"{delta:+.1f}%")
    else:
        st.metric("Taux Qualif. (7j)", "0.0%")

st.markdown("<br>", unsafe_allow_html=True)

# ============== GRAPHIQUES D'OUTREACH ==============
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">📈 Distribution des Scores de Qualification</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if 'relevance_score' in df.columns and not df.empty:
        # Histogramme des scores avec ligne de seuil
        fig = px.histogram(
            df,
            x='relevance_score',
            nbins=30,
            labels={'relevance_score': 'Score de pertinence', 'count': 'Nombre de prospects'},
            title=''
        )
        
        fig.update_traces(marker_color='#6366f1', opacity=0.7)
        
        # Ajouter une ligne verticale pour le seuil moyen
        if 'relevance_score' in df.columns:
            threshold = df['relevance_score'].mean()
            fig.add_vline(
                x=threshold,
                line_dash="dash",
                line_color="#22c55e",
                annotation_text=f"Seuil moyen: {threshold:.2f}"
            )
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée de score disponible")

with col2:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">🎯 Qualifiés vs Non Qualifiés</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if 'prospect_relevant' in df.columns and not df.empty:
        relevant_counts = df['prospect_relevant'].value_counts().reset_index()
        relevant_counts.columns = ['Pertinent', 'Nombre']
        relevant_counts['Pertinent'] = relevant_counts['Pertinent'].map({True: 'Qualifié', False: 'Non Qualifié'})
        
        colors = ['#22c55e', '#ef4444']
        fig = px.pie(
            relevant_counts,
            values='Nombre',
            names='Pertinent',
            color='Pertinent',
            color_discrete_map={'Qualifié': '#22c55e', 'Non Qualifié': '#ef4444'},
            hole=0.5,
            title=''
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1)
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+value')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

st.markdown("<br>", unsafe_allow_html=True)

# ============== PERFORMANCE PAR TYPE DE RÉACTION ==============
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">💬 Répartition par Type de Réaction</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if 'reaction_type' in df.columns and not df.empty:
        reaction_counts = df['reaction_type'].value_counts().reset_index()
        reaction_counts.columns = ['Type', 'Nombre']
        
        colors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#e9d5ff']
        fig = px.pie(
            reaction_counts,
            values='Nombre',
            names='Type',
            color_discrete_sequence=colors,
            hole=0.6,
            title=''
        )
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2)
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+value')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

with col2:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">📊 Taux de Qualification par Type de Réaction</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if 'reaction_type' in df.columns and 'prospect_relevant' in df.columns and not df.empty:
        reaction_qualification = df.groupby('reaction_type').agg({
            'prospect_relevant': ['sum', 'count']
        }).reset_index()
        reaction_qualification.columns = ['Type', 'qualified', 'total']
        reaction_qualification['rate'] = (reaction_qualification['qualified'] / reaction_qualification['total'] * 100).fillna(0)
        reaction_qualification = reaction_qualification.sort_values('rate', ascending=False)
        
        fig = px.bar(
            reaction_qualification,
            x='Type',
            y='rate',
            labels={'rate': 'Taux de qualification (%)', 'Type': 'Type de réaction'},
            title=''
        )
        
        fig.update_traces(marker_color='#6366f1')
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

st.markdown("<br>", unsafe_allow_html=True)

# ============== TOP SOURCES ET PERFORMANCE ==============
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">🏆 Top 10 Sources/Radars par Performance</div>
        </div>
    </div>
""", unsafe_allow_html=True)

if 'company_name' in df.columns and 'prospect_relevant' in df.columns and not df.empty:
    # Calculer les stats par source
    source_stats = df.groupby('company_name').agg({
        'prospect_relevant': ['sum', 'count'],
        'relevance_score': 'mean'
    }).reset_index()
    
    source_stats.columns = ['Source', 'qualified', 'total', 'avg_score']
    source_stats['qualification_rate'] = (source_stats['qualified'] / source_stats['total'] * 100).fillna(0)
    
    # Trier par nombre total de prospects (ou par taux de qualification)
    source_stats = source_stats.sort_values('total', ascending=False).head(10)
    
    # Créer un graphique en barres groupées
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Total prospects',
        x=source_stats['Source'],
        y=source_stats['total'],
        marker_color='#6366f1',
        opacity=0.7
    ))
    
    fig.add_trace(go.Bar(
        name='Qualifiés',
        x=source_stats['Source'],
        y=source_stats['qualified'],
        marker_color='#22c55e',
        opacity=0.9
    ))
    
    fig.update_layout(
        barmode='group',
        height=400,
        margin=dict(l=0, r=0, t=20, b=100),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.05)',
            tickangle=-45
        ),
        yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Afficher un tableau avec les stats détaillées
    st.markdown("#### Détails par Source")
    display_stats = source_stats[['Source', 'total', 'qualified', 'qualification_rate', 'avg_score']].copy()
    display_stats.columns = ['Source', 'Total', 'Qualifiés', 'Taux (%)', 'Score Moyen']
    display_stats['Taux (%)'] = display_stats['Taux (%)'].round(2)
    display_stats['Score Moyen'] = display_stats['Score Moyen'].round(2)
    st.dataframe(display_stats, use_container_width=True, hide_index=True)
else:
    st.info("Aucune donnée disponible")
