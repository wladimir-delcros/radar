"""
Module d'authentification pour l'application Streamlit
"""
import streamlit as st
import hashlib
import json
from pathlib import Path
from typing import Optional

CONFIG_FILE = Path(__file__).parent.parent / "config.json"
AUTH_CONFIG_KEY = "app_password"


def get_password_hash(password: str) -> str:
    """Génère un hash SHA256 du mot de passe"""
    return hashlib.sha256(password.encode()).hexdigest()


def load_auth_config() -> dict:
    """Charge la configuration d'authentification depuis config.json"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('auth', {})
        except Exception:
            pass
    return {}


def save_auth_config(auth_config: dict):
    """Sauvegarde la configuration d'authentification dans config.json"""
    # Charger la config existante
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            config = {}
    else:
        config = {}
    
    # Mettre à jour la section auth
    config['auth'] = auth_config
    
    # Sauvegarder
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_stored_password_hash() -> Optional[str]:
    """Récupère le hash du mot de passe stocké"""
    auth_config = load_auth_config()
    return auth_config.get('password_hash')


def set_password(password: str):
    """Définit un nouveau mot de passe"""
    password_hash = get_password_hash(password)
    auth_config = load_auth_config()
    auth_config['password_hash'] = password_hash
    auth_config['enabled'] = True
    save_auth_config(auth_config)


def verify_password(password: str) -> bool:
    """Vérifie si le mot de passe est correct"""
    stored_hash = get_stored_password_hash()
    if not stored_hash:
        return False
    return get_password_hash(password) == stored_hash


def is_auth_enabled() -> bool:
    """Vérifie si l'authentification est activée"""
    auth_config = load_auth_config()
    return auth_config.get('enabled', False)


def is_authenticated() -> bool:
    """Vérifie si l'utilisateur est authentifié dans la session"""
    return st.session_state.get('authenticated', False)


def set_authenticated(value: bool = True):
    """Définit l'état d'authentification dans la session"""
    st.session_state.authenticated = value


def render_login_form() -> bool:
    """
    Affiche le formulaire de connexion et retourne True si l'authentification réussit
    
    Returns:
        True si l'utilisateur est authentifié, False sinon
    """
    # Vérifier si l'authentification est activée
    if not is_auth_enabled():
        # Si pas de mot de passe configuré, permettre l'accès
        set_authenticated(True)
        return True
    
    # Si déjà authentifié, permettre l'accès
    if is_authenticated():
        return True
    
    # Afficher le formulaire de connexion
    st.title("🔐 Authentification")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Connexion requise")
        st.info("Veuillez entrer le mot de passe pour accéder à l'application.")
        
        with st.form("login_form"):
            password = st.text_input("Mot de passe", type="password", autofocus=True)
            submit_button = st.form_submit_button("Se connecter", use_container_width=True)
            
            if submit_button:
                if verify_password(password):
                    set_authenticated(True)
                    st.success("✅ Authentification réussie !")
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect. Veuillez réessayer.")
    
    return False


def require_auth():
    """
    Décorateur/fonction pour protéger une page - doit être appelé au début de chaque page
    
    Si l'utilisateur n'est pas authentifié, affiche le formulaire de connexion et arrête l'exécution
    """
    if not is_authenticated():
        if not render_login_form():
            st.stop()
