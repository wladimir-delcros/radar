"""
Page Prospects - Liste et gestion des prospects
Refactorisée avec meilleure UI/UX
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import json
import logging

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.data_loader import load_all_reactions
from utils.export_manager import export_to_csv, export_to_excel
from utils.session import render_client_selector
from utils.database import get_client, get_client_profile_as_dict, delete_reaction, delete_reactions_batch, save_reaction
from utils.intelligent_scoring import recalculate_prospect_scoring
from utils.styles import render_page_header, render_metric_card
from utils.radar_manager import get_profile_detail, extract_username_from_url

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Prospects | LeadFlow", page_icon="🚀", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Prospects",
    f"Liste complète des leads - {client['name'] if client else ''}"
)

# Initialiser session_state pour pagination et sélection
if 'prospects_page' not in st.session_state:
    st.session_state.prospects_page = 0
if 'prospects_per_page' not in st.session_state:
    st.session_state.prospects_per_page = 50
if 'selected_prospects' not in st.session_state:
    st.session_state.selected_prospects = set()
if 'nav_action' not in st.session_state:
    st.session_state.nav_action = None
if 'last_filter_state' not in st.session_state:
    st.session_state.last_filter_state = None

# Charger les données (cache par client_id)
@st.cache_data(ttl=300)
def load_data(cid):
    return load_all_reactions(client_id=cid)

df = load_data(client_id)

if df.empty:
    st.markdown("""
        <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 12px; padding: 3rem; text-align: center; margin-top: 2rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">👥</div>
            <div style="font-size: 1.25rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.5rem;">
                Aucun prospect
            </div>
            <div style="color: #94a3b8;">
                Lancez une campagne de scraping pour collecter des prospects
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# ========== FILTRES (désactivés - supprimés de la sidebar) ==========
# Valeurs par défaut pour les filtres
filter_relevant = False
score_range = None
selected_reaction = 'Tous'
selected_company = 'Tous'
search_text = ''

# ========== APPLIQUER LES FILTRES ==========
# Pas de filtres appliqués - afficher tous les prospects
filtered_df = df.copy()

# Détecter les changements de filtres et réinitialiser la pagination (désactivé)
current_filter_state = None

if st.session_state.last_filter_state is not None and st.session_state.last_filter_state != current_filter_state:
    # Les filtres ont changé, réinitialiser à la page 0
    st.session_state.prospects_page = 0

st.session_state.last_filter_state = current_filter_state

# ========== MÉTRIQUES ==========
total = len(df)
filtered = len(filtered_df)
qualified = len(filtered_df[filtered_df.get('prospect_relevant', False) == True])
selected_count = len(st.session_state.selected_prospects)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(render_metric_card(filtered, "Prospects affichés"), unsafe_allow_html=True)
with col2:
    st.markdown(render_metric_card(qualified, "Qualifiés"), unsafe_allow_html=True)
with col3:
    st.markdown(render_metric_card(total, "Total"), unsafe_allow_html=True)
with col4:
    st.markdown(render_metric_card(selected_count, "Sélectionnés"), unsafe_allow_html=True)
with col5:
    # Contrôle du nombre d'éléments par page
    per_page_options = [25, 50, 100, 200, 500]
    new_per_page = st.selectbox(
        "Éléments par page",
        options=per_page_options,
        index=per_page_options.index(st.session_state.prospects_per_page) if st.session_state.prospects_per_page in per_page_options else 1,
        help="Nombre de prospects à afficher par page",
        key="per_page_selector"
    )
    if new_per_page != st.session_state.prospects_per_page:
        st.session_state.prospects_per_page = new_per_page
        st.session_state.prospects_page = 0
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ========== CONTROLES DE SÉLECTION ET ACTIONS ==========
st.markdown("### 📋 Actions en masse")

col_sel1, col_sel2, col_sel3, col_sel4, col_sel5, col_sel6 = st.columns(6)

with col_sel1:
    if st.button("✓ Tout sélectionner", use_container_width=True, help="Sélectionner tous les prospects filtrés"):
        st.session_state.selected_prospects = set(
            filtered_df.apply(
                lambda row: f"{row.get('reactor_urn', '')}_{row.get('post_url', '')}",
                axis=1
            ).tolist()
        )
        st.rerun()

with col_sel2:
    if st.button("✗ Tout désélectionner", use_container_width=True, help="Désélectionner tous les prospects"):
        st.session_state.selected_prospects = set()
        st.rerun()

with col_sel3:
    if selected_count > 0:
        if st.button("🔄 Recalculer Scoring", type="primary", use_container_width=True, help="Recalculer le scoring IA des prospects sélectionnés"):
            company_profile = get_client_profile_as_dict(client_id)
            if not company_profile:
                st.error("❌ Profil entreprise non trouvé. Configurez d'abord le persona.")
            else:
                selected_prospects_data = []
                for idx, row in filtered_df.iterrows():
                    prospect_key = f"{row.get('reactor_urn', '')}_{row.get('post_url', '')}"
                    if prospect_key in st.session_state.selected_prospects:
                        selected_prospects_data.append(row)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                success_count = 0
                error_count = 0
                
                for idx, prospect in enumerate(selected_prospects_data):
                    progress = (idx + 1) / len(selected_prospects_data)
                    progress_bar.progress(progress)
                    status_text.text(f"Traitement {idx + 1}/{len(selected_prospects_data)}: {prospect.get('reactor_name', 'Unknown')}")
                    
                    try:
                        result = recalculate_prospect_scoring(
                            client_id,
                            prospect.get('reactor_urn', ''),
                            prospect.get('post_url', ''),
                            company_profile
                        )
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Erreur recalcul prospect {prospect.get('reactor_name')}: {e}")
                
                progress_bar.empty()
                status_text.empty()
                
                if success_count > 0:
                    st.success(f"✅ {success_count} prospect(s) recalculé(s) avec succès!")
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} erreur(s) lors du recalcul")
                
                load_data.clear()
                st.rerun()

with col_sel4:
    if selected_count > 0:
        if st.button("✨ Enrichir", type="primary", use_container_width=True, help="Enrichir les prospects sélectionnés avec get_profile"):
            selected_prospects_data = []
            for idx, row in filtered_df.iterrows():
                prospect_key = f"{row.get('reactor_urn', '')}_{row.get('post_url', '')}"
                if prospect_key in st.session_state.selected_prospects:
                    selected_prospects_data.append(row)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            success_count = 0
            error_count = 0
            
            for idx, prospect in enumerate(selected_prospects_data):
                progress = (idx + 1) / len(selected_prospects_data)
                progress_bar.progress(progress)
                status_text.text(f"Enrichissement {idx + 1}/{len(selected_prospects_data)}: {prospect.get('reactor_name', 'Unknown')}")
                
                try:
                    # Récupérer le profile_url ou reactor_urn
                    profile_url = prospect.get('profile_url', '')
                    reactor_urn = str(prospect.get('reactor_urn', ''))
                    
                    # Extraire le username pour l'API
                    username = None
                    if profile_url:
                        username = extract_username_from_url(profile_url)
                    if not username and reactor_urn:
                        # Si on a un URN, on peut essayer de l'utiliser
                        username = reactor_urn.split(':')[-1] if ':' in reactor_urn else reactor_urn
                    
                    if username:
                        # Appel API get_profile pour enrichir
                        profile_detail = get_profile_detail(username)
                        if profile_detail:
                            # Récupérer le scoring_breakdown existant
                            relevance_reasoning = prospect.get('relevance_reasoning', '')
                            scoring_breakdown = {}
                            if relevance_reasoning:
                                try:
                                    scoring_breakdown = json.loads(relevance_reasoning) if isinstance(relevance_reasoning, str) else relevance_reasoning
                                except:
                                    scoring_breakdown = {}
                            
                            # Ajouter les données enrichies
                            scoring_breakdown['enriched_profile'] = profile_detail
                            
                            # Enrichir aussi avec les données d'entreprise si disponible
                            company_name = prospect.get('detected_company') or prospect.get('company_name')
                            if company_name:
                                from utils.database import get_company_detail_from_db, save_company_detail
                                from utils.radar_manager import get_company_detail
                                
                                company_identifier = company_name.lower().strip()
                                company_detail = get_company_detail_from_db(company_identifier)
                                
                                if not company_detail:
                                    company_detail = get_company_detail(company_name)
                                    if company_detail:
                                        save_company_detail(company_identifier, company_name, company_detail)
                                
                                if company_detail:
                                    scoring_breakdown['enriched_company'] = company_detail
                            
                            # Mettre à jour la réaction dans la base
                            reaction_data = {
                                'company_name': prospect.get('company_name', ''),
                                'post_url': prospect.get('post_url', ''),
                                'post_date': str(prospect.get('post_date', '')),
                                'reactor_name': prospect.get('reactor_name', ''),
                                'reactor_urn': reactor_urn,
                                'profile_url': profile_url,
                                'reaction_type': prospect.get('reaction_type', ''),
                                'headline': prospect.get('headline', ''),
                                'profile_picture_url': prospect.get('profile_picture_url', ''),
                                'post_relevant': prospect.get('post_relevant', False),
                                'prospect_relevant': prospect.get('prospect_relevant', False),
                                'relevance_score': float(prospect.get('relevance_score', 0.0)),
                                'relevance_reasoning': json.dumps(scoring_breakdown) if scoring_breakdown else '',
                                'personalized_message': prospect.get('personalized_message', '')
                            }
                            
                            save_reaction(client_id, reaction_data)
                            success_count += 1
                        else:
                            error_count += 1
                            logger.warning(f"Impossible d'enrichir le profil: {prospect.get('reactor_name', 'Unknown')}")
                    else:
                        error_count += 1
                        logger.warning(f"Username non disponible pour: {prospect.get('reactor_name', 'Unknown')}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Erreur enrichissement prospect {prospect.get('reactor_name')}: {e}")
            
            progress_bar.empty()
            status_text.empty()
            
            if success_count > 0:
                st.success(f"✅ {success_count} prospect(s) enrichi(s) avec succès!")
            if error_count > 0:
                st.warning(f"⚠️ {error_count} erreur(s) lors de l'enrichissement")
            
            load_data.clear()
            st.rerun()

with col_sel5:
    if selected_count > 0:
        delete_key = "confirm_bulk_delete"
        if delete_key not in st.session_state:
            st.session_state[delete_key] = False
        
        if st.button("🗑️ Supprimer", type="secondary", use_container_width=True, help="Supprimer les prospects sélectionnés"):
            st.session_state[delete_key] = True
            st.rerun()
        
        if st.session_state[delete_key]:
            st.warning(f"⚠️ Confirmer la suppression de {selected_count} prospect(s) ?")
            col_conf1, col_conf2 = st.columns(2)
            with col_conf1:
                if st.button("✅ Confirmer", key="confirm_delete_yes", use_container_width=True, type="primary"):
                    selected_prospects_data = []
                    for idx, row in filtered_df.iterrows():
                        prospect_key = f"{row.get('reactor_urn', '')}_{row.get('post_url', '')}"
                        if prospect_key in st.session_state.selected_prospects:
                            selected_prospects_data.append({
                                'reactor_urn': row.get('reactor_urn', ''),
                                'post_url': row.get('post_url', ''),
                                'reactor_name': row.get('reactor_name', 'Unknown')
                            })
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    deleted_count = 0
                    error_count = 0
                    
                    for idx, prospect in enumerate(selected_prospects_data):
                        progress = (idx + 1) / len(selected_prospects_data)
                        progress_bar.progress(progress)
                        status_text.text(f"Suppression {idx + 1}/{len(selected_prospects_data)}: {prospect.get('reactor_name', 'Unknown')}")
                        
                        try:
                            if delete_reaction(client_id, prospect.get('reactor_urn', ''), prospect.get('post_url', '')):
                                deleted_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Erreur suppression prospect {prospect.get('reactor_name')}: {e}")
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    if deleted_count > 0:
                        st.success(f"✅ {deleted_count} prospect(s) supprimé(s)!")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} erreur(s)")
                    
                    st.session_state.selected_prospects = set()
                    st.session_state[delete_key] = False
                    load_data.clear()
                    st.rerun()
            with col_conf2:
                if st.button("❌ Annuler", key="confirm_delete_no", use_container_width=True):
                    st.session_state[delete_key] = False
                    st.rerun()

with col_sel5:
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if st.button("📤 Exporter CSV", use_container_width=True):
            output_path = Path("data/export_prospects.csv")
            if export_to_csv(filtered_df, output_path):
                with open(output_path, 'rb') as f:
                    st.download_button("📥 Télécharger CSV", f.read(), "prospects.csv", "text/csv", key="dl_csv", use_container_width=True)
    with col_exp2:
        if st.button("📤 Exporter Excel", use_container_width=True):
            output_path = Path("data/export_prospects.xlsx")
            if export_to_excel(filtered_df, output_path):
                with open(output_path, 'rb') as f:
                    st.download_button("📥 Télécharger Excel", f.read(), "prospects.xlsx",
                                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     key="dl_xlsx", use_container_width=True)

with col_sel6:
    st.markdown("")  # Espacement

st.markdown("<br>", unsafe_allow_html=True)

# ========== CALCULS DE PAGINATION ==========
total_prospects = len(filtered_df)
per_page = st.session_state.prospects_per_page
total_pages = max(1, (total_prospects + per_page - 1) // per_page) if total_prospects > 0 else 1
current_page = st.session_state.prospects_page

# S'assurer que la page actuelle est valide
if current_page >= total_pages:
    current_page = max(0, total_pages - 1)
    st.session_state.prospects_page = current_page

start_idx = current_page * per_page
end_idx = min(start_idx + per_page, total_prospects)

# ========== TABLEAU DES PROSPECTS ==========
st.markdown("### 📊 Liste des Prospects")

# Préparer les données pour la page actuelle
paginated_df = filtered_df.iloc[start_idx:end_idx].copy()
display_cols = ['reactor_name', 'headline', 'detected_company', 'company_name',
                'reaction_type', 'relevance_score', 'prospect_relevant',
                'personalized_message', 'profile_url', 'post_date']
available_cols = [col for col in display_cols if col in filtered_df.columns]
display_df = paginated_df[available_cols].copy() if not paginated_df.empty else pd.DataFrame(columns=available_cols)

# Formatage
if not display_df.empty:
    if 'post_date' in display_df.columns:
        display_df['post_date'] = display_df['post_date'].dt.strftime('%d/%m/%Y %H:%M')
    if 'prospect_relevant' in display_df.columns:
        display_df['prospect_relevant'] = display_df['prospect_relevant'].map({True: '✓', False: '✗'})
    if 'relevance_score' in display_df.columns:
        display_df['relevance_score'] = display_df['relevance_score'].round(2)
    
    # Colonne de sélection
    def create_selection_column(idx):
        if idx < len(paginated_df):
            row = paginated_df.iloc[idx]
            prospect_key = f"{row.get('reactor_urn', '')}_{row.get('post_url', '')}"
            return prospect_key in st.session_state.selected_prospects
        return False
    
    display_df['_select'] = [create_selection_column(i) for i in range(len(display_df))]

# Renommer colonnes
col_names = {
    'reactor_name': 'Nom',
    'headline': 'Titre',
    'detected_company': 'Entreprise',
    'company_name': 'Concurrent',
    'reaction_type': 'Réaction',
    'relevance_score': 'Score',
    'prospect_relevant': 'Qualifié',
    'personalized_message': 'Message',
    'profile_url': 'Profil',
    'post_date': 'Date',
    '_select': 'Sélection'
}
if not display_df.empty:
    display_df = display_df.rename(columns=col_names)
    if 'Sélection' in display_df.columns:
        cols_order = ['Sélection'] + [col for col in display_df.columns if col != 'Sélection']
        display_df = display_df[cols_order]

# Configuration des colonnes
column_config = {
    "Profil": st.column_config.LinkColumn("Profil", width="small"),
    "Sélection": st.column_config.CheckboxColumn("Sélection", width="small", default=False)
}

# Afficher le tableau
if not display_df.empty:
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500,
        key=f"prospects_table_{current_page}"
    )
    
    # Mettre à jour la sélection
    if edited_df is not None and not edited_df.empty and 'Sélection' in edited_df.columns:
        updated_selection = st.session_state.selected_prospects.copy()
        
        for idx in range(len(edited_df)):
            real_idx = start_idx + idx
            if real_idx < len(filtered_df):
                row = filtered_df.iloc[real_idx]
                prospect_key = f"{row.get('reactor_urn', '')}_{row.get('post_url', '')}"
                is_selected = edited_df.iloc[idx]['Sélection']
                
                if is_selected:
                    updated_selection.add(prospect_key)
                else:
                    updated_selection.discard(prospect_key)
        
        if updated_selection != st.session_state.selected_prospects:
            st.session_state.selected_prospects = updated_selection
            st.rerun()
else:
    st.info("Aucun prospect à afficher pour cette page.")

# ========== PAGINATION ÉPURÉE ==========
if total_pages > 1:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Pagination avec UI améliorée mais fonction identique
    pag_col1, pag_col2, pag_col3 = st.columns([2, 3, 2])
    
    with pag_col1:
        st.markdown("")
        st.caption(f"📄 Page {current_page + 1} sur {total_pages}")
        st.caption(f"📊 {start_idx + 1}-{end_idx} / {total_prospects} prospects")
    
    with pag_col2:
        page_options = list(range(1, total_pages + 1))
        selected_page = st.selectbox(
            "Aller à la page",
            options=page_options,
            index=current_page,
            key="page_selector",
            help=f"Naviguer vers une page spécifique (1-{total_pages})"
        )
        if selected_page != current_page + 1:
            st.session_state.prospects_page = selected_page - 1
            st.rerun()
    
    with pag_col3:
        st.markdown("")
        if selected_count > 0:
            st.caption(f"✅ {selected_count} sélectionné(s)")

st.markdown("<br>", unsafe_allow_html=True)

# ========== DÉTAILS D'UN PROSPECT ==========
with st.expander("👤 Détails d'un prospect", expanded=False):
    if not filtered_df.empty:
        # Dédupliquer les prospects par reactor_urn pour éviter les doublons dans le dropdown
        unique_prospects_df = filtered_df.drop_duplicates(subset='reactor_urn', keep='first').reset_index(drop=True)
        
        prospect_options = unique_prospects_df.apply(
            lambda row: f"{row.get('reactor_name', 'Unknown')} - {row.get('headline', '')[:50]}...",
            axis=1
        ).tolist()
        
        selected_prospect_idx = st.selectbox(
            "Choisir un prospect",
            options=range(len(prospect_options)),
            format_func=lambda x: prospect_options[x] if x < len(prospect_options) else "",
            index=0,
            key="prospect_detail_selector"
        )
        
        if selected_prospect_idx is not None and selected_prospect_idx < len(unique_prospects_df):
            prospect = unique_prospects_df.iloc[selected_prospect_idx]
            
            # Extraire les données enrichies AVANT l'affichage pour pouvoir les utiliser
            enriched_profile = None
            enriched_company = None
            reasoning_text = prospect.get('relevance_reasoning', '')
            if reasoning_text:
                try:
                    reasoning_data = json.loads(reasoning_text) if isinstance(reasoning_text, str) else reasoning_text
                    if isinstance(reasoning_data, dict):
                        if 'enriched_profile' in reasoning_data:
                            enriched_profile = reasoning_data.get('enriched_profile', {})
                        if 'enriched_company' in reasoning_data:
                            enriched_company = reasoning_data.get('enriched_company', {})
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Préparer l'URL LinkedIn (prioriser l'URL enrichie si disponible)
            profile_url_display = None
            if enriched_profile:
                # Les données enrichies peuvent être dans basic_info ou directement dans enriched_profile
                basic_info = enriched_profile.get('basic_info', {}) if isinstance(enriched_profile, dict) else {}
                
                # Essayer d'abord dans basic_info (format actuel de l'API)
                if basic_info and isinstance(basic_info, dict):
                    if basic_info.get('profile_url'):
                        profile_url_display = basic_info.get('profile_url')
                    elif basic_info.get('public_identifier'):
                        profile_url_display = f"https://www.linkedin.com/in/{basic_info.get('public_identifier')}"
                    elif basic_info.get('username'):
                        profile_url_display = f"https://www.linkedin.com/in/{basic_info.get('username')}"
                
                # Sinon essayer directement dans enriched_profile (ancien format)
                if not profile_url_display:
                    if enriched_profile.get('profile_url'):
                        profile_url_display = enriched_profile.get('profile_url')
                    elif enriched_profile.get('public_identifier'):
                        profile_url_display = f"https://www.linkedin.com/in/{enriched_profile.get('public_identifier')}"
                    elif enriched_profile.get('username'):
                        profile_url_display = f"https://www.linkedin.com/in/{enriched_profile.get('username')}"
            
            # Fallback sur l'URL stockée
            if not profile_url_display and 'profile_url' in prospect and prospect.get('profile_url'):
                profile_url_display = prospect.get('profile_url')
            
            # Nettoyer et formater l'URL pour l'affichage
            if profile_url_display:
                # Nettoyer l'URL pour s'assurer qu'elle est complète
                if not profile_url_display.startswith('http'):
                    if '/in/' in profile_url_display:
                        profile_url_display = f"https://www.{profile_url_display.lstrip('/')}"
                    else:
                        profile_url_display = f"https://www.linkedin.com/in/{profile_url_display}"
                # Normaliser l'URL (linkedin.com -> www.linkedin.com)
                if profile_url_display.startswith('https://linkedin.com'):
                    profile_url_display = profile_url_display.replace('https://linkedin.com', 'https://www.linkedin.com')
                # Retirer les paramètres de requête et les fragments
                profile_url_display = profile_url_display.split('?')[0].split('#')[0].rstrip('/')
            
            col_detail1, col_detail2 = st.columns(2)
            
            with col_detail1:
                st.markdown("**Informations Prospect**")
                st.markdown(f"**Nom:** {prospect.get('reactor_name', 'N/A')}")
                st.markdown(f"**Titre:** {prospect.get('headline', 'N/A')}")
                # Afficher l'entreprise (prioriser depuis basic_info si enrichi, sinon detected_company)
                company_display = None
                if enriched_profile:
                    # Récupérer basic_info si disponible
                    basic_info_for_company = enriched_profile.get('basic_info', {}) if isinstance(enriched_profile, dict) else {}
                    company_display = basic_info_for_company.get('current_company') or basic_info_for_company.get('company')
                
                if not company_display:
                    company_display = prospect.get('detected_company', 'N/A')
                
                st.markdown(f"**Entreprise:** {company_display if company_display and company_display != 'N/A' else 'N/A'}")
                st.markdown(f"**Concurrent:** {prospect.get('company_name', 'N/A')}")
                st.markdown(f"**Réaction:** {prospect.get('reaction_type', 'N/A')}")
                st.markdown(f"**Date:** {prospect.get('post_date', 'N/A')}")
                
                # Afficher l'URL LinkedIn (toujours afficher l'URL enrichie si disponible)
                if profile_url_display:
                    # Afficher avec un indicateur si c'est l'URL enrichie
                    is_enriched = enriched_profile and (
                        (isinstance(enriched_profile, dict) and enriched_profile.get('basic_info', {}).get('profile_url')) or
                        enriched_profile.get('profile_url') or
                        enriched_profile.get('public_identifier')
                    )
                    if is_enriched:
                        st.markdown(f"**Profil LinkedIn (enrichi):** [{profile_url_display}]({profile_url_display})")
                    else:
                        st.markdown(f"**Profil LinkedIn:** [{profile_url_display}]({profile_url_display})")
                elif 'profile_url' in prospect and prospect.get('profile_url'):
                    # Fallback si pas de données enrichies
                    st.markdown(f"**Profil LinkedIn:** [{prospect.get('profile_url')}]({prospect.get('profile_url')})")
            
            with col_detail2:
                st.markdown("**Scoring**")
                score = prospect.get('relevance_score', 0.0)
                st.metric("Score de pertinence", f"{score:.2f}/1.0")
                st.progress(float(score))
                
                is_relevant = prospect.get('prospect_relevant', False)
                st.markdown(f"**Qualifié:** {'✅ Oui' if is_relevant else '❌ Non'}")
                
                # Raisonnement IA
                reasoning_text = prospect.get('relevance_reasoning', '')
                if reasoning_text:
                    try:
                        reasoning_data = json.loads(reasoning_text) if isinstance(reasoning_text, str) else reasoning_text
                        if isinstance(reasoning_data, dict):
                            if 'reasoning' in reasoning_data:
                                st.markdown("**Raisonnement IA:**")
                                st.info(reasoning_data.get('reasoning', ''))
                            if 'breakdown' in reasoning_data:
                                with st.expander("📊 Breakdown du scoring"):
                                    breakdown = reasoning_data.get('breakdown', {})
                                    for key, value in breakdown.items():
                                        if isinstance(value, (int, float)):
                                            st.metric(key.replace('_', ' ').title(), f"{value:.2f}")
                            if 'strengths' in reasoning_data and reasoning_data.get('strengths'):
                                st.markdown("**Points forts:**")
                                for strength in reasoning_data.get('strengths', []):
                                    st.markdown(f"✅ {strength}")
                            if 'weaknesses' in reasoning_data and reasoning_data.get('weaknesses'):
                                st.markdown("**Points faibles:**")
                                for weakness in reasoning_data.get('weaknesses', []):
                                    st.markdown(f"⚠️ {weakness}")
                            if 'recommendation' in reasoning_data:
                                st.markdown(f"**Recommandation:** {reasoning_data.get('recommendation', '')}")
                    except (json.JSONDecodeError, TypeError):
                        st.text(reasoning_text[:200])
            
            # Informations enrichies (déjà extraites plus haut)
            if enriched_profile:
                st.markdown("---")
                st.markdown("### ✨ Informations Enrichies")
                
                # Les données enrichies peuvent être dans basic_info ou directement dans enriched_profile
                basic_info = enriched_profile.get('basic_info', {}) if isinstance(enriched_profile, dict) else {}
                
                col_enrich1, col_enrich2 = st.columns(2)
                
                with col_enrich1:
                    # Informations de base enrichies (prioriser basic_info)
                    full_name = basic_info.get('fullname') or basic_info.get('full_name') or enriched_profile.get('full_name')
                    if full_name:
                        st.markdown(f"**Nom complet:** {full_name}")
                    
                    headline = basic_info.get('headline') or enriched_profile.get('headline')
                    if headline:
                        st.markdown(f"**Headline:** {headline}")
                    
                    location = basic_info.get('location') or enriched_profile.get('location')
                    if location:
                        if isinstance(location, dict):
                            location_str = location.get('full', location.get('city', str(location)))
                        else:
                            location_str = str(location)
                        st.markdown(f"**Localisation:** {location_str}")
                    
                    about = basic_info.get('about') or enriched_profile.get('summary') or enriched_profile.get('about')
                    if about:
                        with st.expander("📝 Résumé"):
                            st.text(about)
                    
                    # Expérience professionnelle
                    if enriched_profile.get('experience'):
                        st.markdown("**💼 Expérience professionnelle:**")
                        experience_list = enriched_profile.get('experience', [])
                        if isinstance(experience_list, list) and len(experience_list) > 0:
                            for exp in experience_list[:5]:  # Limiter à 5 expériences
                                if isinstance(exp, dict):
                                    company = exp.get('company', exp.get('company_name', 'N/A'))
                                    title = exp.get('title', exp.get('position', 'N/A'))
                                    duration = exp.get('duration', exp.get('period', ''))
                                    st.markdown(f"  • **{title}** chez *{company}* {duration}")
                        else:
                            st.text("Aucune expérience disponible")
                
                with col_enrich2:
                    # Éducation
                    if enriched_profile.get('education'):
                        st.markdown("**🎓 Éducation:**")
                        education_list = enriched_profile.get('education', [])
                        if isinstance(education_list, list) and len(education_list) > 0:
                            for edu in education_list[:3]:  # Limiter à 3 formations
                                if isinstance(edu, dict):
                                    school = edu.get('school', edu.get('institution', 'N/A'))
                                    degree = edu.get('degree', edu.get('field_of_study', ''))
                                    st.markdown(f"  • {degree} - *{school}*")
                        else:
                            st.text("Aucune formation disponible")
                    
                    # Compétences
                    if enriched_profile.get('skills'):
                        st.markdown("**🛠️ Compétences:**")
                        skills_list = enriched_profile.get('skills', [])
                        if isinstance(skills_list, list) and len(skills_list) > 0:
                            # Gérer les cas où c'est une liste de strings ou de dicts
                            skills_display = []
                            for skill in skills_list[:10]:  # Limiter à 10 compétences
                                if isinstance(skill, str):
                                    skills_display.append(skill)
                                elif isinstance(skill, dict):
                                    # Extraire le nom de la compétence depuis le dict
                                    skill_name = skill.get('name', skill.get('skill', str(skill)))
                                    skills_display.append(skill_name)
                                else:
                                    skills_display.append(str(skill))
                            st.text(", ".join(skills_display) if skills_display else "Aucune compétence disponible")
                        else:
                            st.text("Aucune compétence disponible")
                    
                    # Statistiques
                    if enriched_profile.get('connections_count'):
                        st.markdown(f"**👥 Connexions:** {enriched_profile.get('connections_count', 'N/A')}")
                    if enriched_profile.get('followers_count'):
                        st.markdown(f"**👤 Abonnés:** {enriched_profile.get('followers_count', 'N/A')}")
                
                # Informations supplémentaires
                if enriched_profile.get('languages'):
                    st.markdown("**🌐 Langues:**")
                    languages_list = enriched_profile.get('languages', [])
                    if isinstance(languages_list, list):
                        # Gérer les cas où c'est une liste de strings ou de dicts
                        languages_display = []
                        for lang in languages_list:
                            if isinstance(lang, str):
                                languages_display.append(lang)
                            elif isinstance(lang, dict):
                                # Extraire le nom de la langue depuis le dict
                                lang_name = lang.get('name', lang.get('language', str(lang)))
                                languages_display.append(lang_name)
                            else:
                                languages_display.append(str(lang))
                        st.text(", ".join(languages_display) if languages_display else "Aucune langue disponible")
                    else:
                        st.text(str(languages_list))
                
                if enriched_profile.get('certifications'):
                    st.markdown("**🏆 Certifications:**")
                    certs_list = enriched_profile.get('certifications', [])
                    if isinstance(certs_list, list) and len(certs_list) > 0:
                        for cert in certs_list[:5]:  # Limiter à 5 certifications
                            if isinstance(cert, dict):
                                cert_name = cert.get('name', cert.get('title', 'N/A'))
                                issuer = cert.get('issuer', cert.get('organization', ''))
                                st.markdown(f"  • {cert_name}" + (f" - *{issuer}*" if issuer else ""))
                    else:
                        st.text("Aucune certification disponible")
            
            # Informations d'entreprise enrichies
            if enriched_company:
                st.markdown("---")
                st.markdown("### 🏢 Informations de l'Entreprise")
                
                # Les données peuvent être directement dans enriched_company ou dans enriched_company.data.basic_info
                company_data = enriched_company.get('data', {}) if 'data' in enriched_company else enriched_company
                basic_info_comp = company_data.get('basic_info', {}) if isinstance(company_data, dict) else {}
                
                # Utiliser basic_info si disponible, sinon utiliser directement company_data
                comp_info = basic_info_comp if basic_info_comp else company_data
                stats = company_data.get('stats', {}) if isinstance(company_data, dict) else {}
                
                col_comp1, col_comp2 = st.columns(2)
                
                with col_comp1:
                    # Nom de l'entreprise
                    company_name = comp_info.get('name') or company_data.get('name')
                    if company_name:
                        st.markdown(f"**Nom:** {company_name}")
                    
                    # Domaine de l'entreprise (extrait depuis l'URL du site web)
                    website = comp_info.get('website') or company_data.get('links', {}).get('website') if isinstance(company_data.get('links'), dict) else None
                    if website:
                        # Extraire le domaine depuis l'URL
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(website)
                            domain = parsed_url.netloc or parsed_url.path.split('/')[0] if parsed_url.path else None
                            # Retirer www. si présent
                            if domain:
                                domain = domain.replace('www.', '')
                                st.markdown(f"**Domaine:** {domain}")
                        except:
                            pass
                        st.markdown(f"**Site web:** [{website}]({website})")
                    
                    # Description
                    description = comp_info.get('description') or company_data.get('description') or company_data.get('tagline')
                    if description:
                        with st.expander("📝 Description"):
                            st.text(description)
                    
                    # Industries
                    industries = comp_info.get('industries', [])
                    if industries and isinstance(industries, list):
                        st.markdown(f"**Industries:** {', '.join(industries)}")
                    
                    # Taille (employee_count_range)
                    employee_range = stats.get('employee_count_range', {})
                    if employee_range:
                        start = employee_range.get('start', '')
                        end = employee_range.get('end', '')
                        if start and end:
                            st.markdown(f"**Taille:** {start}-{end} employés")
                    elif stats.get('employee_count'):
                        st.markdown(f"**Employés:** {stats.get('employee_count')}")
                
                with col_comp2:
                    # Localisation
                    locations = company_data.get('locations', {})
                    if locations and isinstance(locations, dict):
                        headquarters = locations.get('headquarters', {})
                        if headquarters:
                            location_str = headquarters.get('city', '') or headquarters.get('country', '')
                            if location_str:
                                st.markdown(f"**Localisation:** {location_str}")
                    
                    # Fondée en
                    founded_info = comp_info.get('founded_info', {})
                    if founded_info and isinstance(founded_info, dict):
                        year = founded_info.get('year')
                        if year:
                            st.markdown(f"**Fondée en:** {year}")
                    
                    # Employés
                    employee_count = stats.get('employee_count')
                    if employee_count:
                        st.markdown(f"**Employés:** {employee_count}")
                    
                    # Abonnés
                    follower_count = stats.get('follower_count')
                    if follower_count:
                        st.markdown(f"**Abonnés:** {follower_count}")
                    
                    # Spécialités
                    specialties = comp_info.get('specialties', [])
                    if specialties and isinstance(specialties, list) and len(specialties) > 0:
                        st.markdown("**Spécialités:**")
                        for spec in specialties[:5]:
                            if isinstance(spec, str):
                                st.markdown(f"  • {spec}")
                            elif isinstance(spec, dict):
                                spec_name = spec.get('name', spec.get('specialty', str(spec)))
                                st.markdown(f"  • {spec_name}")
                            else:
                                st.markdown(f"  • {str(spec)}")
                    
                    # LinkedIn URL
                    linkedin_url = comp_info.get('linkedin_url') or (company_data.get('links', {}).get('linkedin') if isinstance(company_data.get('links'), dict) else None)
                    if linkedin_url:
                        st.markdown(f"**LinkedIn:** [{linkedin_url}]({linkedin_url})")
            
            if not enriched_profile and not enriched_company:
                st.markdown("---")
                st.info("💡 Ce prospect n'a pas encore été enrichi. Utilisez le bouton '✨ Enrichir' pour récupérer plus d'informations.")
            
            # Message personnalisé
            if 'personalized_message' in prospect and prospect.get('personalized_message'):
                st.markdown("**💬 Message Personnalisé**")
                st.text_area("", value=prospect.get('personalized_message', ''), height=100, disabled=True, key=f"msg_{selected_prospect_idx}")
            
            # Actions
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if st.button("🔄 Recalculer scoring", key=f"recalc_{selected_prospect_idx}", use_container_width=True):
                    company_profile = get_client_profile_as_dict(client_id)
                    if not company_profile:
                        st.error("❌ Profil entreprise non trouvé.")
                    else:
                        with st.spinner("Recalcul en cours..."):
                            result = recalculate_prospect_scoring(
                                client_id,
                                prospect.get('reactor_urn', ''),
                                prospect.get('post_url', ''),
                                company_profile
                            )
                            if result:
                                st.success(f"✅ Score: {result.get('total_score', 0.0):.2f}")
                                load_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ Erreur lors du recalcul")
            
            with col_act2:
                delete_key = f"del_single_{selected_prospect_idx}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False
                
                if st.button("🗑️ Supprimer", key=f"del_{selected_prospect_idx}", use_container_width=True, type="secondary"):
                    st.session_state[delete_key] = True
                    st.rerun()
                
                if st.session_state[delete_key]:
                    st.warning(f"⚠️ Confirmer la suppression de {prospect.get('reactor_name', 'Unknown')} ?")
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        if st.button("✅ Oui", key=f"yes_{selected_prospect_idx}", use_container_width=True):
                            try:
                                if delete_reaction(client_id, prospect.get('reactor_urn', ''), prospect.get('post_url', '')):
                                    st.success("✅ Supprimé!")
                                    prospect_key = f"{prospect.get('reactor_urn', '')}_{prospect.get('post_url', '')}"
                                    if prospect_key in st.session_state.selected_prospects:
                                        st.session_state.selected_prospects.remove(prospect_key)
                                    st.session_state[delete_key] = False
                                    load_data.clear()
                                    st.rerun()
                                else:
                                    st.error("❌ Erreur")
                                    st.session_state[delete_key] = False
                            except Exception as e:
                                st.error(f"❌ Erreur: {e}")
                                st.session_state[delete_key] = False
                    with col_c2:
                        if st.button("❌ Non", key=f"no_{selected_prospect_idx}", use_container_width=True):
                            st.session_state[delete_key] = False
                            st.rerun()
