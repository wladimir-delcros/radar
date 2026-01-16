"""
Module de gestion des radars LinkedIn
Supporte différents types de radars:
- competitor_last_post: Engagés du dernier post d'un concurrent
- person_last_post: Engagés du dernier post d'une personne
- keyword_posts: X derniers posts sur une thématique (keyword)
"""
import requests
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import quote
import threading
from utils.database import save_company_detail, get_company_detail_from_db

logger = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = Path(__file__).parent.parent / "config.json"
API_BASE_URL = "https://linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
ROTATION_STATE_FILE = Path(__file__).parent.parent / "api_rotation_state.json"

# Lock pour thread-safety
_rotation_lock = threading.Lock()


def load_config() -> Dict[str, Any]:
    """Charge la configuration depuis le fichier config.json"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.warning(f"Erreur lors du chargement de la config: {e}")
    
    return {
        "api_key": "8d94f2d4b9msh384e09aab682e2bp173e86jsn7b448f5e8961",
        "api_host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }


def load_rotation_state() -> Dict[str, int]:
    """Charge l'état de rotation depuis le fichier"""
    if ROTATION_STATE_FILE.exists():
        try:
            with open(ROTATION_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Erreur lors du chargement de l'état de rotation: {e}")
    return {}


def save_rotation_state(state: Dict[str, int]):
    """Sauvegarde l'état de rotation dans le fichier"""
    try:
        with open(ROTATION_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"Erreur lors de la sauvegarde de l'état de rotation: {e}")


def get_api_keys() -> List[Dict[str, str]]:
    """
    Récupère la liste des clés API configurées (uniquement les clés activées)
    
    Returns:
        Liste de dictionnaires avec 'api_key' et 'api_host' (uniquement les clés activées)
    """
    config = load_config()
    api_host = config.get("api_host", "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com")
    
    # Support pour plusieurs formats de configuration
    api_keys_list = []
    
    # Format 1: Liste de clés API dans 'api_keys'
    if "api_keys" in config and isinstance(config["api_keys"], list):
        for key_config in config["api_keys"]:
            if isinstance(key_config, dict):
                # Vérifier si la clé est activée (par défaut True si non défini)
                is_enabled = key_config.get("enabled", True)
                if is_enabled:  # Ne retourner que les clés activées
                    api_keys_list.append({
                        "api_key": key_config.get("api_key", ""),
                        "api_host": key_config.get("api_host", api_host)
                    })
            elif isinstance(key_config, str):
                api_keys_list.append({
                    "api_key": key_config,
                    "api_host": api_host
                })
    
    # Format 2: Clé API unique (rétrocompatibilité)
    if not api_keys_list and "api_key" in config:
        api_keys_list.append({
            "api_key": config.get("api_key", ""),
            "api_host": api_host
        })
    
    # Si aucune clé trouvée, utiliser la valeur par défaut
    if not api_keys_list:
        api_keys_list.append({
            "api_key": "8d94f2d4b9msh384e09aab682e2bp173e86jsn7b448f5e8961",
            "api_host": api_host
        })
    
    return api_keys_list


def get_current_api_key(endpoint: str = "default") -> Dict[str, str]:
    """
    Récupère la clé API actuelle sans faire de rotation
    
    Args:
        endpoint: Nom de l'endpoint pour gérer des rotations séparées (optionnel)
    
    Returns:
        Dictionnaire avec 'api_key' et 'api_host'
    """
    with _rotation_lock:
        api_keys = get_api_keys()
        if not api_keys:
            raise ValueError("Aucune clé API configurée")
        
        state = load_rotation_state()
        state_key = f"{endpoint}_index"
        current_index = state.get(state_key, 0)
        
        # Sélectionner la clé API actuelle
        selected_key = api_keys[current_index % len(api_keys)]
        
        logger.debug(f"Clé API actuelle [{endpoint}]: {current_index + 1}/{len(api_keys)}")
        
        return selected_key


def rotate_to_next_api_key(endpoint: str = "default"):
    """
    Passe à la clé API suivante en rotation (round-robin)
    
    Args:
        endpoint: Nom de l'endpoint pour gérer des rotations séparées (optionnel)
    """
    with _rotation_lock:
        api_keys = get_api_keys()
        if not api_keys:
            return
        
        state = load_rotation_state()
        state_key = f"{endpoint}_index"
        current_index = state.get(state_key, 0)
        
        # Passer à la suivante
        next_index = (current_index + 1) % len(api_keys)
        state[state_key] = next_index
        save_rotation_state(state)
        
        logger.debug(f"Rotation API [{endpoint}]: Passage à la clé {next_index + 1}/{len(api_keys)}")


def get_next_api_key(endpoint: str = "default") -> Dict[str, str]:
    """
    Récupère la clé API actuelle et passe à la suivante (pour compatibilité)
    
    Args:
        endpoint: Nom de l'endpoint pour gérer des rotations séparées (optionnel)
    
    Returns:
        Dictionnaire avec 'api_key' et 'api_host'
    """
    current = get_current_api_key(endpoint)
    rotate_to_next_api_key(endpoint)
    return current


config = load_config()
# Rétrocompatibilité: garder API_KEY et API_HOST pour les autres fonctions
api_keys_list = get_api_keys()
API_KEY = api_keys_list[0].get("api_key") if api_keys_list else config.get("api_key", "")
API_HOST = api_keys_list[0].get("api_host") if api_keys_list else config.get("api_host", "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com")


def make_api_request_with_retry(url: str, headers: dict, params: dict = None, max_retries: int = 3, base_delay: float = 2.0):
    """
    Effectue une requête API avec retry automatique en cas d'erreur 429 (Rate Limit)
    
    Args:
        url: URL de l'API
        headers: Headers de la requête
        params: Paramètres de la requête (optionnel)
        max_retries: Nombre maximum de tentatives (défaut: 3)
        base_delay: Délai de base en secondes pour le backoff exponentiel (défaut: 2.0)
    
    Returns:
        Response object ou None en cas d'échec après tous les retries
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Si succès (2xx), retourner la réponse
            if response.status_code < 300:
                return response
            
            # Si erreur 429 (Rate Limit), attendre et réessayer
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    # Backoff exponentiel : 2s, 4s, 8s...
                    delay = base_delay * (2 ** attempt)
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            delay = float(retry_after)
                        except ValueError:
                            pass
                    
                    logger.warning(
                        f"Erreur 429 (Rate Limit) - Tentative {attempt + 1}/{max_retries}. "
                        f"Attente de {delay:.1f} secondes avant de réessayer..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Erreur 429 (Rate Limit) - Nombre maximum de tentatives ({max_retries}) atteint. "
                        f"Limite de taux de l'API RapidAPI dépassée. "
                        f"Veuillez attendre quelques minutes ou mettre à jour votre plan RapidAPI."
                    )
                    response.raise_for_status()
            
            # Pour les autres erreurs, lever l'exception directement
            response.raise_for_status()
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Timeout - Tentative {attempt + 1}/{max_retries}. Attente de {delay:.1f} secondes...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Timeout - Nombre maximum de tentatives ({max_retries}) atteint.")
                raise
        
        except requests.exceptions.RequestException as e:
            # Pour les autres erreurs de requête, retourner None après la dernière tentative
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Erreur de requête: {e} - Tentative {attempt + 1}/{max_retries}. Attente de {delay:.1f} secondes...")
            time.sleep(delay)
    
    return None


def get_company_posts(company_name: str, limit: int = 1) -> Optional[Dict[Any, Any]]:
    """
    Récupère les posts d'une entreprise via l'API LinkedIn RapidAPI
    
    Args:
        company_name: Nom de l'entreprise (ex: "growthroom")
        limit: Nombre de posts à récupérer (par défaut: 1)
    
    Returns:
        Dict contenant les données des posts ou None en cas d'erreur
    """
    if not company_name:
        logger.error("Nom d'entreprise vide")
        return None
    
    url = f"{API_BASE_URL}/company/posts"
    
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }
    
    params = {
        'company_name': company_name.lower(),
        'limit': limit
    }
    
    try:
        logger.info(f"Récupération de {limit} post(s) pour: {company_name}")
        response = make_api_request_with_retry(url, headers, params)
        if response is None:
            logger.error(f"Échec de la requête API après tous les retries pour: {company_name}")
            return None
        
        data = response.json()
        
        if isinstance(data, dict) and data.get('success') and 'data' in data:
            posts = data.get('data', {}).get('posts', [])
            if posts:
                logger.info(f"{len(posts)} post(s) trouvé(s) pour {company_name}")
                return data
            else:
                logger.warning(f"Aucun post trouvé pour {company_name}")
                return None
        else:
            logger.error(f"Réponse API invalide pour {company_name}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour {company_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour {company_name}: {e}", exc_info=True)
        return None


def extract_username_from_url(profile_url: str) -> Optional[str]:
    """
    Extrait le nom d'utilisateur d'une URL LinkedIn
    
    Args:
        profile_url: URL du profil LinkedIn (ex: "https://www.linkedin.com/in/john-doe/")
    
    Returns:
        Nom d'utilisateur (ex: "john-doe") ou None si l'URL est invalide
    """
    if not profile_url:
        return None
    
    # Nettoyer l'URL
    profile_url = profile_url.strip().rstrip('/')
    
    # Si c'est déjà un username (pas une URL)
    if '/' not in profile_url and not profile_url.startswith('http'):
        return profile_url
    
    # Extraire depuis l'URL
    if '/in/' in profile_url:
        username = profile_url.split('/in/')[-1].split('/')[0].split('?')[0]
        return username if username else None
    
    return None


def get_real_profile_slug_via_redirect(profile_url_or_urn: str) -> Optional[str]:
    """
    Tente de récupérer le vrai slug en suivant les redirections HTTP et en scrappant les meta tags
    ⚠️ Méthode alternative gratuite mais peut ne pas fonctionner pour tous les profils
    ⚠️ Peut violer les ToS de LinkedIn si utilisé de manière abusive
    
    Args:
        profile_url_or_urn: URL du profil avec ID (ex: linkedin.com/in/ACoAAA...)
    
    Returns:
        URL complète avec le vrai slug ou None si impossible à résoudre
    """
    if not profile_url_or_urn:
        return None
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # S'assurer que c'est une URL complète
        if not profile_url_or_urn.startswith('http'):
            if '/in/' in profile_url_or_urn:
                profile_url_or_urn = f"https://www.{profile_url_or_urn.lstrip('/')}"
            else:
                profile_url_or_urn = f"https://www.linkedin.com/in/{profile_url_or_urn}"
        
        # Headers pour simuler un navigateur
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # Suivre les redirections (allow_redirects=True par défaut)
        response = requests.get(profile_url_or_urn, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            # Méthode 1: Vérifier l'URL finale après redirection
            final_url = response.url
            if '/in/' in final_url:
                final_slug = final_url.split('/in/')[-1].split('/')[0].split('?')[0]
                # Si ce n'est plus un ID (ACo), c'est probablement le vrai slug
                if not final_slug.startswith('ACo') and len(final_slug) > 3:
                    return final_url.split('?')[0].rstrip('/')
            
            # Méthode 2: Scraper les meta tags (og:url, canonical)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Chercher dans og:url
            og_url = soup.find('meta', property='og:url')
            if og_url and og_url.get('content'):
                og_content = og_url.get('content')
                if '/in/' in og_content:
                    slug = og_content.split('/in/')[-1].split('/')[0].split('?')[0]
                    if not slug.startswith('ACo') and len(slug) > 3:
                        return og_content.split('?')[0].rstrip('/')
            
            # Chercher dans canonical
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                canonical_href = canonical.get('href')
                if '/in/' in canonical_href:
                    slug = canonical_href.split('/in/')[-1].split('/')[0].split('?')[0]
                    if not slug.startswith('ACo') and len(slug) > 3:
                        return canonical_href.split('?')[0].rstrip('/')
        
        logger.warning(f"Impossible de résoudre le slug via redirection pour: {profile_url_or_urn}")
        return None
        
    except ImportError:
        logger.error("BeautifulSoup4 ou requests non installés. Installez avec: pip install beautifulsoup4 requests")
        return None
    except Exception as e:
        logger.debug(f"Erreur lors de la résolution via redirection pour {profile_url_or_urn}: {e}")
        return None


def get_real_profile_slug(profile_url_or_urn: str, use_api: bool = False, try_redirect: bool = True) -> Optional[str]:
    """
    Récupère le vrai slug (username) d'un profil LinkedIn à partir d'une URL avec ID/URN
    
    Méthodes disponibles (par ordre de priorité):
    1. try_redirect=True (gratuit): Suit les redirections HTTP et scrappe les meta tags
    2. use_api=True (coûteux): Utilise l'API RapidAPI pour obtenir le slug
    
    Args:
        profile_url_or_urn: URL du profil (peut être avec ID/URN comme linkedin.com/in/ACoAAA...)
        use_api: Si True, appelle l'API pour obtenir le vrai slug (coûteux)
        try_redirect: Si True, essaie d'abord la méthode gratuite via redirections (défaut: True)
    
    Returns:
        URL complète avec le vrai slug (ex: "https://www.linkedin.com/in/john-doe") ou None
    """
    if not profile_url_or_urn:
        return None
    
    try:
        # Extraire l'identifiant actuel (ID/URN ou username)
        current_id = extract_username_from_url(profile_url_or_urn)
        if not current_id:
            # Si c'est déjà une URL valide avec un slug (pas un ID), la retourner telle quelle
            if '/in/' in profile_url_or_urn and not profile_url_or_urn.split('/in/')[-1].startswith('ACo'):
                return profile_url_or_urn.strip().rstrip('/')
            return None
        
        # Si c'est déjà un slug (pas un ID commençant par ACo), retourner l'URL telle quelle
        if not current_id.startswith('ACo') and not current_id.startswith('urn:'):
            return profile_url_or_urn.strip().rstrip('/')
        
        # Essayer d'abord la méthode gratuite via redirections si activée
        if try_redirect:
            logger.info(f"Tentative de résolution gratuite du slug pour: {current_id[:20]}...")
            real_url = get_real_profile_slug_via_redirect(profile_url_or_urn)
            if real_url:
                logger.info(f"✓ Slug résolu via redirection: {real_url}")
                return real_url
            else:
                logger.info(f"✗ Résolution via redirection échouée pour: {current_id[:20]}...")
        
        # Si c'est un ID mais qu'on ne veut pas utiliser l'API, retourner None
        if not use_api:
            logger.info(f"Profile URL contient un ID ({current_id[:20]}...). Utilisez use_api=True pour obtenir le vrai slug (coûteux).")
            return None
        
        # Utiliser l'API pour obtenir le vrai slug (COÛTEUX - seulement si vraiment nécessaire)
        url = f"{API_BASE_URL}/profile/detail"
        headers = {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST
        }
        
        # L'API peut accepter soit un username, soit une URL complète
        params = {"username": current_id}
        
        logger.warning(f"⚠️ Appel API coûteux pour récupérer le vrai slug: {current_id}")
        response = make_api_request_with_retry(url, headers, params)
        
        if response and response.status_code == 200:
            data = response.json()
            profile_data = data.get('data', {})
            
            # Le vrai slug peut être dans plusieurs champs
            real_slug = (
                profile_data.get('profile_url') or
                profile_data.get('username') or
                profile_data.get('public_identifier')
            )
            
            if real_slug:
                # Construire l'URL complète avec le vrai slug
                if real_slug.startswith('http'):
                    return real_slug.strip().rstrip('/')
                else:
                    return f"https://www.linkedin.com/in/{real_slug}".strip().rstrip('/')
        
        logger.warning(f"Impossible de récupérer le vrai slug pour: {current_id}")
        return None
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du slug pour {profile_url_or_urn}: {e}")
        return None


def get_profile_detail(username: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les détails complets d'un profil LinkedIn via l'API avec rotation des clés API
    
    Args:
        username: Username du profil LinkedIn (ex: "john-doe" ou "linkedin.com/in/john-doe")
    
    Returns:
        Dict contenant les détails du profil ou None en cas d'erreur
    """
    if not username:
        return None
    
    # Extraire le username si c'est une URL
    username = extract_username_from_url(username) if '/' in username else username
    
    url = f"{API_BASE_URL}/profile/detail"
    params = {
        'username': username
    }
    
    # Récupérer toutes les clés API disponibles
    api_keys_list = get_api_keys()
    
    if not api_keys_list:
        logger.error("Aucune clé API configurée")
        return None
    
    # Obtenir la clé API actuelle en rotation (sans faire la rotation maintenant)
    current_api = get_current_api_key("profile_detail")
    api_key = current_api.get("api_key")
    api_host = current_api.get("api_host", API_HOST)
    
    headers = {
        'x-rapidapi-host': api_host,
        'x-rapidapi-key': api_key
    }
    
    # Essayer d'abord avec la clé actuelle
    try:
        logger.debug(f"Récupération des détails du profil: {username}")
        response = make_api_request_with_retry(url, headers, params, max_retries=2)
        
        if response and response.status_code == 200:
            data = response.json()
            profile_data = data.get('data', {})
            logger.debug(f"✓ Détails du profil récupérés pour: {username}")
            # Rotation vers la clé suivante en cas de succès
            rotate_to_next_api_key("profile_detail")
            return profile_data
        elif response and response.status_code == 429:
            # Rate limit: essayer les autres clés
            logger.warning(f"Rate limit (429) détecté, essai avec les autres clés API...")
        else:
            logger.warning(f"Erreur {response.status_code if response else 'None'}, essai avec les autres clés API...")
    except Exception as e:
        logger.warning(f"Exception avec la clé API actuelle: {e}")
    
    # Si la clé actuelle a échoué, essayer toutes les autres clés en rotation
    last_error = None
    for attempt, api_config in enumerate(api_keys_list):
        # Skip la clé déjà essayée
        if api_config.get("api_key") == api_key:
            continue
            
        api_key_alt = api_config.get("api_key")
        api_host_alt = api_config.get("api_host", API_HOST)
        
        headers_alt = {
            'x-rapidapi-host': api_host_alt,
            'x-rapidapi-key': api_key_alt
        }
        
        try:
            logger.debug(f"Essai avec clé API alternative {attempt + 1}")
            response = make_api_request_with_retry(url, headers_alt, params, max_retries=1)
            
            if response and response.status_code == 200:
                data = response.json()
                profile_data = data.get('data', {})
                logger.debug(f"✓ Détails du profil récupérés pour: {username} (avec clé alternative)")
                return profile_data
            elif response and response.status_code == 429:
                last_error = f"Rate limit (429)"
                continue
            else:
                last_error = f"Erreur {response.status_code if response else 'None'}"
                continue
                
        except Exception as e:
            last_error = str(e)
            continue
    
    # Toutes les clés ont échoué
    logger.error(f"Impossible de récupérer les détails du profil {username} avec toutes les clés API. Dernière erreur: {last_error}")
    return None


def get_company_detail(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les détails complets d'une entreprise LinkedIn via l'API
    
    Args:
        identifier: Identifiant de l'entreprise (nom, URL LinkedIn, ou URN)
    
    Returns:
        Dict contenant les détails de l'entreprise ou None en cas d'erreur
    """
    if not identifier:
        return None
    
    url = f"{API_BASE_URL}/companies/detail"
    
    # Récupérer toutes les clés API disponibles
    api_keys_list = get_api_keys()
    
    if not api_keys_list:
        logger.error("Aucune clé API configurée")
        return None
    
    # Obtenir la clé API actuelle en rotation (sans faire la rotation maintenant)
    current_api = get_current_api_key("company_detail")
    api_key = current_api.get("api_key")
    api_host = current_api.get("api_host", API_HOST)
    
    headers = {
        'x-rapidapi-host': api_host,
        'x-rapidapi-key': api_key
    }
    
    params = {
        'identifier': identifier
    }
    
    # Essayer d'abord avec la clé actuelle
    try:
        logger.debug(f"Récupération des détails de l'entreprise: {identifier}")
        response = make_api_request_with_retry(url, headers, params, max_retries=2)
        
        if response and response.status_code == 200:
            data = response.json()
            company_data = data.get('data', {})
            logger.debug(f"✓ Détails de l'entreprise récupérés pour: {identifier}")
            # Rotation vers la clé suivante en cas de succès
            rotate_to_next_api_key("company_detail")
            return company_data
        elif response and response.status_code == 429:
            logger.warning(f"Rate limit (429) détecté, essai avec les autres clés API...")
        else:
            logger.warning(f"Erreur {response.status_code if response else 'None'}, essai avec les autres clés API...")
    except Exception as e:
        logger.warning(f"Exception avec la clé API actuelle: {e}")
    
    # Si la clé actuelle a échoué, essayer toutes les autres clés en rotation
    last_error = None
    for attempt, api_config in enumerate(api_keys_list):
        # Skip la clé déjà essayée
        if api_config.get("api_key") == api_key:
            continue
            
        api_key_alt = api_config.get("api_key")
        api_host_alt = api_config.get("api_host", API_HOST)
        
        headers_alt = {
            'x-rapidapi-host': api_host_alt,
            'x-rapidapi-key': api_key_alt
        }
        
        try:
            logger.debug(f"Essai avec clé API alternative {attempt + 1}")
            response = make_api_request_with_retry(url, headers_alt, params, max_retries=1)
            
            if response and response.status_code == 200:
                data = response.json()
                company_data = data.get('data', {})
                logger.debug(f"✓ Détails de l'entreprise récupérés pour: {identifier} (avec clé alternative)")
                return company_data
            elif response and response.status_code == 429:
                last_error = f"Rate limit (429)"
                continue
            else:
                last_error = f"Erreur {response.status_code if response else 'None'}"
                continue
                
        except Exception as e:
            last_error = str(e)
            continue
    
    # Toutes les clés ont échoué
    logger.error(f"Impossible de récupérer les détails de l'entreprise {identifier} avec toutes les clés API. Dernière erreur: {last_error}")
    return None


def get_person_posts(profile_url: str, limit: int = 1) -> Optional[Dict[Any, Any]]:
    """
    Récupère les posts d'une personne via l'API LinkedIn RapidAPI
    
    Args:
        profile_url: URL du profil LinkedIn (ex: "https://www.linkedin.com/in/john-doe/") ou username (ex: "john-doe")
        limit: Nombre de posts à récupérer (par défaut: 1)
    
    Returns:
        Dict contenant les données des posts ou None en cas d'erreur
    """
    if not profile_url:
        logger.error("URL du profil vide")
        return None
    
    # Extraire le username de l'URL
    username = extract_username_from_url(profile_url)
    if not username:
        logger.error(f"Impossible d'extraire le username de: {profile_url}")
        return None
    
    # L'endpoint correct est /profile/posts avec le paramètre username
    url = f"{API_BASE_URL}/profile/posts"
    
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }
    
    params = {
        'username': username,
        'page_number': 1  # L'API utilise page_number au lieu de limit
    }
    
    try:
        logger.info(f"Récupération de {limit} post(s) pour: {username} (depuis {profile_url})")
        response = make_api_request_with_retry(url, headers, params)
        if response is None:
            logger.error(f"Échec de la requête API après tous les retries pour: {username}")
            return None
        
        data = response.json()
        
        # L'API peut retourner différentes structures de réponse
        posts = []
        if isinstance(data, dict):
            # Structure 1: {success: true, data: {posts: [...]}}
            if data.get('success') and 'data' in data:
                posts = data.get('data', {}).get('posts', [])
            # Structure 2: {posts: [...]}
            elif 'posts' in data:
                posts = data.get('posts', [])
            # Structure 3: {data: [...]}
            elif 'data' in data and isinstance(data['data'], list):
                posts = data['data']
        
        if posts:
            # Limiter le nombre de posts si nécessaire
            if limit and len(posts) > limit:
                posts = posts[:limit]
                # Mettre à jour la structure de réponse
                if isinstance(data, dict) and 'data' in data:
                    if isinstance(data['data'], dict):
                        data['data']['posts'] = posts
                    elif isinstance(data['data'], list):
                        data['data'] = posts
            
            logger.info(f"{len(posts)} post(s) trouvé(s) pour {username}")
            return data
        else:
            logger.warning(f"Aucun post trouvé pour {username}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour {username}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour {username}: {e}", exc_info=True)
        return None


def search_posts_by_keyword(keyword: str, limit: int = 10) -> Optional[Dict[Any, Any]]:
    """
    Recherche les posts contenant un mot-clé via l'API LinkedIn RapidAPI
    
    Args:
        keyword: Mot-clé à rechercher
        limit: Nombre de posts à récupérer (par défaut: 10)
    
    Returns:
        Dict contenant les données des posts ou None en cas d'erreur
    """
    if not keyword:
        logger.error("Mot-clé vide")
        return None
    
    # L'endpoint correct est /posts/search (pas /search/posts)
    url = f"{API_BASE_URL}/posts/search"
    
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }
    
    # L'API utilise page_number, pas limit directement
    # On va récupérer page par page jusqu'à avoir le nombre souhaité
    params = {
        'keyword': keyword,
        'page_number': 1,
        'sort_type': 'date_posted'  # ou 'relevance'
    }
    
    try:
        logger.info(f"Recherche de {limit} post(s) avec le mot-clé: {keyword}")
        all_posts = []
        page_number = 1
        max_pages = 10  # Limite de sécurité
        
        while len(all_posts) < limit and page_number <= max_pages:
            params['page_number'] = page_number
            response = make_api_request_with_retry(url, headers, params)
            if response is None:
                logger.error(f"Échec de la requête API après tous les retries pour le mot-clé: {keyword}")
                break
            
            data = response.json()
            
            # Extraire les posts selon différentes structures possibles
            posts = []
            if isinstance(data, dict):
                # Structure 1: {success: true, data: {posts: [...]}}
                if data.get('success') and 'data' in data:
                    posts = data.get('data', {}).get('posts', [])
                # Structure 2: {posts: [...]}
                elif 'posts' in data and isinstance(data['posts'], list):
                    posts = data['posts']
                # Structure 3: {data: [...]}
                elif 'data' in data and isinstance(data['data'], list):
                    posts = data['data']
            
            if not posts:
                # Plus de posts disponibles
                break
            
            all_posts.extend(posts)
            
            # Si on a assez de posts ou si c'était la dernière page
            if len(all_posts) >= limit:
                all_posts = all_posts[:limit]
                break
            
            page_number += 1
        
        if all_posts:
            # Reconstruire la structure de réponse attendue
            result = {
                'success': True,
                'data': {
                    'posts': all_posts
                }
            }
            logger.info(f"{len(all_posts)} post(s) trouvé(s) pour '{keyword}'")
            return result
        else:
            logger.warning(f"Aucun post trouvé pour '{keyword}'")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour '{keyword}': {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour '{keyword}': {e}", exc_info=True)
        return None


def get_post_reactions(post_url: str, page_number: int = 1, reaction_type: str = "ALL") -> Optional[Dict[Any, Any]]:
    """
    Récupère les réactions détaillées d'un post via l'API LinkedIn RapidAPI
    
    Args:
        post_url: URL complète du post LinkedIn
        page_number: Numéro de page pour la pagination (par défaut: 1)
        reaction_type: Type de réaction à récupérer (par défaut: "ALL")
    
    Returns:
        Dict contenant les réactions ou None en cas d'erreur
    """
    if not post_url:
        logger.error("URL du post vide")
        return None
    
    url = f"{API_BASE_URL}/post/reactions"
    
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }
    
    params = {
        'post_url': post_url,
        'page_number': page_number,
        'reaction_type': reaction_type
    }
    
    try:
        logger.info(f"Récupération des réactions pour le post: {post_url[:80]}...")
        response = make_api_request_with_retry(url, headers, params)
        if response is None:
            logger.error(f"Échec de la requête API après tous les retries pour le post")
            return None
        
        data = response.json()
        
        if isinstance(data, dict) and data.get('success') and 'data' in data:
            reactions = data.get('data', {}).get('reactions', [])
            total_reactions = data.get('data', {}).get('total_reactions', 0)
            logger.info(f"{total_reactions} réaction(s) totale(s), {len(reactions)} sur cette page")
            return data
        else:
            logger.error(f"Réponse API invalide pour le post")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour le post: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour le post: {e}", exc_info=True)
        return None


def extract_post_url_from_posts_data(posts_data: Dict[Any, Any], index: int = 0) -> Optional[str]:
    """
    Extrait l'URL d'un post depuis les données
    
    Args:
        posts_data: Données des posts depuis l'API
        index: Index du post à extraire (0 = plus récent)
    
    Returns:
        URL du post ou None
    """
    try:
        posts = []
        
        # Structure 1: {success: true, data: {posts: [...]}}
        if posts_data.get('success') and 'data' in posts_data:
            posts = posts_data.get('data', {}).get('posts', [])
        # Structure 2: {posts: [...]}
        elif 'posts' in posts_data and isinstance(posts_data['posts'], list):
            posts = posts_data['posts']
        # Structure 3: {data: [...]} (liste directe)
        elif 'data' in posts_data and isinstance(posts_data['data'], list):
            posts = posts_data['data']
        
        if posts and len(posts) > index:
            post = posts[index]
            post_url = (
                post.get('post_url') or
                post.get('url') or
                post.get('linkedin_url') or
                post.get('share_url') or
                post.get('permalink')
            )
            if post_url:
                return post_url
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction de l'URL du post: {e}")
        return None


def extract_post_date_from_posts_data(posts_data: Dict[Any, Any], index: int = 0) -> str:
    """
    Extrait la date d'un post depuis les données
    
    Args:
        posts_data: Données des posts depuis l'API
        index: Index du post à extraire (0 = plus récent)
    
    Returns:
        Date du post (format ISO) ou date actuelle
    """
    try:
        posts = []
        
        # Structure 1: {success: true, data: {posts: [...]}}
        if posts_data.get('success') and 'data' in posts_data:
            posts = posts_data.get('data', {}).get('posts', [])
        # Structure 2: {posts: [...]}
        elif 'posts' in posts_data and isinstance(posts_data['posts'], list):
            posts = posts_data['posts']
        # Structure 3: {data: [...]} (liste directe)
        elif 'data' in posts_data and isinstance(posts_data['data'], list):
            posts = posts_data['data']
        
        if posts and len(posts) > index:
            post = posts[index]
            post_date = (
                post.get('created_at') or
                post.get('date') or
                post.get('published_at') or
                post.get('timestamp') or
                post.get('time')
            )
            if post_date:
                return str(post_date)
    except Exception as e:
        logger.warning(f"Erreur lors de l'extraction de la date du post: {e}")
    
    return datetime.now().isoformat()


def process_competitor_last_post_radar(company_name: str, client_id: int = None, max_extractions: int = None) -> List[Dict[str, Any]]:
    """
    NOTE: max_extractions n'est plus utilisé ici - la limite est appliquée après le scoring IA
    sur les profils qualifiés uniquement. Ce paramètre est conservé pour compatibilité mais ignoré.
    """
    """
    Traite un radar de type 'competitor_last_post'
    Récupère le dernier post du concurrent et extrait les réactions
    
    Args:
        company_name: Nom de l'entreprise concurrente
        client_id: ID du client (pour déduplication)
        max_extractions: Nombre maximum de prospects à extraire (None = illimité)
    
    Returns:
        Liste de dictionnaires contenant les réactions
    """
    reactions_list = []
    
    # Récupérer les prospects existants pour déduplication
    # NOTE: La déduplication se fera dans process_radar_with_scoring à l'étape 2, après l'extraction.
    # Ici, on collecte toutes les réactions pour permettre à l'IA de les analyser.
    
    logger.info(f"Récupération du dernier post pour: {company_name}")
    # 1. Récupérer le dernier post
    posts_data = get_company_posts(company_name, limit=1)
    if not posts_data:
        logger.warning(f"Aucun post trouvé pour {company_name}")
        return reactions_list
    
    logger.info(f"✓ Post trouvé pour {company_name}")
    
    # 2. Extraire l'URL du post
    post_url = extract_post_url_from_posts_data(posts_data, index=0)
    if not post_url:
        logger.warning(f"Impossible d'extraire l'URL du post pour {company_name}")
        return reactions_list
    
    # 3. Récupérer les réactions (avec pagination)
    post_date = extract_post_date_from_posts_data(posts_data, index=0)
    page_number = 1
    total_reactions = 0
    
    logger.info(f"Récupération des réactions du post (pagination)...")
    # NOTE: On collecte toutes les réactions pour laisser l'IA analyser tous les profils
    # La limite sera appliquée après le scoring sur les profils qualifiés uniquement
    
    while True:
        reactions_data = get_post_reactions(post_url, page_number=page_number, reaction_type="ALL")
        if not reactions_data:
            break
        
        # Obtenir le total la première fois
        if page_number == 1:
            total_reactions = reactions_data.get('data', {}).get('total_reactions', 0)
            logger.info(f"  Total de {total_reactions} réaction(s) trouvée(s)")
        
        reactions = reactions_data.get('data', {}).get('reactions', [])
        if not reactions:
            break
        
        logger.info(f"  Page {page_number}: {len(reactions)} réaction(s)")
        
        # Extraire les réactions (toutes pour laisser l'IA analyser tous les profils)
        # NOTE: La déduplication avec la DB se fera dans process_radar_with_scoring à l'étape 2
        for reaction in reactions:
            reactor = reaction.get('reactor', {})
            reactor_urn = str(reactor.get('urn', ''))
            
            # Utiliser directement le profile_url de l'API (peut être un ID ou un slug)
            profile_url = reactor.get('profile_url', '')
            
            reactions_list.append({
                'company_name': company_name,
                'post_url': post_url,
                'post_date': post_date,
                'reactor_name': reactor.get('name', ''),
                'reactor_urn': reactor_urn,
                'profile_url': profile_url,
                'reaction_type': reaction.get('reaction_type', ''),
                'headline': reactor.get('headline', ''),
                'profile_picture_url': (
                    reactor.get('profile_pictures', {}).get('medium') or
                    reactor.get('profile_pictures', {}).get('large') or ''
                )
            })
        
        # Vérifier s'il y a d'autres pages
        if len(reactions_list) >= total_reactions or page_number >= 50:
            break
        
        page_number += 1
    
    logger.info(f"✓ {len(reactions_list)} réaction(s) extraite(s) pour {company_name}")
    return reactions_list


def process_person_last_post_radar(profile_url: str, client_id: int = None, max_extractions: int = None) -> List[Dict[str, Any]]:
    """
    Traite un radar de type 'person_last_post'
    Récupère le dernier post d'une personne et extrait les réactions
    
    Args:
        profile_url: URL du profil LinkedIn
    
    Returns:
        Liste de dictionnaires contenant les réactions
    """
    reactions_list = []
    
    # Récupérer les prospects existants pour déduplication
    # NOTE: La déduplication se fera dans process_radar_with_scoring à l'étape 2, après l'extraction.
    # Ici, on collecte toutes les réactions pour permettre à l'IA de les analyser.
    
    # 1. Récupérer le dernier post
    posts_data = get_person_posts(profile_url, limit=1)
    if not posts_data:
        logger.warning(f"Aucun post trouvé pour {profile_url}")
        return reactions_list
    
    # 2. Extraire l'URL du post
    post_url = extract_post_url_from_posts_data(posts_data, index=0)
    if not post_url:
        logger.warning(f"Impossible d'extraire l'URL du post pour {profile_url}")
        return reactions_list
    
    # 3. Récupérer les réactions (avec pagination)
    post_date = extract_post_date_from_posts_data(posts_data, index=0)
    page_number = 1
    total_reactions = 0
    
    if max_extractions:
        logger.info(f"Limite d'extraction: {max_extractions} prospect(s)")
    
    while True:
        # Arrêter si on a atteint la limite
        if max_extractions and len(reactions_list) >= max_extractions:
            logger.info(f"Limite d'extraction atteinte: {max_extractions} prospect(s)")
            break
        
        reactions_data = get_post_reactions(post_url, page_number=page_number, reaction_type="ALL")
        if not reactions_data:
            break
        
        # Obtenir le total la première fois
        if page_number == 1:
            total_reactions = reactions_data.get('data', {}).get('total_reactions', 0)
            logger.info(f"  Total de {total_reactions} réaction(s) trouvée(s)")
        
        reactions = reactions_data.get('data', {}).get('reactions', [])
        if not reactions:
            break
        
        logger.info(f"  Page {page_number}: {len(reactions)} réaction(s)")
        
        # Extraire les réactions (toutes pour laisser l'IA analyser tous les profils)
        # NOTE: La déduplication avec la DB se fera dans process_radar_with_scoring à l'étape 2
        for reaction in reactions:
            reactor = reaction.get('reactor', {})
            reactor_urn = str(reactor.get('urn', ''))
            
            # Utiliser directement le profile_url de l'API (peut être un ID ou un slug)
            profile_url_reactor = reactor.get('profile_url', '')
            
            reactions_list.append({
                'person_profile_url': profile_url,
                'post_url': post_url,
                'post_date': post_date,
                'reactor_name': reactor.get('name', ''),
                'reactor_urn': reactor_urn,
                'profile_url': profile_url_reactor,
                'reaction_type': reaction.get('reaction_type', ''),
                'headline': reactor.get('headline', ''),
                'profile_picture_url': (
                    reactor.get('profile_pictures', {}).get('medium') or
                    reactor.get('profile_pictures', {}).get('large') or ''
                )
            })
        
        # Vérifier s'il y a d'autres pages
        total_reactions = reactions_data.get('data', {}).get('total_reactions', 0)
        if len(reactions_list) >= total_reactions or page_number >= 50:
            break
        
        page_number += 1
    
    logger.info(f"✓ {len(reactions_list)} réaction(s) extraite(s) pour {profile_url}")
    return reactions_list


def process_keyword_posts_radar(keyword: str, post_count: int = 10, client_id: int = None, max_extractions: int = None) -> List[Dict[str, Any]]:
    """
    Traite un radar de type 'keyword_posts'
    Recherche X derniers posts sur une thématique et extrait les réactions
    
    Args:
        keyword: Mot-clé à rechercher
        post_count: Nombre de posts à analyser
    
    Returns:
        Liste de dictionnaires contenant les réactions
    """
    reactions_list = []
    
    # Récupérer les prospects existants pour déduplication
    # NOTE: max_extractions n'est plus utilisé ici - la limite est appliquée après le scoring IA
    # sur les profils qualifiés uniquement. On collecte toutes les réactions pour l'analyse IA.
    # La déduplication se fera dans process_radar_with_scoring à l'étape 2, après l'extraction.
    
    # 1. Rechercher les posts par mot-clé
    posts_data = search_posts_by_keyword(keyword, limit=post_count)
    if not posts_data:
        logger.warning(f"Aucun post trouvé pour '{keyword}'")
        return reactions_list
    
    # 2. Traiter chaque post (tous pour laisser l'IA analyser)
    posts = posts_data.get('data', {}).get('posts', [])
    for post in posts:
        post_url = (
            post.get('post_url') or
            post.get('url') or
            post.get('linkedin_url') or
            post.get('share_url')
        )
        
        if not post_url:
            continue
        
        post_date = (
            post.get('created_at') or
            post.get('date') or
            post.get('published_at') or
            datetime.now().isoformat()
        )
        
        # 3. Récupérer les réactions de ce post (seulement la première page pour éviter trop de requêtes)
        reactions_data = get_post_reactions(post_url, page_number=1, reaction_type="ALL")
        if not reactions_data:
            continue
        
        reactions = reactions_data.get('data', {}).get('reactions', [])
        
        # Extraire les réactions (toutes pour laisser l'IA analyser tous les profils)
        # NOTE: La déduplication avec la DB se fera dans process_radar_with_scoring à l'étape 2
        for reaction in reactions:
            reactor = reaction.get('reactor', {})
            reactor_urn = str(reactor.get('urn', ''))
            
            # Utiliser directement le profile_url de l'API (peut être un ID ou un slug)
            profile_url_reactor = reactor.get('profile_url', '')
            
            reactions_list.append({
                'keyword': keyword,
                'post_url': post_url,
                'post_date': str(post_date),
                'reactor_name': reactor.get('name', ''),
                'reactor_urn': reactor_urn,
                'profile_url': profile_url_reactor,
                'reaction_type': reaction.get('reaction_type', ''),
                'headline': reactor.get('headline', ''),
                'profile_picture_url': (
                    reactor.get('profile_pictures', {}).get('medium') or
                    reactor.get('profile_pictures', {}).get('large') or ''
                )
            })
    
    logger.info(f"✓ {len(reactions_list)} réaction(s) extraite(s) pour '{keyword}'")
    return reactions_list


def process_radar(radar: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Traite un radar selon son type (version simple sans scoring)
    
    Args:
        radar: Dictionnaire contenant les informations du radar
    
    Returns:
        Liste de dictionnaires contenant les réactions
    """
    radar_type = radar.get('radar_type')
    target_identifier = radar.get('target_identifier')
    target_value = radar.get('target_value')
    keyword = radar.get('keyword')
    post_count = radar.get('post_count', 1)
    client_id = radar.get('client_id')
    max_extractions = radar.get('max_extractions')
    
    if radar_type == 'competitor_last_post':
        return process_competitor_last_post_radar(target_identifier, client_id=client_id, max_extractions=max_extractions)
    elif radar_type == 'person_last_post':
        profile_url = target_value or target_identifier
        return process_person_last_post_radar(profile_url, client_id=client_id, max_extractions=max_extractions)
    elif radar_type == 'keyword_posts':
        return process_keyword_posts_radar(keyword or target_identifier, post_count, client_id=client_id, max_extractions=max_extractions)
    else:
        logger.error(f"Type de radar inconnu: {radar_type}")
        return []


def process_multiple_competitors(competitor_names: List[str]) -> List[Dict[str, Any]]:
    """
    Traite plusieurs concurrents en une fois
    
    Args:
        competitor_names: Liste des noms de concurrents
    
    Returns:
        Liste consolidée de toutes les réactions
    """
    all_reactions = []
    
    for company_name in competitor_names:
        logger.info(f"Traitement du concurrent: {company_name}")
        reactions = process_competitor_last_post_radar(company_name)
        all_reactions.extend(reactions)
    
    logger.info(f"Total: {len(all_reactions)} réaction(s) pour {len(competitor_names)} concurrent(s)")
    return all_reactions


def process_multiple_persons(profile_urls: List[str]) -> List[Dict[str, Any]]:
    """
    Traite plusieurs profils personnes en une fois
    
    Args:
        profile_urls: Liste des URLs de profils LinkedIn
    
    Returns:
        Liste consolidée de toutes les réactions
    """
    all_reactions = []
    
    for profile_url in profile_urls:
        logger.info(f"Traitement du profil: {profile_url}")
        reactions = process_person_last_post_radar(profile_url)
        all_reactions.extend(reactions)
    
    logger.info(f"Total: {len(all_reactions)} réaction(s) pour {len(profile_urls)} profil(s)")
    return all_reactions


def get_post_details(post_url: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les détails complets d'un post pour le scoring
    
    Args:
        post_url: URL du post
    
    Returns:
        Dict avec détails du post ou None
    """
    # Cette fonction pourrait être étendue pour récupérer plus d'informations
    # Pour l'instant, on retourne juste les infos de base
    return {
        'post_url': post_url,
        'post_date': datetime.now().isoformat()
    }


def process_radar_with_scoring(radar: Dict[str, Any], 
                               client_id: int,
                               company_profile: Optional[Dict[str, Any]] = None,
                               competitors_list: Optional[List[Dict[str, Any]]] = None,
                               min_score_threshold: float = 0.6,
                               filter_competitors: bool = True,
                               max_qualified_prospects: int = None) -> List[Dict[str, Any]]:
    """
    Traite un radar avec scoring IA et filtrage
    
    Args:
        radar: Dictionnaire contenant les informations du radar
        client_id: ID du client
        company_profile: Profil entreprise (optionnel)
        competitors_list: Liste des concurrents (optionnel)
        min_score_threshold: Score minimum pour qualifier
        filter_competitors: Activer le filtrage des concurrents
    
    Returns:
        Liste de réactions avec scoring appliqué
    """
    logger.info(f"Traitement du radar: {radar.get('name', 'Unknown')} (ID: {radar.get('id')})")
    
    # ÉTAPE 1: Collecte de toutes les réactions (sans limite)
    logger.info("Étape 1/7: Récupération des réactions depuis LinkedIn...")
    raw_reactions = process_radar(radar)
    
    if not raw_reactions:
        logger.warning(f"Aucune réaction trouvée pour le radar {radar.get('id')}")
        return []
    
    logger.info(f"✓ {len(raw_reactions)} réaction(s) brute(s) récupérée(s)")
    
    # Charger le profil et les concurrents si non fournis
    if not company_profile:
        from utils.database import get_client_profile_as_dict
        company_profile = get_client_profile_as_dict(client_id)
    
    if not competitors_list:
        from utils.database import get_competitors
        competitors_list = get_competitors(client_id)
    
    # ÉTAPE 2: Déduplication APRÈS l'extraction, AVANT le scoring IA pour éviter les coûts inutiles
    logger.info("Étape 2/7: Déduplication des prospects existants (après extraction)...")
    from utils.database import get_existing_prospect_urns
    existing_urns = get_existing_prospect_urns(client_id)
    logger.info(f"  → {len(existing_urns)} prospect(s) déjà présent(s) dans la base de données")
    
    new_reactions = []
    skipped_count = 0
    for reaction in raw_reactions:
        reactor_urn = str(reaction.get('reactor_urn', ''))
        if reactor_urn and reactor_urn in existing_urns:
            skipped_count += 1
            logger.debug(f"  Prospect déjà existant ignoré (skip IA): {reaction.get('reactor_name', 'Unknown')}")
            continue
        new_reactions.append(reaction)
    
    logger.info(f"✓ {skipped_count} prospect(s) déjà existant(s) ignoré(s), {len(new_reactions)} nouveau(x) prospect(s) à analyser")
    
    if not new_reactions:
        logger.info("Aucun nouveau prospect à analyser")
        return []
    
    # Filtrer les concurrents si activé (sur les nouveaux prospects uniquement)
    if filter_competitors and competitors_list:
        logger.info(f"Étape 2.5/7: Filtrage des concurrents ({len(competitors_list)} concurrent(s) à filtrer)...")
        from utils.intelligent_scoring import filter_competitors_from_reactions
        filtered_reactions, filtered_count = filter_competitors_from_reactions(
            new_reactions,
            client_id,
            competitors_list
        )
        logger.info(f"✓ {filtered_count} prospect(s) filtré(s) (concurrents), {len(filtered_reactions)} restant(s)")
        new_reactions = filtered_reactions
    elif filter_competitors:
        logger.info("Filtrage des concurrents désactivé (aucun concurrent configuré)")
    
    # ÉTAPE 3: Scoring IA uniquement sur les profils non présents
    if company_profile:
        logger.info(f"Étape 3/7: Application du scoring IA sur {len(new_reactions)} nouveau(x) prospect(s) (seuil: {min_score_threshold})...")
        from utils.intelligent_scoring import calculate_prospect_score_with_ai, calculate_prospect_score
        
        scored_reactions = []
        scored_count = 0
        ai_scoring_used = 0
        fallback_scoring_used = 0
        
        for idx, reaction in enumerate(new_reactions, 1):
            try:
                # Préparer le contexte du post si disponible
                post_context = None
                if reaction.get('post_url'):
                    # On pourrait enrichir avec les détails du post ici
                    post_context = {
                        'post_text': reaction.get('post_text', ''),
                        'post_author': reaction.get('post_author', '')
                    }
                
                # Calculer le score avec IA (avec fallback automatique si erreur)
                scoring_result = calculate_prospect_score_with_ai(
                    reaction,
                    company_profile,
                    post_context=post_context
                )
                
                # Détecter si c'était un fallback (pas de reasoning = fallback)
                if 'reasoning' in scoring_result and scoring_result.get('reasoning'):
                    ai_scoring_used += 1
                else:
                    fallback_scoring_used += 1
                
                score = scoring_result.get('total_score', 0.0)
                
                # Filtrer selon le seuil
                if score >= min_score_threshold:
                    # Ajouter les informations de scoring à la réaction
                    reaction['relevance_score'] = score
                    reaction['scoring_breakdown'] = scoring_result
                    reaction['prospect_relevant'] = True
                    scored_reactions.append(reaction)
                    scored_count += 1
                    
                    # Log tous les 20 pour ne pas surcharger
                    if scored_count % 20 == 0:
                        logger.info(f"  → {scored_count} prospect(s) qualifié(s) sur {idx} analysé(s)...")
                else:
                    logger.debug(f"Prospect filtré (score {score:.2f} < {min_score_threshold}): {reaction.get('reactor_name')}")
                    
            except Exception as e:
                logger.error(f"Erreur lors du scoring pour prospect {reaction.get('reactor_name', 'Unknown')}: {e}")
                # En cas d'erreur, utiliser le scoring classique
                try:
                    scoring_result = calculate_prospect_score(
                        reaction,
                        company_profile,
                        post_context=None
                    )
                    score = scoring_result.get('total_score', 0.0)
                    fallback_scoring_used += 1
                    
                    if score >= min_score_threshold:
                        reaction['relevance_score'] = score
                        reaction['scoring_breakdown'] = scoring_result
                        reaction['prospect_relevant'] = True
                        scored_reactions.append(reaction)
                        scored_count += 1
                except Exception as e2:
                    logger.error(f"Erreur même avec scoring classique: {e2}")
                    # Prospect ignoré en cas d'erreur double
        
        logger.info(f"✓ {len(scored_reactions)} prospect(s) qualifié(s) sur {len(new_reactions)} analysé(s)")
        if ai_scoring_used > 0:
            logger.info(f"  → Scoring IA utilisé: {ai_scoring_used} prospect(s)")
        if fallback_scoring_used > 0:
            logger.info(f"  → Scoring classique (fallback): {fallback_scoring_used} prospect(s)")
        
        # ÉTAPE 4: Filtrage des profils qualifiés (score >= seuil) - déjà fait dans la boucle
        # Les réactions dans scored_reactions ont déjà score >= min_score_threshold
        
        # ÉTAPE 5: Application de la limite sur les qualifiés (triés par score décroissant)
        if max_qualified_prospects and len(scored_reactions) > max_qualified_prospects:
            logger.info(f"Étape 5/7: Application de la limite ({max_qualified_prospects} prospect(s) qualifié(s) maximum)...")
            # Trier par score décroissant pour garder les meilleurs
            scored_reactions.sort(key=lambda x: x.get('relevance_score', 0.0), reverse=True)
            limited_reactions = scored_reactions[:max_qualified_prospects]
            logger.info(f"✓ {max_qualified_prospects} prospect(s) qualifié(s) retenu(s) sur {len(scored_reactions)} qualifié(s)")
            scored_reactions = limited_reactions
        
        # ÉTAPE 6: Enrichissement des profils qualifiés avec get_profile
        if scored_reactions:
            logger.info(f"Étape 6/7: Enrichissement des {len(scored_reactions)} prospect(s) qualifié(s) avec get_profile...")
            enriched_reactions = []
            for idx, reaction in enumerate(scored_reactions, 1):
                try:
                    reactor_urn = str(reaction.get('reactor_urn', ''))
                    profile_url = reaction.get('profile_url', '')
                    
                    # Extraire le username pour l'API
                    username = extract_username_from_url(profile_url) if profile_url else None
                    if not username and reactor_urn:
                        # Si on a un URN, on peut essayer de l'utiliser
                        username = reactor_urn.split(':')[-1] if ':' in reactor_urn else reactor_urn
                    
                    if username:
                        # Appel API get_profile pour enrichir
                        profile_detail = get_profile_detail(username)
                        if profile_detail:
                            # Enrichir la réaction avec les détails du profil
                            reaction['enriched_profile'] = profile_detail
                            logger.debug(f"  ✓ Profil enrichi: {reaction.get('reactor_name', 'Unknown')}")
                            
                            # ÉTAPE 7: Enrichissement des données d'entreprise
                            # Extraire l'URN et le nom de l'entreprise depuis basic_info (priorité à l'URN)
                            company_urn = None
                            company_name = None
                            company_identifier = None
                            
                            # Les données enrichies sont dans basic_info
                            basic_info = profile_detail.get('basic_info', {}) if isinstance(profile_detail, dict) else {}
                            
                            if basic_info and isinstance(basic_info, dict):
                                # Priorité 1: URN de l'entreprise (le plus fiable)
                                company_urn = basic_info.get('current_company_urn')
                                company_name = basic_info.get('current_company')
                            
                            # Fallback: chercher dans experience
                            if not company_urn and profile_detail.get('experience') and isinstance(profile_detail.get('experience'), list):
                                for exp in profile_detail.get('experience', []):
                                    if isinstance(exp, dict) and exp.get('is_current', False):
                                        company_urn = exp.get('company_id')  # company_id est l'URN
                                        if not company_name:
                                            company_name = exp.get('company')
                                        break
                            
                            # Fallback: nom de l'entreprise seulement
                            if not company_name:
                                if profile_detail.get('current_company'):
                                    company_name = profile_detail.get('current_company')
                                elif profile_detail.get('company'):
                                    company_name = profile_detail.get('company')
                            
                            # Utiliser aussi le detected_company depuis la réaction originale
                            if not company_name:
                                company_name = reaction.get('detected_company') or reaction.get('company_name')
                            
                            if company_urn or company_name:
                                # Utiliser l'URN comme identifiant principal si disponible, sinon le nom
                                if company_urn:
                                    company_identifier = str(company_urn)
                                else:
                                    company_identifier = company_name.lower().strip()
                                
                                # Vérifier si l'entreprise existe déjà en DB
                                company_detail = get_company_detail_from_db(company_identifier)
                                
                                if not company_detail:
                                    # Appel API pour récupérer les détails de l'entreprise
                                    # Prioriser l'URN si disponible (plus fiable que le nom)
                                    api_identifier = company_urn if company_urn else company_name
                                    logger.debug(f"  → Récupération des détails de l'entreprise: {api_identifier} (URN: {company_urn or 'N/A'}, Nom: {company_name or 'N/A'})")
                                    company_detail = get_company_detail(api_identifier)
                                    
                                    if company_detail:
                                        # Sauvegarder en DB avec l'URN comme identifiant si disponible
                                        save_company_detail(company_identifier, company_name or 'Unknown', company_detail)
                                        logger.debug(f"  ✓ Entreprise enrichie et sauvegardée: {company_name or company_urn}")
                                    else:
                                        logger.debug(f"  ✗ Impossible de récupérer les détails de l'entreprise: {api_identifier}")
                                else:
                                    logger.debug(f"  ✓ Entreprise trouvée en DB (pas d'appel API): {company_name or company_urn}")
                                
                                # Ajouter les données d'entreprise à la réaction
                                if company_detail:
                                    reaction['enriched_company'] = company_detail
                            
                            # Mettre à jour profile_url avec le vrai slug depuis basic_info
                            if basic_info and isinstance(basic_info, dict):
                                enriched_profile_url = basic_info.get('profile_url')
                                if enriched_profile_url:
                                    # Normaliser l'URL (linkedin.com -> www.linkedin.com)
                                    if enriched_profile_url.startswith('https://linkedin.com'):
                                        enriched_profile_url = enriched_profile_url.replace('https://linkedin.com', 'https://www.linkedin.com')
                                    reaction['profile_url'] = enriched_profile_url
                                    logger.debug(f"  ✓ Profile URL mis à jour avec le slug: {enriched_profile_url}")
                        else:
                            logger.debug(f"  ✗ Impossible d'enrichir: {reaction.get('reactor_name', 'Unknown')}")
                    
                    enriched_reactions.append(reaction)
                    
                    # Log tous les 10 pour ne pas surcharger
                    if idx % 10 == 0:
                        logger.info(f"  → {idx}/{len(scored_reactions)} profil(s) enrichi(s)...")
                        
                except Exception as e:
                    logger.error(f"Erreur lors de l'enrichissement du profil {reaction.get('reactor_name', 'Unknown')}: {e}")
                    # Continuer même en cas d'erreur d'enrichissement
                    enriched_reactions.append(reaction)
            
            logger.info(f"✓ {len(enriched_reactions)} prospect(s) qualifié(s) enrichi(s)")
            return enriched_reactions
        
        return scored_reactions
    else:
        logger.warning("Profil entreprise non disponible, scoring désactivé")
    
    # Si pas de profil, retourner toutes les réactions sans scoring
    return raw_reactions
