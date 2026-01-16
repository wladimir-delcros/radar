"""
Page Configuration - Gestion de la configuration (multi-client)
"""
import streamlit as st
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth, is_auth_enabled, set_password, verify_password
from utils.config_manager import load_config, save_config
from utils.session import render_client_selector, get_active_client_id
from utils.database import (
    get_all_clients, get_client, add_client, update_client, delete_client
)
from utils.styles import render_page_header

st.set_page_config(page_title="Configuration | LeadFlow", page_icon="⚙️", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Configuration",
    "Gerer la configuration du systeme"
)

# Onglets
tab1, tab2, tab3 = st.tabs(["API", "Clients", "Sécurité"])

# ============== Tab 1: Configuration API ==============
with tab1:
    st.subheader("Configuration API")

    config = load_config()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### RapidAPI")
        
        # Host commun
        rapidapi_host = st.text_input("Host RapidAPI",
                                      value=config.get('api_host', 'linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com'),
                                      help="Host commun pour toutes les clés API")
        
        st.markdown("---")
        st.markdown("#### 🔑 Clés API RapidAPI")
        st.caption("Ajoutez plusieurs clés API pour la rotation automatique")
        
        # Initialiser la liste des clés API dans session_state
        if 'rapidapi_keys_list' not in st.session_state:
            api_keys = config.get('api_keys', [])
            # Si pas de api_keys mais qu'il y a api_key (ancien format)
            if not api_keys and config.get('api_key'):
                # Migration depuis l'ancien format
                api_keys = [{
                    'api_key': config.get('api_key', ''),
                    'api_host': config.get('api_host', rapidapi_host),
                    'enabled': True  # Par défaut activée
                }]
            # S'assurer que toutes les clés ont un api_host et enabled
            for key_config in api_keys:
                if isinstance(key_config, dict):
                    if 'api_host' not in key_config:
                        key_config['api_host'] = rapidapi_host
                    if 'enabled' not in key_config:
                        key_config['enabled'] = True  # Par défaut activée
            st.session_state.rapidapi_keys_list = api_keys if api_keys else []
        
        # État pour afficher/masquer les clés
        if 'show_api_keys' not in st.session_state:
            st.session_state.show_api_keys = False
        
        # Bouton pour afficher/masquer les clés
        if st.session_state.rapidapi_keys_list:
            col_show, col_info = st.columns([1, 4])
            with col_show:
                # Le bouton affiche l'action à faire, pas l'état actuel
                # Si les clés sont masquées (show_api_keys = False), on affiche "Afficher"
                # Si les clés sont visibles (show_api_keys = True), on affiche "Masquer"
                is_hidden = not st.session_state.show_api_keys
                button_text = "👁️ Afficher" if is_hidden else "🙈 Masquer"
                button_type = "primary" if is_hidden else "secondary"
                
                if st.button(button_text, key="toggle_show_keys", use_container_width=True, type=button_type):
                    st.session_state.show_api_keys = not st.session_state.show_api_keys
                    st.rerun()
        
        # Réinitialiser si la config a changé (après sauvegarde)
        if 'config_saved' not in st.session_state:
            st.session_state.config_saved = False
        
        # Afficher les clés existantes
        rapidapi_keys_list = st.session_state.get('rapidapi_keys_list', [])
        
        # Debug: afficher le nombre de clés trouvées
        if rapidapi_keys_list:
            st.caption(f"📋 {len(rapidapi_keys_list)} clé(s) trouvée(s) dans la configuration")
        
        if rapidapi_keys_list and len(rapidapi_keys_list) > 0:
            for idx, key_config in enumerate(rapidapi_keys_list):
                if not isinstance(key_config, dict):
                    continue
                    
                displayed_key = key_config.get('api_key', '')
                if not displayed_key:
                    continue
                
                # État activé/désactivé (par défaut True si non défini)
                is_enabled = key_config.get('enabled', True)
                
                col_key, col_enable, col_del = st.columns([4, 1, 1])
                with col_key:
                    # Afficher la clé selon l'état
                    if st.session_state.show_api_keys:
                        # Afficher la clé complète en texte normal
                        status_icon = "✅" if is_enabled else "❌"
                        st.markdown(f"**Clé API #{idx + 1}** {status_icon}")
                        st.code(displayed_key, language=None)
                    else:
                        # Masquer la clé avec des points
                        masked_value = '•' * min(len(displayed_key), 20) if displayed_key else ''
                        status_icon = "✅" if is_enabled else "❌"
                        st.text_input(
                            f"Clé API #{idx + 1} {status_icon}",
                            value=masked_value,
                            disabled=True,
                            type='password',
                            key=f"display_key_{idx}",
                            help=f"Clé API: {displayed_key[:10]}...{displayed_key[-10:] if len(displayed_key) > 20 else ''}" + (f" - {'Activée' if is_enabled else 'Désactivée'}" if displayed_key else "")
                        )
                with col_enable:
                    st.markdown("<br>", unsafe_allow_html=True)
                    new_enabled_state = st.checkbox(
                        "Actif",
                        value=is_enabled,
                        key=f"enable_key_{idx}",
                        help="Activer/Désactiver cette clé API"
                    )
                    if new_enabled_state != is_enabled:
                        st.session_state.rapidapi_keys_list[idx]['enabled'] = new_enabled_state
                        st.rerun()
                with col_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_key_{idx}", help="Supprimer cette clé"):
                        st.session_state.rapidapi_keys_list.pop(idx)
                        st.rerun()
        else:
            st.info("ℹ️ Aucune clé API configurée. Ajoutez-en une ci-dessous.")
        
        # Formulaire pour ajouter une nouvelle clé
        st.markdown("---")
        with st.expander("➕ Ajouter une nouvelle clé API", expanded=False):
            new_key = st.text_input(
                "Nouvelle clé API RapidAPI",
                value="",
                type='password',
                key="new_rapidapi_key",
                help="Collez votre clé API RapidAPI ici"
            )
            if st.button("➕ Ajouter la clé", key="add_rapidapi_key", use_container_width=True):
                if new_key and new_key.strip():
                    # Vérifier si la clé n'existe pas déjà
                    existing_keys = [k.get('api_key', '') for k in st.session_state.rapidapi_keys_list]
                    if new_key.strip() not in existing_keys:
                        st.session_state.rapidapi_keys_list.append({
                            'api_key': new_key.strip(),
                            'api_host': rapidapi_host,
                            'enabled': True  # Par défaut activée
                        })
                        st.success(f"✅ Clé API ajoutée! ({len(st.session_state.rapidapi_keys_list)} clé(s) au total)")
                        st.rerun()
                    else:
                        st.warning("⚠️ Cette clé API est déjà configurée")
                else:
                    st.error("❌ Veuillez entrer une clé API valide")
        
        # Afficher le nombre de clés
        if st.session_state.rapidapi_keys_list:
            total_keys = len(st.session_state.rapidapi_keys_list)
            enabled_keys = sum(1 for k in st.session_state.rapidapi_keys_list if k.get('enabled', True))
            disabled_keys = total_keys - enabled_keys
            status_text = f"📊 {total_keys} clé(s) API configurée(s)"
            if disabled_keys > 0:
                status_text += f" - ✅ {enabled_keys} activée(s), ❌ {disabled_keys} désactivée(s)"
            st.info(status_text)

    with col2:
        st.markdown("### OpenAI")
        openai_config = config.get('openai', {})
        openai_key = st.text_input("Cle API OpenAI",
                                   value=openai_config.get('api_key', ''),
                                   type='password')
        openai_model = st.selectbox("Modele",
                                    ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'],
                                    index=0 if openai_config.get('model', 'gpt-4o-mini') == 'gpt-4o-mini' else 1)
        openai_temperature = st.slider("Temperature", 0.0, 1.0, openai_config.get('temperature', 0.3), 0.1)
        openai_threshold = st.slider("Seuil de pertinence", 0.0, 1.0, openai_config.get('relevance_threshold', 0.6), 0.1)
        openai_enabled = st.checkbox("Activer l'analyse IA", value=openai_config.get('enabled', True))

    if st.button("Sauvegarder la Configuration API", key="save_api", type="primary", use_container_width=True):
        # Préparer la configuration avec les clés API
        rapidapi_keys_list = st.session_state.get('rapidapi_keys_list', [])
        
        # Mettre à jour le host pour toutes les clés
        for key_config in rapidapi_keys_list:
            key_config['api_host'] = rapidapi_host
        
        new_config = {
            'api_host': rapidapi_host,
            'api_keys': rapidapi_keys_list,
            # Rétrocompatibilité: garder la première clé comme api_key principale
            'api_key': rapidapi_keys_list[0].get('api_key', '') if rapidapi_keys_list else '',
            'limit': config.get('limit', 1),
            'output_directory': config.get('output_directory', 'data'),
            'openai': {
                'api_key': openai_key,
                'model': openai_model,
                'temperature': openai_temperature,
                'max_tokens': openai_config.get('max_tokens', 500),
                'enabled': openai_enabled,
                'relevance_threshold': openai_threshold
            }
        }
        
        if not rapidapi_keys_list:
            st.error("❌ Veuillez ajouter au moins une clé API RapidAPI")
        elif save_config(new_config):
            st.success(f"✅ Configuration sauvegardée! ({len(rapidapi_keys_list)} clé(s) API configurée(s))")
            st.cache_data.clear()
            # Forcer le rechargement de la liste depuis la config
            st.session_state.force_reload_keys = True
            if 'rapidapi_keys_list' in st.session_state:
                del st.session_state.rapidapi_keys_list
            st.rerun()
        else:
            st.error("❌ Erreur lors de la sauvegarde")

# ============== Tab 3: Sécurité ==============
with tab3:
    st.subheader("🔐 Sécurité de l'Application")
    
    auth_enabled = is_auth_enabled()
    
    st.markdown("### Protection par mot de passe")
    
    if auth_enabled:
        st.success("✅ L'authentification est activée. Un mot de passe est requis pour accéder à l'application.")
    else:
        st.warning("⚠️ L'authentification n'est pas activée. L'application est accessible sans mot de passe.")
    
    st.markdown("---")
    
    # Définir un nouveau mot de passe
    st.markdown("### Définir / Modifier le mot de passe")
    
    with st.form("password_form"):
        new_password = st.text_input("Nouveau mot de passe", type="password", help="Le mot de passe sera hashé et stocké de manière sécurisée")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit_password = st.form_submit_button("💾 Définir le mot de passe", use_container_width=True)
        with col2:
            if auth_enabled:
                disable_auth = st.form_submit_button("🔓 Désactiver l'authentification", use_container_width=True, type="secondary")
            else:
                disable_auth = False
        
        if submit_password:
            if not new_password:
                st.error("❌ Le mot de passe ne peut pas être vide.")
            elif new_password != confirm_password:
                st.error("❌ Les mots de passe ne correspondent pas.")
            elif len(new_password) < 4:
                st.error("❌ Le mot de passe doit contenir au moins 4 caractères.")
            else:
                set_password(new_password)
                st.success("✅ Mot de passe défini avec succès ! L'authentification est maintenant activée.")
                st.info("ℹ️ Vous devrez vous reconnecter avec ce nouveau mot de passe.")
                st.rerun()
        
        if disable_auth:
            from utils.auth import load_auth_config, save_auth_config
            auth_config = load_auth_config()
            auth_config['enabled'] = False
            save_auth_config(auth_config)
            st.success("✅ Authentification désactivée.")
            st.rerun()
    
    # Tester le mot de passe actuel
    if auth_enabled:
        st.markdown("---")
        st.markdown("### Tester le mot de passe actuel")
        
        with st.form("test_password_form"):
            test_password = st.text_input("Mot de passe actuel", type="password")
            test_submit = st.form_submit_button("🔍 Tester", use_container_width=True)
            
            if test_submit:
                if verify_password(test_password):
                    st.success("✅ Le mot de passe est correct.")
                else:
                    st.error("❌ Le mot de passe est incorrect.")

# ============== Tab 2: Gestion des Clients ==============
with tab2:
    st.subheader("Gestion des Clients")

    clients = get_all_clients()

    # Liste des clients
    st.markdown("### Liste des clients")
    for c in clients:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            st.write(f"**{c['name']}** - {c.get('description', '')[:50]}...")
        with col2:
            if c['id'] == client_id:
                st.success("Actif")
        with col3:
            if st.button("✏️ Éditer", key=f"edit_client_{c['id']}", use_container_width=True):
                st.session_state[f'edit_client_id_{c["id"]}'] = c['id']
                st.rerun()
        with col4:
            if len(clients) > 1 and c['id'] != client_id:
                if st.button("🗑️ Supprimer", key=f"del_client_{c['id']}", use_container_width=True, type="secondary"):
                    delete_client(c['id'])
                    st.rerun()
        
        # Formulaire d'édition
        if f'edit_client_id_{c["id"]}' in st.session_state and st.session_state[f'edit_client_id_{c["id"]}'] == c['id']:
            st.markdown("---")
            st.markdown(f"#### ✏️ Édition du client: {c['name']}")
            
            with st.form(key=f"edit_client_form_{c['id']}"):
                edited_name = st.text_input(
                    "Nom du client",
                    value=c.get('name', ''),
                    key=f"edit_name_{c['id']}"
                )
                edited_description = st.text_area(
                    "Description",
                    value=c.get('description', ''),
                    height=100,
                    key=f"edit_desc_{c['id']}"
                )
                edited_website = st.text_input(
                    "Site web",
                    value=c.get('website', ''),
                    key=f"edit_website_{c['id']}"
                )
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    save_edited = st.form_submit_button("💾 Sauvegarder", type="primary", use_container_width=True)
                with col_cancel:
                    cancel_edit = st.form_submit_button("❌ Annuler", use_container_width=True)
                
                if save_edited:
                    if edited_name:
                        try:
                            update_client(c['id'], edited_name, edited_description, edited_website)
                            st.success("✅ Client modifié avec succès!")
                            if f'edit_client_id_{c["id"]}' in st.session_state:
                                del st.session_state[f'edit_client_id_{c["id"]}']
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la modification: {e}")
                    else:
                        st.error("Le nom du client est requis")
                
                if cancel_edit:
                    if f'edit_client_id_{c["id"]}' in st.session_state:
                        del st.session_state[f'edit_client_id_{c["id"]}']
                    st.rerun()
            
            st.markdown("---")

    st.markdown("---")

    # Ajouter un client
    st.markdown("### Ajouter un nouveau client")
    with st.form("add_client_form"):
        new_client_name = st.text_input("Nom du client")
        new_client_desc = st.text_area("Description", height=100)
        new_client_website = st.text_input("Site web")

        if st.form_submit_button("Ajouter le client"):
            if new_client_name:
                try:
                    add_client(new_client_name, new_client_desc, new_client_website)
                    st.success(f"Client '{new_client_name}' ajoute!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")
            else:
                st.error("Le nom du client est requis")
