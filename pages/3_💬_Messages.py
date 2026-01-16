"""
Page Messages - Gestion et edition des messages personnalises
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.data_loader import load_all_reactions, get_prospects_with_messages
from utils.session import render_client_selector
from utils.database import (
    get_client, get_edited_messages, save_edited_message,
    get_client_profile_as_dict, save_reaction, find_radar_by_identifier, get_radar_message_template
)
from utils.styles import render_page_header, render_metric_card, render_empty_state
from utils.ai_analyzer import generate_message_for_prospect
import logging

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Messages | LeadFlow", page_icon="💬", layout="wide")

# Vérifier l'authentification
require_auth()

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Messages",
    f"Gestion et edition des messages - {client['name'] if client else ''}"
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
        "💬"
    )
    st.stop()

# Charger les messages edites depuis SQLite (avec cache pour éviter de recharger à chaque rerun)
@st.cache_data(ttl=60)
def load_edited_messages_cached(cid):
    return get_edited_messages(cid)

edited_messages = load_edited_messages_cached(client_id)

# Filtrer les prospects qualifiés (prospect_relevant=True)
qualified_df = df[df.get('prospect_relevant', False) == True].copy() if not df.empty and 'prospect_relevant' in df.columns else pd.DataFrame()

if qualified_df.empty:
    render_empty_state(
        "Aucun prospect qualifié",
        "Les prospects pertinents n'ont pas encore été qualifiés",
        "📝"
    )
    st.stop()

# Filtrer les prospects avec messages (pour les stats)
messages_df = get_prospects_with_messages(df)

# Statistiques des messages
if not messages_df.empty:
    avg_length = messages_df['personalized_message'].astype(str).str.len().mean()
    total_chars = messages_df['personalized_message'].astype(str).str.len().sum()
else:
    avg_length = 0
    total_chars = 0

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(render_metric_card(f"{avg_length:.0f}", "Longueur moyenne"), unsafe_allow_html=True)

with col2:
    st.markdown(render_metric_card(f"{total_chars:,}", "Total caracteres"), unsafe_allow_html=True)

with col3:
    st.markdown(render_metric_card(f"{len(messages_df)}", "Messages générés"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Liste des messages avec edition
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">Edition des Messages</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Selection d'un prospect pour edition (dedupliquer par reactor_urn)
# Utiliser les prospects qualifiés, pas seulement ceux avec messages
unique_prospects = qualified_df.drop_duplicates(subset='reactor_urn', keep='first').reset_index(drop=True)

if unique_prospects.empty:
    st.warning("Aucun prospect unique trouvé")
    st.stop()

# Créer une liste de noms uniques pour le dropdown
prospect_options = [
    f"{row['reactor_name']} - {row.get('headline', '')[:50] if pd.notna(row.get('headline')) else ''}"
    for _, row in unique_prospects.iterrows()
]

# Initialiser l'index sélectionné dans le session state
if 'selected_prospect_idx' not in st.session_state:
    st.session_state.selected_prospect_idx = 0

# S'assurer que l'index est valide
if st.session_state.selected_prospect_idx >= len(unique_prospects):
    st.session_state.selected_prospect_idx = 0

# Si on a un reactor_urn sauvegardé, trouver son index
if 'selected_reactor_urn' in st.session_state and st.session_state.selected_reactor_urn:
    matching_idx = None
    for idx, row in unique_prospects.iterrows():
        if row.get('reactor_urn') == st.session_state.selected_reactor_urn:
            matching_idx = idx
            break
    if matching_idx is not None:
        st.session_state.selected_prospect_idx = matching_idx

selected_idx = st.selectbox(
    "Choisir un prospect",
    options=range(len(unique_prospects)),
    index=st.session_state.selected_prospect_idx,
    format_func=lambda x: prospect_options[x] if x < len(prospect_options) else "",
    key="prospect_selector"
)

# Mettre à jour le session state quand la sélection change
st.session_state.selected_prospect_idx = selected_idx

if selected_idx is not None and selected_idx < len(unique_prospects):
    selected_prospect = unique_prospects.iloc[selected_idx]
    reactor_urn = selected_prospect.get('reactor_urn', '')
    
    # Stocker le reactor_urn dans le session state pour le retrouver après rerun
    st.session_state.selected_reactor_urn = reactor_urn

    # Message original ou edite
    original_message = selected_prospect.get('personalized_message', '')
    if not original_message or pd.isna(original_message) or str(original_message).strip() == '':
        original_message = ''  # Pas encore de message généré
    
    # Prioriser le message édité, puis le message original
    current_message = edited_messages.get(reactor_urn, original_message)
    
    # Si on vient de générer un message pour ce prospect, utiliser celui du session state en priorité
    if 'just_generated_message' in st.session_state:
        if st.session_state.just_generated_message.get('reactor_urn') == reactor_urn:
            current_message = st.session_state.just_generated_message.get('message', current_message)
            # Mettre à jour aussi edited_messages pour la session courante
            edited_messages[reactor_urn] = current_message
    
    # Afficher un message si pas encore de message
    if not current_message or str(current_message).strip() == '':
        st.info("💡 Ce prospect n'a pas encore de message généré. Cliquez sur 'Générer le message' pour en créer un.")
        current_message = ''

    # Afficher les infos du prospect
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"**Nom:** {selected_prospect.get('reactor_name', 'N/A')}")
        st.markdown(f"**Headline:** {selected_prospect.get('headline', 'N/A')}")
        st.markdown(f"**Score:** {selected_prospect.get('relevance_score', 0):.2f}")

    with col2:
        profile_url = selected_prospect.get('profile_url', '')
        if profile_url:
            st.markdown(f"[Profil LinkedIn]({profile_url})")

    st.markdown("---")

    # Bouton pour générer le message
    col_gen1, col_gen2 = st.columns([3, 1])
    
    with col_gen2:
        if st.button("🤖 Générer le message", type="primary", use_container_width=True):
            company_profile = get_client_profile_as_dict(client_id)
            if not company_profile:
                st.error("❌ Profil entreprise non trouvé. Configurez d'abord le persona.")
            else:
                with st.spinner("Génération du message en cours..."):
                    # Préparer les données du prospect
                    prospect_data = {
                        'reactor_name': selected_prospect.get('reactor_name', ''),
                        'headline': selected_prospect.get('headline', ''),
                        'post_url': selected_prospect.get('post_url', ''),
                        'company_name': selected_prospect.get('company_name', ''),
                        'competitor_name': selected_prospect.get('company_name', ''),
                        'reaction_type': selected_prospect.get('reaction_type', ''),
                        'profile_url': selected_prospect.get('profile_url', ''),
                        'reactor_urn': reactor_urn
                    }
                    
                    # Trouver le radar correspondant pour récupérer son message template
                    # Essayer d'abord avec company_name (pour competitor_last_post)
                    company_name = selected_prospect.get('company_name', '')
                    radar = find_radar_by_identifier(
                        client_id,
                        company_name=company_name,
                        keyword=None
                    )
                    
                    # Si pas trouvé, essayer avec keyword si disponible dans les données
                    if not radar and company_name:
                        # Pour les radars keyword_posts, le company_name peut contenir le keyword
                        radar = find_radar_by_identifier(
                            client_id,
                            company_name=None,
                            keyword=company_name
                        )
                    
                    radar_message_template = None
                    if radar:
                        radar_id = radar.get('id')
                        radar_name = radar.get('name', 'Unknown')
                        radar_message_template = get_radar_message_template(radar_id)
                        if radar_message_template:
                            logger.info(f"[DEBUG] Template de radar trouvé pour '{radar_name}' (ID: {radar_id}): {radar_message_template[:100]}...")
                        else:
                            logger.info(f"[DEBUG] Radar '{radar_name}' trouvé mais aucun template configuré")
                    else:
                        logger.info(f"[DEBUG] Aucun radar trouvé pour company_name='{company_name}'. Utilisation du template général du profil entreprise.")
                    
                    # Générer le message
                    generated_message = generate_message_for_prospect(
                        client_id,
                        prospect_data,
                        company_profile,
                        radar_message_template=radar_message_template
                    )
                    
                    if generated_message:
                        # Mettre à jour le message dans la base de données
                        reaction_data = {
                            'company_name': selected_prospect.get('company_name', ''),
                            'post_url': selected_prospect.get('post_url', ''),
                            'post_date': str(selected_prospect.get('post_date', '')),
                            'reactor_name': selected_prospect.get('reactor_name', ''),
                            'reactor_urn': reactor_urn,
                            'profile_url': selected_prospect.get('profile_url', ''),
                            'reaction_type': selected_prospect.get('reaction_type', ''),
                            'headline': selected_prospect.get('headline', ''),
                            'profile_picture_url': selected_prospect.get('profile_picture_url', ''),
                            'post_relevant': selected_prospect.get('post_relevant', False),
                            'prospect_relevant': selected_prospect.get('prospect_relevant', False),
                            'relevance_score': float(selected_prospect.get('relevance_score', 0.0)),
                            'relevance_reasoning': selected_prospect.get('relevance_reasoning', ''),
                            'personalized_message': generated_message
                        }
                        
                        save_reaction(client_id, reaction_data)
                        
                        # Sauvegarder aussi dans les messages édités pour affichage immédiat
                        save_edited_message(client_id, reactor_urn, generated_message)
                        
                        # Stocker le message généré dans le session state pour l'afficher après rerun
                        st.session_state.just_generated_message = {
                            'reactor_urn': reactor_urn,
                            'message': generated_message
                        }
                        
                        # Préserver l'index du prospect sélectionné ET le reactor_urn
                        st.session_state.selected_prospect_idx = selected_idx
                        st.session_state.selected_reactor_urn = reactor_urn
                        
                        # Vider les caches pour recharger les données fraîches
                        load_data.clear()
                        load_edited_messages_cached.clear()
                        
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la génération du message. Vérifiez la configuration OpenAI.")

    # Editeur de message
    edited = st.text_area("Message personnalise", current_message, height=200, key=f"msg_{reactor_urn}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Sauvegarder", key=f"save_{reactor_urn}"):
            save_edited_message(client_id, reactor_urn, edited)
            st.success("Message sauvegarde!")
            load_data.clear()
            st.rerun()

    with col2:
        if st.button("📋 Copier", key=f"copy_{reactor_urn}"):
            st.code(edited, language=None)
            st.info("Message copie (utilisez Ctrl+C)")
