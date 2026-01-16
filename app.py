"""
LeadFlow - LinkedIn Automation Platform
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from utils.auth import require_auth
from utils.session import render_client_selector
from utils.database import get_client, get_reactions, get_competitors
from utils.styles import render_page_header, render_metric_card

# Vérifier l'authentification avant d'afficher le contenu
require_auth()

# Configuration de la page
st.set_page_config(
    page_title="LeadFlow",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Selecteur de client (injecte aussi les CSS)
client_id = render_client_selector()
client = get_client(client_id)

# Sidebar footer
with st.sidebar:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("""
        <div style="padding: 1rem 0.5rem; color: #64748b; font-size: 0.75rem;">
            <div style="margin-bottom: 0.5rem;">
                <span class="version-badge">v2.0.0</span>
            </div>
            <div>Powered by AI</div>
        </div>
    """, unsafe_allow_html=True)

# Header
client_name = client['name'] if client else "Client"
render_page_header(
    f"Bienvenue, {client_name}",
    "Votre tableau de bord LinkedIn Automation"
)

# Recuperer les stats du client actif
reactions = get_reactions(client_id)
competitors = get_competitors(client_id)
prospects_count = len(reactions)
relevant_count = sum(1 for r in reactions if r.get('prospect_relevant'))
messages_count = sum(1 for r in reactions if r.get('personalized_message'))

# Metriques principales avec design moderne
col1, col2, col3, col4 = st.columns(4)

with col1:
    relevance_rate = f"{(relevant_count/prospects_count*100):.0f}%" if prospects_count > 0 else "0%"
    st.markdown(render_metric_card(
        value=prospects_count,
        label="Total Prospects",
        delta=relevance_rate,
        delta_type="positive"
    ), unsafe_allow_html=True)

with col2:
    st.markdown(render_metric_card(
        value=relevant_count,
        label="Prospects Qualifies"
    ), unsafe_allow_html=True)

with col3:
    st.markdown(render_metric_card(
        value=messages_count,
        label="Messages Generes"
    ), unsafe_allow_html=True)

with col4:
    st.markdown(render_metric_card(
        value=len(competitors),
        label="Concurrents Suivis"
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Quick actions
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">Actions Rapides</div>
        </div>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
                    border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 12px; padding: 1.5rem; text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎯</div>
            <div style="font-weight: 600; color: #f8fafc; margin-bottom: 0.25rem;">Scraper</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">Lancer une campagne</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Lancer le Scraper", width="stretch", key="btn_scraper"):
        st.switch_page("pages/4_⚙️_Scraper.py")

with col2:
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.1));
                    border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 12px; padding: 1.5rem; text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">👥</div>
            <div style="font-weight: 600; color: #f8fafc; margin-bottom: 0.25rem;">Prospects</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">Voir tous les leads</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Voir les Prospects", width="stretch", key="btn_prospects"):
        st.switch_page("pages/2_👥_Prospects.py")

with col3:
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(234, 179, 8, 0.1), rgba(245, 158, 11, 0.1));
                    border: 1px solid rgba(234, 179, 8, 0.2); border-radius: 12px; padding: 1.5rem; text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">💬</div>
            <div style="font-weight: 600; color: #f8fafc; margin-bottom: 0.25rem;">Messages</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">Gerer les messages</div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Gerer les Messages", width="stretch", key="btn_messages"):
        st.switch_page("pages/3_💬_Messages.py")

# Info card
st.markdown("<br>", unsafe_allow_html=True)

if prospects_count == 0:
    st.markdown("""
        <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 12px; padding: 2rem; text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">🚀</div>
            <div style="font-size: 1.25rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.5rem;">
                Pret a demarrer ?
            </div>
            <div style="color: #94a3b8; margin-bottom: 1rem;">
                Configurez vos concurrents et lancez votre premiere campagne de scraping
            </div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Configurer maintenant", width="stretch", type="primary"):
            st.switch_page("pages/6_⚙️_Configuration.py")
