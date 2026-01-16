"""
Page Radars - Gestion des différents types de radars LinkedIn
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.session import render_client_selector
from utils.database import (
    get_client, get_radars, get_radar, add_radar, update_radar,
    delete_radar, update_radar_last_run, get_competitors,
    get_radar_targets, add_radar_target, delete_radar_targets,
    get_radar_message_template, save_radar_message_template, get_client_profile_as_dict,
    get_client_profile
)
from utils.ai_analyzer import generate_message_for_prospect
from utils.radar_manager import process_radar, process_radar_with_scoring
from utils.radar_scheduler import schedule_radar, unschedule_radar, get_next_run_time, get_scheduler_status
from utils.database import save_reaction, save_reactions_batch, get_client_profile_as_dict
from utils.styles import render_page_header, render_metric_card
from utils.log_capture import setup_log_capture, format_log_for_display

st.set_page_config(page_title="Radars | LeadFlow", page_icon="🎯", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Radars",
    f"Gestion des radars de veille LinkedIn - {client['name'] if client else ''}"
)

# Charger les radars
radars = get_radars(client_id)

# Onglets
tab1, tab2, tab3, tab4 = st.tabs(["📋 Liste des Radars", "➕ Nouveau Radar", "▶️ Exécuter un Radar", "⏰ Scheduling"])

# ============== ONGLET 1: Liste des Radars ==============
with tab1:
    if not radars:
        st.markdown("""
            <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3);
                        border-radius: 12px; padding: 3rem; text-align: center; margin-top: 2rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🎯</div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.5rem;">
                    Aucun radar configuré
                </div>
                <div style="color: #94a3b8;">
                    Créez votre premier radar pour commencer la veille LinkedIn
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Métriques
        enabled_count = len([r for r in radars if r['enabled']])
        total_count = len(radars)
        scheduled_count = len([r for r in radars if r.get('schedule_type') != 'manual' and r.get('schedule_interval', 0) > 0])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(render_metric_card(total_count, "Radars Total"), unsafe_allow_html=True)
        with col2:
            st.markdown(render_metric_card(enabled_count, "Radars Actifs"), unsafe_allow_html=True)
        with col3:
            st.markdown(render_metric_card(total_count - enabled_count, "Radars Inactifs"), unsafe_allow_html=True)
        with col4:
            st.markdown(render_metric_card(scheduled_count, "Radars Planifiés"), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tableau des radars
        st.markdown("""
            <div class="data-card">
                <div class="data-card-header">
                    <div class="data-card-title">Liste des Radars</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Préparer les données pour l'affichage
        radar_data = []
        for radar in radars:
            radar_type_label = {
                'competitor_last_post': '📊 Dernier post concurrent',
                'person_last_post': '👤 Dernier post personne',
                'keyword_posts': '🔍 Posts par mot-clé'
            }.get(radar['radar_type'], radar['radar_type'])
            
            schedule_info = "Manuel"
            if radar.get('schedule_type') != 'manual' and radar.get('schedule_interval', 0) > 0:
                interval = radar.get('schedule_interval', 0)
                schedule_type = radar.get('schedule_type', '')
                if schedule_type == 'minutes':
                    schedule_info = f"Toutes les {interval} min"
                elif schedule_type == 'hours':
                    schedule_info = f"Toutes les {interval}h"
                elif schedule_type == 'days':
                    schedule_info = f"Tous les {interval} jours"
            
            max_extractions = radar.get('max_extractions')
            limit_display = str(max_extractions) if max_extractions else "Illimité"
            
            radar_data.append({
                'ID': radar['id'],
                'Nom': radar['name'],
                'Type': radar_type_label,
                'Cible': radar['target_identifier'],
                'Mot-clé': radar.get('keyword', ''),
                'Nb Posts': radar.get('post_count', 1),
                'Limite': limit_display,
                'Statut': '🟢 Actif' if radar['enabled'] else '🔴 Inactif',
                'Scheduling': schedule_info,
                'Score min': radar.get('min_score_threshold', 0.6),
                'Dernière exécution': radar.get('last_run_at', 'Jamais')[:19] if radar.get('last_run_at') else 'Jamais',
                'Créé le': radar['created_at'][:19] if radar.get('created_at') else ''
            })
        
        df_radars = pd.DataFrame(radar_data)
        
        if not df_radars.empty:
            st.dataframe(df_radars, use_container_width=True, hide_index=True, height=400)
            
            # Actions sur les radars
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Actions")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                selected_radar_id = st.selectbox(
                    "Sélectionner un radar",
                    options=[r['id'] for r in radars],
                    format_func=lambda x: next((r['name'] for r in radars if r['id'] == x), '')
                )
            
            with col2:
                if st.button("✏️ Éditer", use_container_width=True, type="primary"):
                    if selected_radar_id:
                        st.session_state['edit_radar_id'] = selected_radar_id
                        st.rerun()
            
            with col3:
                if st.button("🔄 Activer/Désactiver", use_container_width=True):
                    if selected_radar_id:
                        radar = get_radar(selected_radar_id)
                        if radar:
                            update_radar(selected_radar_id, enabled=not radar['enabled'])
                            st.success(f"Radar {'activé' if not radar['enabled'] else 'désactivé'}")
                            st.rerun()
            
            with col4:
                if st.button("🗑️ Supprimer", use_container_width=True, type="secondary"):
                    if selected_radar_id:
                        if delete_radar(selected_radar_id):
                            st.success("Radar supprimé")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression")
            
            # Section d'édition
            if 'edit_radar_id' in st.session_state and st.session_state['edit_radar_id']:
                edit_radar_id = st.session_state['edit_radar_id']
                edit_radar = get_radar(edit_radar_id)
                
                if edit_radar:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("---")
                    st.subheader(f"✏️ Édition du radar: {edit_radar['name']}")
                    
                    # Formulaire d'édition
                    with st.form(key=f"edit_radar_form_{edit_radar_id}"):
                        # Nom du radar
                        edited_name = st.text_input(
                            "Nom du radar",
                            value=edit_radar.get('name', ''),
                            key=f"edit_name_{edit_radar_id}"
                        )
                        
                        # Type de radar (non modifiable, mais affiché)
                        radar_type_readonly = {
                            'competitor_last_post': '📊 Engagés du dernier post d\'un concurrent',
                            'person_last_post': '👤 Engagés du dernier post d\'une personne',
                            'keyword_posts': '🔍 X derniers posts sur une thématique (mot-clé)'
                        }.get(edit_radar['radar_type'], edit_radar['radar_type'])
                        st.info(f"**Type:** {radar_type_readonly} (non modifiable)")
                        
                        edited_radar_type = edit_radar['radar_type']
                        
                        # Champs spécifiques selon le type
                        if edited_radar_type == 'competitor_last_post':
                            competitors = get_competitors(client_id)
                            if competitors:
                                competitor_options = [c['company_name'] for c in competitors]
                                # Récupérer les cibles existantes
                                existing_targets = get_radar_targets(edit_radar_id)
                                existing_competitors = [edit_radar.get('target_identifier')] + [
                                    t['target_value'] for t in existing_targets if t['target_type'] == 'competitor'
                                ]
                                existing_competitors = [c for c in existing_competitors if c]
                                
                                edited_selected_competitors = st.multiselect(
                                    "Sélectionner un ou plusieurs concurrents",
                                    options=competitor_options,
                                    default=[c for c in existing_competitors if c in competitor_options],
                                    key=f"edit_competitors_{edit_radar_id}",
                                    help="Vous pouvez sélectionner plusieurs concurrents pour un seul radar"
                                )
                                if edited_selected_competitors:
                                    edited_target_identifier = edited_selected_competitors[0]
                                else:
                                    edited_target_identifier = st.text_input(
                                        "Nom du concurrent (saisie libre)",
                                        value=existing_competitors[0] if existing_competitors else '',
                                        key=f"edit_competitor_free_{edit_radar_id}",
                                        placeholder="ex: growthroom"
                                    )
                                    edited_selected_competitors = [edited_target_identifier] if edited_target_identifier else []
                            else:
                                edited_target_identifier = st.text_input(
                                    "Nom du concurrent",
                                    value=edit_radar.get('target_identifier', ''),
                                    key=f"edit_competitor_{edit_radar_id}",
                                    placeholder="ex: growthroom"
                                )
                                edited_selected_competitors = [edited_target_identifier] if edited_target_identifier else []
                        
                        elif edited_radar_type == 'person_last_post':
                            # Récupérer les cibles existantes
                            existing_targets = get_radar_targets(edit_radar_id)
                            existing_urls = [edit_radar.get('target_value', '')] + [
                                t['target_value'] for t in existing_targets if t['target_type'] == 'person'
                            ]
                            existing_urls = [url for url in existing_urls if url]
                            existing_urls_text = '\n'.join(existing_urls)
                            
                            edited_profile_urls_input = st.text_area(
                                "URLs des profils LinkedIn (une par ligne)",
                                value=existing_urls_text,
                                key=f"edit_profile_urls_{edit_radar_id}",
                                placeholder="https://www.linkedin.com/in/john-doe/\nhttps://www.linkedin.com/in/jane-doe/",
                                help="Entrez une ou plusieurs URLs de profils LinkedIn, une par ligne"
                            )
                            if edited_profile_urls_input:
                                edited_profile_urls = [url.strip() for url in edited_profile_urls_input.split('\n') if url.strip()]
                                edited_target_identifier = edited_profile_urls[0] if edited_profile_urls else None
                                edited_target_value = edited_profile_urls[0] if edited_profile_urls else None
                            else:
                                edited_profile_urls = []
                                edited_target_identifier = None
                                edited_target_value = None
                        
                        elif edited_radar_type == 'keyword_posts':
                            edited_keyword = st.text_input(
                                "Mot-clé à rechercher",
                                value=edit_radar.get('keyword', ''),
                                key=f"edit_keyword_{edit_radar_id}",
                                placeholder="ex: intelligence artificielle, marketing automation..."
                            )
                            st.markdown("#### Nombre de posts à analyser")
                            edited_post_count = st.number_input(
                                "Nombre de posts à analyser",
                                min_value=1,
                                max_value=50,
                                value=edit_radar.get('post_count', 10),
                                key=f"edit_post_count_{edit_radar_id}",
                                help="Nombre de posts récents contenant le mot-clé à analyser",
                                label_visibility="collapsed"
                            )
                            edited_target_identifier = edited_keyword
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Limite d'extraction/export
                        st.markdown("### Limite d'Extraction/Export")
                        edited_max_extractions = st.number_input(
                            "Nombre maximum d'engagés à extraire et sauvegarder par exécution",
                            min_value=1,
                            max_value=1000,
                            value=edit_radar.get('max_extractions') if edit_radar.get('max_extractions') else None,
                            key=f"edit_max_extractions_{edit_radar_id}",
                            help="Limite le nombre d'engagés collectés ET sauvegardés dans la base (ex: 50 sur 300). Les doublons sont automatiquement exclus. Laissez vide pour illimité.",
                            placeholder="Illimité"
                        )
                        if edited_max_extractions == 0:
                            edited_max_extractions = None
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Configuration du scoring et filtrage
                        st.markdown("### Configuration du Scoring")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            edited_filter_competitors = st.checkbox(
                                "Filtrer les concurrents",
                                value=edit_radar.get('filter_competitors', True),
                                key=f"edit_filter_{edit_radar_id}",
                                help="Les personnes travaillant pour vos concurrents seront automatiquement exclues"
                            )
                        with col2:
                            edited_min_score_threshold = st.slider(
                                "Score minimum pour qualifier",
                                min_value=0.0,
                                max_value=1.0,
                                value=float(edit_radar.get('min_score_threshold', 0.6)),
                                step=0.05,
                                key=f"edit_score_{edit_radar_id}",
                                help="Score minimum (0-1) pour qu'un prospect soit considéré comme qualifié"
                            )
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Section Message Type du Radar
                        st.markdown("### 💬 Message Type du Radar")
                        st.caption("Ce message type sera utilisé comme base pour générer les messages personnalisés des prospects de ce radar")
                        
                        # Récupérer le message template actuel ou celui généré
                        current_message_template = get_radar_message_template(edit_radar_id) or ''
                        
                        # DEBUG: Log pour voir l'état
                        generated_key = f'generated_template_{edit_radar_id}'
                        textarea_key = f"edit_message_template_{edit_radar_id}"
                        
                        # Déterminer la valeur initiale AVANT de créer le widget
                        # Priorité: message généré > valeur existante dans session_state > valeur de la DB
                        if generated_key in st.session_state:
                            generated_value = st.session_state[generated_key]
                            logger.info(f"[DEBUG] Message généré trouvé dans session_state (clé: {generated_key}): {generated_value[:100] if generated_value else 'vide'}...")
                            # Si la clé textarea n'existe pas encore, l'initialiser avec le message généré
                            # Si elle existe déjà, on ne peut pas la modifier (widget déjà créé), donc on utilise generated_value comme valeur par défaut
                            if textarea_key not in st.session_state:
                                st.session_state[textarea_key] = generated_value
                                textarea_value = generated_value
                                logger.info(f"[DEBUG] Initialisation du textarea avec le message généré (longueur: {len(generated_value)})")
                            else:
                                # La clé existe déjà, on ne peut pas la modifier, on utilise generated_value comme valeur par défaut
                                textarea_value = generated_value
                                logger.info(f"[DEBUG] Utilisation du message généré comme valeur (clé textarea existe déjà, longueur: {len(generated_value)})")
                        elif textarea_key not in st.session_state:
                            # Initialiser avec la valeur de la DB si pas déjà dans session_state
                            st.session_state[textarea_key] = current_message_template
                            textarea_value = current_message_template
                            logger.info(f"[DEBUG] Initialisation du textarea avec la valeur de la DB: {current_message_template[:100] if current_message_template else 'vide'}...")
                        else:
                            # Utiliser la valeur existante dans session_state
                            textarea_value = st.session_state[textarea_key]
                            logger.info(f"[DEBUG] Utilisation de la valeur existante dans session_state: {textarea_value[:100] if textarea_value else 'vide'}...")
                        
                        logger.info(f"[DEBUG] Valeur finale utilisée pour le textarea (longueur: {len(textarea_value)}): {textarea_value[:100] if textarea_value else 'vide'}...")
                        
                        edited_message_template = st.text_area(
                            "Message type",
                            value=textarea_value,
                            height=150,
                            key=textarea_key,
                            placeholder="Exemple: Je te contacte car j'ai vu que tu as réagi à un post de [entreprise] sur [sujet]. C'est quelque chose que nous faisons chez [notre entreprise]. Est-ce une problématique que vous rencontrez ?",
                            help="Ce template sera utilisé comme base pour générer les messages personnalisés. Vous pouvez utiliser des variables comme [entreprise], [sujet], [notre entreprise]."
                        )
                        
                        logger.info(f"[DEBUG] Valeur retournée par le textarea (longueur: {len(edited_message_template) if edited_message_template else 0}): {edited_message_template[:100] if edited_message_template else 'vide'}...")
                        
                        col_gen_msg, col_clear_msg = st.columns(2)
                        with col_gen_msg:
                            if st.form_submit_button("✨ Générer avec IA", key=f"gen_msg_{edit_radar_id}", use_container_width=True):
                                company_profile = get_client_profile_as_dict(client_id)
                                if company_profile:
                                    # Récupérer le profil pour le persona
                                    profile = get_client_profile(client_id) or {}
                                    
                                    # Générer un message type basé sur le radar
                                    radar_type = edit_radar.get('radar_type', '')
                                    radar_name = edit_radar.get('name', 'Sans nom')
                                    target_identifier = edit_radar.get('target_identifier', '')
                                    keyword = edit_radar.get('keyword', '')
                                    
                                    # Construire le contexte selon le type de radar
                                    if radar_type == 'competitor_last_post':
                                        context = f"Radar sur les derniers posts du concurrent '{target_identifier}'. Les prospects réagissent aux posts de cette entreprise."
                                    elif radar_type == 'person_last_post':
                                        context = f"Radar sur les derniers posts de la personne '{target_identifier}'. Les prospects réagissent aux posts de cette personne."
                                    elif radar_type == 'keyword_posts':
                                        context = f"Radar sur les posts contenant le mot-clé '{keyword}'. Les prospects réagissent à des posts sur ce sujet."
                                    else:
                                        context = f"Radar '{radar_name}' de type '{radar_type}'."
                                    
                                    # Créer un prompt pour générer le message type
                                    prompt = f"""Tu es un expert en outbound B2B. Génère un message type (template) LinkedIn pour ce radar.

Contexte du radar:
{context}

Notre entreprise:
- Nom: {company_profile.get('company_name', '')}
- Description: {company_profile.get('company_description', '')}
- Ce qu'on offre: {company_profile.get('outreach_strategy', {}).get('what_offers', '')}
- Proposition de valeur: {company_profile.get('outreach_strategy', {}).get('value_proposition', '')}

Persona cible:
- Titres de poste: {', '.join(company_profile.get('target_persona', {}).get('job_titles', []))}
- Secteurs: {', '.join(company_profile.get('target_persona', {}).get('industries', []))}
- Pain points: {', '.join(company_profile.get('target_persona', {}).get('pain_points', []))}

Template de message général:
- Ton: {profile.get('message_tone', 'professionnel, amical')}
- Structure: {profile.get('message_structure', '')}
- Points clés: {', '.join(profile.get('message_key_points', []))}

Génère un message type (template) court (maximum 100 mots) en français qui:
1. Fait référence à la réaction du prospect sur le post du radar
2. Connecte avec notre solution en se basant sur le persona
3. Pose une question ouverte pertinente
4. Est naturel, personnel et engageant

Utilise des variables comme [entreprise], [sujet], [notre entreprise], [prospect] pour la personnalisation future.

Réponds UNIQUEMENT avec le message type, sans markdown, sans "Message:", sans guillemets."""
                                    
                                    try:
                                        from utils.ai_analyzer import openai_client, OPENAI_ENABLED, OPENAI_MODEL
                                        if OPENAI_ENABLED and openai_client:
                                            with st.spinner("Génération en cours..."):
                                                response = openai_client.chat.completions.create(
                                                    model=OPENAI_MODEL,
                                                    messages=[
                                                        {"role": "system", "content": "Tu es un expert en rédaction de messages outbound B2B. Réponds UNIQUEMENT avec le message final, sans formatage supplémentaire."},
                                                        {"role": "user", "content": prompt}
                                                    ],
                                                    temperature=0.7,
                                                    max_tokens=200
                                                )
                                                generated_template = response.choices[0].message.content.strip()
                                                
                                                # Nettoyer le message
                                                if generated_template.startswith('"') and generated_template.endswith('"'):
                                                    generated_template = generated_template[1:-1]
                                                if generated_template.startswith("Message:"):
                                                    generated_template = generated_template[8:].strip()
                                                
                                                if generated_template:
                                                    generated_key = f'generated_template_{edit_radar_id}'
                                                    textarea_key = f"edit_message_template_{edit_radar_id}"
                                                    
                                                    logger.info(f"[DEBUG] Message généré par OpenAI (longueur: {len(generated_template)}): {generated_template[:100]}...")
                                                    
                                                    # Stocker le message généré
                                                    st.session_state[generated_key] = generated_template
                                                    
                                                    # Supprimer la clé du textarea pour forcer sa réinitialisation au prochain rendu
                                                    # Cela permet d'éviter l'erreur "cannot be modified after widget is instantiated"
                                                    if textarea_key in st.session_state:
                                                        del st.session_state[textarea_key]
                                                        logger.info(f"[DEBUG] Clé textarea supprimée pour forcer la réinitialisation")
                                                    
                                                    logger.info(f"[DEBUG] Message stocké dans session_state avec la clé: {generated_key}")
                                                    
                                                    st.success("✅ Message type généré avec succès!")
                                                    st.rerun()
                                                else:
                                                    logger.error("[DEBUG] Aucun message généré par OpenAI (réponse vide)")
                                                    st.error("❌ Aucun message généré")
                                        else:
                                            st.error("❌ OpenAI non configuré")
                                    except Exception as e:
                                        st.error(f"❌ Erreur: {e}")
                                else:
                                    st.error("❌ Profil entreprise non trouvé")
                        
                        with col_clear_msg:
                            if st.form_submit_button("🗑️ Effacer", key=f"clear_msg_{edit_radar_id}", use_container_width=True):
                                if f'generated_template_{edit_radar_id}' in st.session_state:
                                    del st.session_state[f'generated_template_{edit_radar_id}']
                                st.rerun()
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_edited = st.form_submit_button("💾 Sauvegarder les modifications", type="primary", use_container_width=True)
                        with col_cancel:
                            cancel_edit = st.form_submit_button("❌ Annuler", use_container_width=True)
                        
                        if save_edited:
                            try:
                                # Sauvegarder le message template d'abord (peut être modifié même si le radar n'est pas sauvegardé)
                                if edited_message_template:
                                    save_radar_message_template(edit_radar_id, edited_message_template)
                                    # Nettoyer le session state si un message avait été généré
                                    if f'generated_template_{edit_radar_id}' in st.session_state:
                                        del st.session_state[f'generated_template_{edit_radar_id}']
                                
                                # Préparer les valeurs selon le type
                                if edited_radar_type == 'competitor_last_post':
                                    keyword_value = None
                                    post_count_value = 1
                                    target_value = None
                                    if not edited_selected_competitors:
                                        st.error("Veuillez sélectionner ou saisir au moins un concurrent")
                                    else:
                                        # Mettre à jour le radar
                                        update_radar(
                                            edit_radar_id,
                                            name=edited_name,
                                            target_identifier=edited_target_identifier,
                                            filter_competitors=edited_filter_competitors,
                                            min_score_threshold=edited_min_score_threshold,
                                            max_extractions=edited_max_extractions
                                        )
                                        # Mettre à jour les cibles multiples
                                        delete_radar_targets(edit_radar_id)
                                        for idx, competitor in enumerate(edited_selected_competitors[1:], start=1):
                                            add_radar_target(edit_radar_id, 'competitor', competitor, idx)
                                        st.success("✅ Radar modifié avec succès!")
                                        if 'edit_radar_id' in st.session_state:
                                            del st.session_state['edit_radar_id']
                                        st.rerun()
                                
                                elif edited_radar_type == 'person_last_post':
                                    if not edited_profile_urls:
                                        st.error("Veuillez saisir au moins une URL de profil LinkedIn")
                                    else:
                                        update_radar(
                                            edit_radar_id,
                                            name=edited_name,
                                            target_identifier=edited_profile_urls[0],
                                            target_value=edited_profile_urls[0],
                                            filter_competitors=edited_filter_competitors,
                                            min_score_threshold=edited_min_score_threshold,
                                            max_extractions=edited_max_extractions
                                        )
                                        # Mettre à jour les cibles multiples
                                        delete_radar_targets(edit_radar_id)
                                        for idx, profile_url in enumerate(edited_profile_urls[1:], start=1):
                                            add_radar_target(edit_radar_id, 'person', profile_url, idx)
                                        st.success("✅ Radar modifié avec succès!")
                                        if 'edit_radar_id' in st.session_state:
                                            del st.session_state['edit_radar_id']
                                        st.rerun()
                                
                                elif edited_radar_type == 'keyword_posts':
                                    if not edited_keyword:
                                        st.error("Veuillez saisir un mot-clé")
                                    else:
                                        update_radar(
                                            edit_radar_id,
                                            name=edited_name,
                                            target_identifier=edited_keyword,
                                            keyword=edited_keyword,
                                            post_count=edited_post_count,
                                            filter_competitors=edited_filter_competitors,
                                            min_score_threshold=edited_min_score_threshold,
                                            max_extractions=edited_max_extractions
                                        )
                                        st.success("✅ Radar modifié avec succès!")
                                        if 'edit_radar_id' in st.session_state:
                                            del st.session_state['edit_radar_id']
                                        st.rerun()
                                
                            except Exception as e:
                                st.error(f"Erreur lors de la modification du radar: {e}")
                        
                        if cancel_edit:
                            if 'edit_radar_id' in st.session_state:
                                del st.session_state['edit_radar_id']
                            st.rerun()

# ============== ONGLET 2: Nouveau Radar ==============
with tab2:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">Créer un Nouveau Radar</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    radar_type = st.selectbox(
        "Type de radar",
        options=['competitor_last_post', 'person_last_post', 'keyword_posts'],
        format_func=lambda x: {
            'competitor_last_post': '📊 Engagés du dernier post d\'un concurrent',
            'person_last_post': '👤 Engagés du dernier post d\'une personne',
            'keyword_posts': '🔍 X derniers posts sur une thématique (mot-clé)'
        }[x]
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if radar_type == 'competitor_last_post':
        # Radar: Dernier post concurrent (multi-cibles)
        competitors = get_competitors(client_id)
        if competitors:
            competitor_options = [c['company_name'] for c in competitors]
            selected_competitors = st.multiselect(
                "Sélectionner un ou plusieurs concurrents",
                options=competitor_options,
                help="Vous pouvez sélectionner plusieurs concurrents pour un seul radar"
            )
            if selected_competitors:
                target_identifier = selected_competitors[0]  # Premier pour compatibilité
                # Les autres seront ajoutés via radar_targets
            else:
                target_identifier = None
        else:
            st.warning("Aucun concurrent configuré. Allez dans Configuration > Concurrents pour en ajouter.")
            target_identifier = st.text_input("Nom du concurrent", placeholder="ex: growthroom")
            selected_competitors = [target_identifier] if target_identifier else []
        
        radar_name = st.text_input(
            "Nom du radar",
            value=f"Radar - {len(selected_competitors)} concurrent(s)" if selected_competitors else "Radar - Concurrent"
        )
    
    elif radar_type == 'person_last_post':
        # Radar: Dernier post personne (multi-cibles)
        profile_urls_input = st.text_area(
            "URLs des profils LinkedIn (une par ligne)",
            placeholder="https://www.linkedin.com/in/john-doe/\nhttps://www.linkedin.com/in/jane-doe/",
            help="Entrez une ou plusieurs URLs de profils LinkedIn, une par ligne"
        )
        if profile_urls_input:
            profile_urls = [url.strip() for url in profile_urls_input.split('\n') if url.strip()]
            target_identifier = profile_urls[0] if profile_urls else None
        else:
            profile_urls = []
            target_identifier = None
        
        radar_name = st.text_input(
            "Nom du radar",
            value=f"Radar - {len(profile_urls)} personne(s)" if profile_urls else "Radar - Profil personne"
        )
    
    elif radar_type == 'keyword_posts':
        # Radar: Posts par mot-clé
        keyword = st.text_input(
            "Mot-clé à rechercher",
            placeholder="ex: intelligence artificielle, marketing automation..."
        )
        st.markdown("#### Nombre de posts à analyser")
        post_count = st.number_input(
            "Nombre de posts à analyser",
            min_value=1,
            max_value=50,
            value=10,
            help="Nombre de posts récents contenant le mot-clé à analyser",
            label_visibility="collapsed"
        )
        target_identifier = keyword
        radar_name = st.text_input(
            "Nom du radar",
            value=f"Radar - {keyword if keyword else 'Mot-clé'}"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Configuration du scoring et filtrage
    st.markdown("### Configuration du Scoring")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_competitors = st.checkbox(
            "Filtrer les concurrents",
            value=True,
            help="Les personnes travaillant pour vos concurrents seront automatiquement exclues"
        )
    with col2:
        min_score_threshold = st.slider(
            "Score minimum pour qualifier",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.05,
            help="Score minimum (0-1) pour qu'un prospect soit considéré comme qualifié"
        )
    
    # Limite d'extraction/export (sur les profils QUALIFIÉS après scoring IA)
    st.markdown("### Limite d'Extraction/Export")
    max_extractions = st.number_input(
        "Nombre maximum de prospects QUALIFIÉS à sauvegarder par exécution",
        min_value=1,
        max_value=1000,
        value=None,
        help="Limite le nombre de prospects QUALIFIÉS (après scoring IA) à sauvegarder. L'IA analysera tous les profils, mais seuls les N meilleurs qualifiés seront sauvegardés. Les doublons sont automatiquement exclus. Laissez vide pour illimité.",
        placeholder="Illimité"
    )
    if max_extractions == 0:
        max_extractions = None
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("➕ Créer le Radar", type="primary", use_container_width=True):
        if not radar_name:
            st.error("Le nom du radar est obligatoire")
        elif radar_type == 'competitor_last_post' and not selected_competitors:
            st.error("Veuillez sélectionner au moins un concurrent")
        elif radar_type == 'person_last_post' and not profile_urls:
            st.error("Veuillez saisir au moins une URL de profil LinkedIn")
        elif radar_type == 'keyword_posts' and not target_identifier:
            st.error("Veuillez saisir un mot-clé")
        else:
            try:
                keyword_value = keyword if radar_type == 'keyword_posts' else None
                post_count_value = post_count if radar_type == 'keyword_posts' else 1
                target_value = target_identifier if radar_type == 'person_last_post' else None
                
                radar_id = add_radar(
                    client_id=client_id,
                    name=radar_name,
                    radar_type=radar_type,
                    target_identifier=target_identifier,
                    target_value=target_value,
                    keyword=keyword_value,
                    post_count=post_count_value,
                    filter_competitors=filter_competitors,
                    min_score_threshold=min_score_threshold
                )
                
                # Ajouter les cibles multiples si nécessaire
                if radar_type == 'competitor_last_post' and len(selected_competitors) > 1:
                    for idx, competitor in enumerate(selected_competitors[1:], start=1):
                        add_radar_target(radar_id, 'competitor', competitor, idx)
                
                elif radar_type == 'person_last_post' and len(profile_urls) > 1:
                    for idx, profile_url in enumerate(profile_urls[1:], start=1):
                        add_radar_target(radar_id, 'person', profile_url, idx)
                
                st.success(f"✅ Radar '{radar_name}' créé avec succès!")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la création du radar: {e}")

# ============== ONGLET 3: Exécuter un Radar ==============
with tab3:
    if not radars:
        st.info("Créez d'abord un radar dans l'onglet 'Nouveau Radar'")
    else:
        st.markdown("""
            <div class="data-card">
                <div class="data-card-header">
                    <div class="data-card-title">Exécuter un Radar</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        enabled_radars = [r for r in radars if r['enabled']]
        
        if not enabled_radars:
            st.warning("Aucun radar activé. Activez d'abord un radar dans l'onglet 'Liste des Radars'")
        else:
            selected_radar_id = st.selectbox(
                "Sélectionner un radar à exécuter",
                options=[r['id'] for r in enabled_radars],
                format_func=lambda x: next((r['name'] for r in enabled_radars if r['id'] == x), '')
            )
            
            if selected_radar_id:
                radar = get_radar(selected_radar_id)
                
                if radar:
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    radar_type_label = {
                        'competitor_last_post': '📊 Dernier post concurrent',
                        'person_last_post': '👤 Dernier post personne',
                        'keyword_posts': '🔍 Posts par mot-clé'
                    }.get(radar['radar_type'], radar['radar_type'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Type:** {radar_type_label}")
                    with col2:
                        st.info(f"**Cible:** {radar['target_identifier']}")
                    
                    if radar.get('keyword'):
                        st.info(f"**Mot-clé:** {radar['keyword']}")
                    if radar.get('post_count', 1) > 1:
                        st.info(f"**Nombre de posts:** {radar['post_count']}")
                    
                    st.info(f"**Filtrage concurrents:** {'Activé' if radar.get('filter_competitors', True) else 'Désactivé'}")
                    st.info(f"**Score minimum:** {radar.get('min_score_threshold', 0.6)}")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Zone de logs
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    col_logs_title, col_copy = st.columns([3, 1])
                    with col_logs_title:
                        st.markdown("### 📋 Console de logs")
                    with col_copy:
                        # Bouton pour copier les logs (uniquement si des logs existent)
                        if 'radar_logs' in st.session_state and st.session_state.radar_logs:
                            logs_text = "\n".join(st.session_state.radar_logs)
                            
                            # Utiliser JavaScript pour copier dans le presse-papier (plus fiable)
                            copy_button_id = "copy_logs_btn"
                            
                            st.markdown(f"""
                                <button id="{copy_button_id}" style="
                                    background: #6366f1;
                                    color: white;
                                    border: none;
                                    border-radius: 6px;
                                    padding: 0.5rem 1rem;
                                    cursor: pointer;
                                    font-size: 0.9rem;
                                    width: 100%;
                                ">📋 Copier les logs</button>
                                <script>
                                    document.getElementById('{copy_button_id}').addEventListener('click', function() {{
                                        const logs = `{logs_text.replace('`', '\\`').replace('$', '\\$')}`;
                                        navigator.clipboard.writeText(logs).then(function() {{
                                            alert('✅ Logs copiés dans le presse-papier!');
                                        }}, function(err) {{
                                            // Fallback pour navigateurs anciens
                                            const textarea = document.createElement('textarea');
                                            textarea.value = logs;
                                            document.body.appendChild(textarea);
                                            textarea.select();
                                            document.execCommand('copy');
                                            document.body.removeChild(textarea);
                                            alert('✅ Logs copiés dans le presse-papier!');
                                        }});
                                    }});
                                </script>
                            """, unsafe_allow_html=True)
                        
                    log_container = st.empty()
                    logs_code_container = st.empty()
                    
                    # Afficher les logs précédents si disponibles
                    if 'radar_logs' in st.session_state and st.session_state.radar_logs:
                        logs_html = "".join([
                            format_log_for_display(log)
                            for log in st.session_state.radar_logs
                        ])
                        
                        # Affichage stylisé HTML
                        log_container.markdown(f"""
                            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; 
                                        font-family: 'Courier New', monospace; font-size: 0.85rem; 
                                        max-height: 400px; overflow-y: auto; line-height: 1.5;">
                                {logs_html}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Affichage en texte brut sélectionnable pour copier facilement (Ctrl+C / Cmd+C)
                        logs_text = "\n".join(st.session_state.radar_logs)
                        st.markdown("**📄 Version texte (sélectionnable et copiable avec Ctrl+C / Cmd+C) :**")
                        logs_code_container.code(logs_text, language=None)
                    
                    if st.button("▶️ Exécuter le Radar", type="primary", use_container_width=True):
                        # Initialiser la liste des logs
                        st.session_state.radar_logs = []
                        
                        # Configurer la capture de logs
                        log_handler = setup_log_capture()
                        log_handler.clear()
                        
                        try:
                            # Afficher un message d'initialisation
                            st.session_state.radar_logs.append(f"[INFO] 🚀 Démarrage de l'exécution du radar: {radar['name']}")
                            st.session_state.radar_logs.append(f"[INFO] Type: {radar_type_label}")
                            st.session_state.radar_logs.append(f"[INFO] Cible: {radar['target_identifier']}")
                            
                            # Afficher les logs initiaux
                            logs_html = "".join([format_log_for_display(log) for log in st.session_state.radar_logs])
                            logs_text = "\n".join(st.session_state.radar_logs)
                            
                            log_container.markdown(f"""
                                <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; 
                                            font-family: 'Courier New', monospace; font-size: 0.85rem; 
                                            max-height: 400px; overflow-y: auto; line-height: 1.5;">
                                    {logs_html}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # Affichage en texte brut sélectionnable pour copier facilement
                            st.markdown("**📄 Version texte (sélectionnable et copiable avec Ctrl+C / Cmd+C) :**")
                            logs_code_container.code(logs_text, language=None)
                            
                            with st.spinner("Exécution du radar en cours..."):
                                # Charger le profil et les concurrents
                                st.session_state.radar_logs.append("[INFO] 📥 Chargement du profil entreprise...")
                                company_profile = get_client_profile_as_dict(client_id)
                                competitors = get_competitors(client_id)
                                st.session_state.radar_logs.append(f"[INFO] ✓ Profil chargé - {len(competitors)} concurrent(s) configuré(s)")
                                
                                # Traiter le radar avec scoring
                                st.session_state.radar_logs.append("[INFO] 🔍 Récupération des posts et réactions...")
                                max_qualified = radar.get('max_extractions')
                                if max_qualified:
                                    st.session_state.radar_logs.append(f"[INFO] 📊 Limite: {max_qualified} prospect(s) qualifié(s) maximum")
                                reactions = process_radar_with_scoring(
                                    radar,
                                    client_id,
                                    company_profile,
                                    competitors,
                                    min_score_threshold=radar.get('min_score_threshold', 0.6),
                                    filter_competitors=radar.get('filter_competitors', True),
                                    max_qualified_prospects=max_qualified
                                )
                                
                                # Récupérer les logs capturés depuis les modules
                                captured_logs = log_handler.get_logs()
                                if captured_logs:
                                    st.session_state.radar_logs.extend(captured_logs)
                                
                                st.session_state.radar_logs.append(f"[INFO] ✓ Traitement terminé - {len(reactions)} prospect(s) qualifié(s) et enrichi(s)")
                                
                                if reactions:
                                    st.session_state.radar_logs.append("[INFO] Étape 7/7: Sauvegarde des prospects qualifiés dans la base de données...")
                                    st.session_state.radar_logs.append(f"[INFO] 📊 {len(reactions)} prospect(s) qualifié(s) à sauvegarder")
                                    
                                    # Sauvegarder les réactions qualifiées (la limite a déjà été appliquée dans process_radar_with_scoring)
                                    saved_count = 0
                                    for idx, reaction in enumerate(reactions, 1):
                                        try:
                                            # Adapter les données pour save_reaction
                                            scoring_breakdown = reaction.get('scoring_breakdown', {})
                                            enriched_profile = reaction.get('enriched_profile', {})
                                            
                                            # Fusionner les données enrichies dans le scoring_breakdown pour les sauvegarder
                                            if enriched_profile:
                                                scoring_breakdown['enriched_profile'] = enriched_profile
                                            if reaction.get('enriched_company'):
                                                scoring_breakdown['enriched_company'] = reaction.get('enriched_company')
                                            
                                            # Utiliser le profile_url enrichi si disponible (vrai slug)
                                            profile_url_to_save = reaction.get('profile_url', '')
                                            
                                            reaction_data = {
                                                'company_name': reaction.get('company_name') or reaction.get('keyword') or '',
                                                'post_url': reaction.get('post_url', ''),
                                                'post_date': reaction.get('post_date', ''),
                                                'reactor_name': reaction.get('reactor_name', ''),
                                                'reactor_urn': reaction.get('reactor_urn', ''),
                                                'profile_url': profile_url_to_save,  # Utilise le profile_url enrichi (vrai slug)
                                                'reaction_type': reaction.get('reaction_type', ''),
                                                'headline': reaction.get('headline', ''),
                                                'profile_picture_url': reaction.get('profile_picture_url', ''),
                                                'post_relevant': False,
                                                'prospect_relevant': reaction.get('prospect_relevant', False),
                                                'relevance_score': reaction.get('relevance_score', 0.0),
                                                'relevance_reasoning': json.dumps(scoring_breakdown) if scoring_breakdown else '',
                                                'personalized_message': ''
                                            }
                                            save_reaction(client_id, reaction_data)
                                            saved_count += 1
                                            
                                            # Log tous les 10 pour ne pas surcharger
                                            if saved_count % 10 == 0:
                                                st.session_state.radar_logs.append(f"[INFO]   → {saved_count} réaction(s) sauvegardée(s)...")
                                        except Exception as e:
                                            st.session_state.radar_logs.append(f"[ERROR] ❌ Erreur sauvegarde réaction {idx}: {e}")
                                    
                                    # Mettre à jour la date de dernière exécution
                                    update_radar_last_run(selected_radar_id)
                                    st.session_state.radar_logs.append(f"[SUCCESS] ✅ {saved_count} réaction(s) qualifiée(s) sauvegardée(s) avec succès!")
                                    
                                    # Afficher les logs dans la console
                                    logs_html = "".join([format_log_for_display(log) for log in st.session_state.radar_logs])
                                    logs_text = "\n".join(st.session_state.radar_logs)
                                    
                                    log_container.markdown(f"""
                                        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; 
                                                    font-family: 'Courier New', monospace; font-size: 0.85rem; 
                                                    max-height: 400px; overflow-y: auto; line-height: 1.5;">
                                            {logs_html}
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Affichage en texte brut sélectionnable pour copier facilement
                                    st.markdown("**📄 Version texte (sélectionnable et copiable avec Ctrl+C / Cmd+C) :**")
                                    logs_code_container.code(logs_text, language=None)
                                    
                                    st.success(f"✅ Radar exécuté avec succès!")
                                    st.success(f"📊 {saved_count} réaction(s) qualifiée(s) collectée(s) et sauvegardée(s)")
                                    st.info("💡 Les réactions sont maintenant disponibles dans l'onglet 'Prospects'")
                                else:
                                    st.session_state.radar_logs.append("[WARNING] ⚠️ Aucune réaction qualifiée trouvée pour ce radar")
                                    
                                    logs_html = "".join([format_log_for_display(log) for log in st.session_state.radar_logs])
                                    logs_text = "\n".join(st.session_state.radar_logs)
                                    
                                    log_container.markdown(f"""
                                        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; 
                                                    font-family: 'Courier New', monospace; font-size: 0.85rem; 
                                                    max-height: 400px; overflow-y: auto; line-height: 1.5;">
                                            {logs_html}
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Affichage en texte brut sélectionnable pour copier facilement
                                    st.markdown("**📄 Version texte (sélectionnable et copiable avec Ctrl+C / Cmd+C) :**")
                                    logs_code_container.code(logs_text, language=None)
                                    
                                    st.warning("⚠️ Aucune réaction qualifiée trouvée pour ce radar")
                                
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            st.session_state.radar_logs.append(f"[ERROR] ❌ Erreur lors de l'exécution: {e}")
                            st.session_state.radar_logs.append(f"[ERROR] Détails: {error_details}")
                            
                            logs_html = "".join([format_log_for_display(log) for log in st.session_state.radar_logs])
                            logs_text = "\n".join(st.session_state.radar_logs)
                            
                            log_container.markdown(f"""
                                <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1rem; 
                                            font-family: 'Courier New', monospace; font-size: 0.85rem; 
                                            max-height: 400px; overflow-y: auto; line-height: 1.5;">
                                    {logs_html}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # Affichage en texte brut sélectionnable pour copier facilement
                            st.markdown("**📄 Version texte (sélectionnable et copiable avec Ctrl+C / Cmd+C) :**")
                            logs_code_container.code(logs_text, language=None)
                            
                            st.error(f"❌ Erreur lors de l'exécution du radar: {e}")
                            st.exception(e)

# ============== ONGLET 4: Scheduling ==============
with tab4:
    if not radars:
        st.info("Créez d'abord un radar dans l'onglet 'Nouveau Radar'")
    else:
        st.markdown("""
            <div class="data-card">
                <div class="data-card-header">
                    <div class="data-card-title">Configuration du Scheduling</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Statut du scheduler
        scheduler_status = get_scheduler_status()
        if scheduler_status.get('available'):
            if scheduler_status.get('running'):
                st.success(f"✅ Scheduler actif - {scheduler_status.get('jobs_count', 0)} job(s) planifié(s)")
            else:
                st.warning("⚠️ Scheduler non démarré. Utilisez le script linkedin_scraper_radars_scheduled.py pour démarrer le scheduler.")
        else:
            st.error("❌ APScheduler non disponible. Installez-le avec: pip install APScheduler")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Sélectionner un radar
        selected_radar_id = st.selectbox(
            "Sélectionner un radar à configurer",
            options=[r['id'] for r in radars],
            format_func=lambda x: next((r['name'] for r in radars if r['id'] == x), '')
        )
        
        if selected_radar_id:
            radar = get_radar(selected_radar_id)
            
            if radar:
                st.markdown("### Configuration du Planning")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    schedule_type = st.selectbox(
                        "Type de planification",
                        options=['manual', 'minutes', 'hours', 'days'],
                        index=['manual', 'minutes', 'hours', 'days'].index(radar.get('schedule_type', 'manual')),
                        format_func=lambda x: {
                            'manual': '🔴 Manuel (aucune planification)',
                            'minutes': '⏱️ Toutes les X minutes',
                            'hours': '⏰ Toutes les X heures',
                            'days': '📅 Tous les X jours'
                        }[x]
                    )
                
                with col2:
                    if schedule_type != 'manual':
                        schedule_interval = st.number_input(
                            "Intervalle",
                            min_value=1,
                            max_value=1000,
                            value=radar.get('schedule_interval', 60) if radar.get('schedule_type') != 'manual' else 60,
                            help="Nombre de minutes/heures/jours entre chaque exécution"
                        )
                    else:
                        schedule_interval = 0
                
                # Afficher la prochaine exécution si planifié
                if schedule_type != 'manual' and schedule_interval > 0:
                    next_run = get_next_run_time(selected_radar_id)
                    if next_run:
                        st.info(f"⏰ Prochaine exécution: {next_run.strftime('%d/%m/%Y %H:%M:%S')}")
                    else:
                        st.info("💡 Le scheduling sera activé après la sauvegarde et le démarrage du scheduler")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("💾 Sauvegarder la Configuration", type="primary", use_container_width=True):
                    try:
                        update_radar(
                            selected_radar_id,
                            schedule_type=schedule_type,
                            schedule_interval=schedule_interval
                        )
                        
                        # Mettre à jour le scheduler
                        if schedule_type != 'manual' and schedule_interval > 0:
                            if schedule_radar(selected_radar_id):
                                st.success("✅ Configuration sauvegardée et radar planifié!")
                            else:
                                st.warning("⚠️ Configuration sauvegardée mais le scheduler n'est pas disponible")
                        else:
                            unschedule_radar(selected_radar_id)
                            st.success("✅ Configuration sauvegardée - Scheduling désactivé")
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la sauvegarde: {e}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Instructions
                st.markdown("### Instructions")
                st.info("""
                **Pour activer le scheduling automatique:**
                1. Configurez le type et l'intervalle ci-dessus
                2. Sauvegardez la configuration
                3. Démarrez le script `linkedin_scraper_radars_scheduled.py` pour exécuter les radars automatiquement
                
                **Commandes:**
                - `python linkedin_scraper_radars_scheduled.py` : Démarre le scheduler en continu
                - `python linkedin_scraper_radars_scheduled.py --run-once` : Exécute une fois tous les radars planifiés
                - `python linkedin_scraper_radars_scheduled.py --client-id 1` : Seulement pour un client spécifique
                """)
