"""
Script pour récupérer quotidiennement le dernier post LinkedIn de plusieurs entreprises
et extraire les réactions dans un CSV consolidé
Liste des entreprises dans companies_to_follow.csv
"""
import requests
import json
import csv
import logging
import re
import time
import signal
import sys
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import quote

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_scraper_company.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Variables globales pour la sauvegarde en cas d'interruption
_save_on_interrupt_enabled = False
_current_progress = {
    'company': None,
    'posts_data': None,
    'post_url': None,
    'post_analysis': None,
    'reactions_rows': [],
    'prospect_analyses': {},
    'processed_reactors': set(),
    'page_number': 1
}

# Configuration
CONFIG_FILE = Path("config.json")
CSV_FILE = Path("companies_to_follow.csv")
API_BASE_URL = "https://linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"

def load_config() -> Dict[str, Any]:
    """Charge la configuration depuis le fichier config.json"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Configuration chargée depuis {CONFIG_FILE}")
                return config
        except Exception as e:
            logger.warning(f"Erreur lors du chargement de la config: {e}. Utilisation des valeurs par défaut.")
    
    # Valeurs par défaut
    return {
        "api_key": "8d94f2d4b9msh384e09aab682e2bp173e86jsn7b448f5e8961",
        "api_host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com",
        "limit": 1,
        "output_directory": "data"
    }

config = load_config()
API_KEY = config.get("api_key")
API_HOST = config.get("api_host", "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com")
OUTPUT_DIR = Path(config.get("output_directory", "data"))
OUTPUT_DIR.mkdir(exist_ok=True)

# Configuration OpenAI
OPENAI_CONFIG = config.get("openai", {})
OPENAI_ENABLED = OPENAI_AVAILABLE and OPENAI_CONFIG.get("enabled", False)
OPENAI_API_KEY = OPENAI_CONFIG.get("api_key") if OPENAI_ENABLED else None
OPENAI_MODEL = OPENAI_CONFIG.get("model", "gpt-4o-mini")
OPENAI_TEMPERATURE = OPENAI_CONFIG.get("temperature", 0.3)
OPENAI_MAX_TOKENS = OPENAI_CONFIG.get("max_tokens", 500)
RELEVANCE_THRESHOLD = OPENAI_CONFIG.get("relevance_threshold", 0.6)

# Avertissement si OpenAI non disponible
if not OPENAI_AVAILABLE:
    logger.warning("OpenAI package non disponible. Installez-le avec: pip install openai")

# Initialiser le client OpenAI si disponible (après définition des variables)
openai_client = None
if OPENAI_ENABLED and OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("Client OpenAI initialisé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du client OpenAI: {e}")
        OPENAI_ENABLED = False
elif OPENAI_ENABLED and not OPENAI_API_KEY:
    logger.warning("OpenAI activé mais clé API manquante. L'analyse IA sera désactivée.")
    OPENAI_ENABLED = False


def load_companies_from_csv(csv_file: Path = CSV_FILE) -> List[Dict[str, str]]:
    """
    Charge la liste des entreprises depuis le fichier CSV
    Utilise company_name comme identifiant principal
    
    Args:
        csv_file: Chemin vers le fichier CSV
    
    Returns:
        Liste de dictionnaires contenant les informations des entreprises
    """
    companies = []
    
    if not csv_file.exists():
        logger.error(f"Fichier CSV introuvable: {csv_file}")
        return companies
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Nettoyer les valeurs et ignorer les lignes vides
                company = {k.strip(): v.strip() if v else None for k, v in row.items()}
                # Utiliser company_name comme identifiant principal
                if company.get('company_name'):
                    companies.append(company)
        
        logger.info(f"{len(companies)} entreprise(s) chargée(s) depuis {csv_file}")
        return companies
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du CSV: {e}", exc_info=True)
        return companies


def get_company_posts(company_name: str) -> Optional[Dict[Any, Any]]:
    """
    Récupère les posts de l'entreprise via l'API LinkedIn RapidAPI
    
    Args:
        company_name: Nom de l'entreprise (ex: "growthroom")
    
    Returns:
        Dict contenant les données des posts ou None en cas d'erreur
    """
    if not company_name:
        logger.error("Nom d'entreprise vide, impossible de récupérer les posts")
        return None
    
    url = f"{API_BASE_URL}/company/posts"
    
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }
    
    params = {
        'company_name': company_name.lower()
    }
    
    try:
        logger.info(f"Récupération des posts pour: {company_name}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Params: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Réponse API reçue: {type(data).__name__}")
        
        # Vérifier la structure de réponse
        if isinstance(data, dict):
            if data.get('success') and 'data' in data:
                posts = data.get('data', {}).get('posts', [])
                if posts and len(posts) > 0:
                    logger.info(f"{len(posts)} post(s) trouvé(s) pour {company_name}")
                    return data
                else:
                    logger.warning(f"Aucun post trouvé pour {company_name}")
                    return None
            else:
                logger.error(f"Réponse API invalide pour {company_name}: {data.get('message', 'Unknown error')}")
                return None
        else:
            logger.error(f"Format de réponse inattendu pour {company_name}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour {company_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erreur lors du parsing JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour {company_name}: {e}", exc_info=True)
        return None


def get_post_reactions(post_url: str, page_number: int = 1, reaction_type: str = "ALL") -> Optional[Dict[Any, Any]]:
    """
    Récupère les réactions détaillées d'un post via l'API LinkedIn RapidAPI
    
    Args:
        post_url: URL complète du post LinkedIn (avec paramètres UTM si présents)
        page_number: Numéro de page pour la pagination (par défaut: 1)
        reaction_type: Type de réaction à récupérer (par défaut: "ALL")
    
    Returns:
        Dict contenant les réactions ou None en cas d'erreur
    """
    if not post_url:
        logger.error("URL du post vide, impossible de récupérer les réactions")
        return None
    
    url = f"{API_BASE_URL}/post/reactions"
    
    headers = {
        'x-rapidapi-host': API_HOST,
        'x-rapidapi-key': API_KEY
    }
    
    # Utiliser l'URL complète avec les paramètres
    params = {
        'post_url': post_url,
        'page_number': page_number,
        'reaction_type': reaction_type
    }
    
    try:
        logger.info(f"Récupération des réactions pour le post: {post_url[:80]}...")
        logger.debug(f"Endpoint: {url}")
        logger.debug(f"Params: page_number={page_number}, reaction_type={reaction_type}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Réponse API reçue: {type(data).__name__}")
        
        # Vérifier la structure de réponse
        if isinstance(data, dict):
            if data.get('success') and 'data' in data:
                reactions = data.get('data', {}).get('reactions', [])
                total_reactions = data.get('data', {}).get('total_reactions', 0)
                logger.info(f"{total_reactions} réaction(s) totale(s) trouvée(s), {len(reactions)} réaction(s) sur cette page")
                
                if total_reactions == 0 or len(reactions) == 0:
                    logger.warning(f"Aucune réaction dans la réponse API pour ce post")
                    return data  # Retourner quand même les données même si vides
                
                return data
            else:
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"Réponse API invalide: {error_msg}")
                logger.debug(f"Réponse complète: {json.dumps(data, indent=2)[:1000]}")
                return None
        else:
            logger.error(f"Format de réponse inattendu: {type(data)}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête API pour le post: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text[:500]}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erreur lors du parsing JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour le post: {e}", exc_info=True)
        return None


def extract_reactions_to_csv(post_reactions: Dict, company_name: str, post_url: str, post_date: str,
                              post_analysis: Optional[Dict[str, Any]] = None,
                              prospect_analyses: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    """
    Convertit les réactions en lignes CSV avec enrichissement IA optionnel
    
    Args:
        post_reactions: Données des réactions depuis l'API
        company_name: Nom de l'entreprise
        post_url: URL du post
        post_date: Date du post (format ISO ou autre)
        post_analysis: Résultat de l'analyse IA du post (optionnel)
        prospect_analyses: Dict mapping reactor_urn -> résultat analyse prospect (optionnel)
    
    Returns:
        Liste de dictionnaires représentant les lignes CSV
    """
    reactions_rows = []
    
    if not post_reactions or not post_reactions.get('success'):
        logger.warning(f"Aucune réaction valide pour {company_name}")
        return reactions_rows
    
    reactions = post_reactions.get('data', {}).get('reactions', [])
    
    if not reactions:
        logger.info(f"Aucune réaction trouvée pour le post de {company_name}")
        return reactions_rows
    
    # Valeurs par défaut pour l'analyse du post
    post_relevant = 'False'
    post_score = ''
    post_reasoning = ''
    
    if post_analysis:
        post_relevant = 'True' if post_analysis.get('relevant', False) else 'False'
        post_score = str(post_analysis.get('score', 0))
        post_reasoning = post_analysis.get('reasoning', '').replace('\n', ' ').replace('\r', '')
    
    for reaction in reactions:
        reactor = reaction.get('reactor', {})
        reaction_type = reaction.get('reaction_type', '')
        
        # Extraire l'URL de la photo de profil (priorité: medium > large > small > original)
        profile_pictures = reactor.get('profile_pictures', {})
        profile_picture_url = (
            profile_pictures.get('medium') or
            profile_pictures.get('large') or
            profile_pictures.get('small') or
            profile_pictures.get('original') or
            ''
        )
        
        # Gérer les valeurs null/None en les convertissant en chaîne vide
        reactor_urn = reactor.get('urn') or ''
        if reactor_urn is None:
            reactor_urn = ''
        else:
            reactor_urn = str(reactor_urn)
        
        # Récupérer l'analyse du prospect si disponible
        prospect_analysis = prospect_analyses.get(reactor_urn) if prospect_analyses else None
        
        prospect_relevant = 'False'
        prospect_score = ''
        prospect_reasoning = ''
        personalized_message = ''
        
        if prospect_analysis:
            prospect_relevant = 'True' if prospect_analysis.get('relevant', False) else 'False'
            prospect_score = str(prospect_analysis.get('score', 0))
            prospect_reasoning = prospect_analysis.get('reasoning', '').replace('\n', ' ').replace('\r', '')
            personalized_message = prospect_analysis.get('personalized_message', '').replace('\n', ' ').replace('\r', '')
        
        row = {
            'company_name': company_name,
            'post_url': post_url,
            'post_date': post_date,
            'reactor_name': reactor.get('name', '') or '',
            'reactor_urn': reactor_urn,
            'profile_url': reactor.get('profile_url', '') or '',
            'reaction_type': reaction_type or '',
            'headline': reactor.get('headline', '') or '',
            'profile_picture_url': profile_picture_url,
            'post_relevant': post_relevant,
            'prospect_relevant': prospect_relevant,
            'relevance_score': prospect_score if prospect_score else post_score,
            'relevance_reasoning': prospect_reasoning if prospect_reasoning else post_reasoning,
            'personalized_message': personalized_message
        }
        reactions_rows.append(row)
    
    logger.info(f"{len(reactions_rows)} réaction(s) extraite(s) pour {company_name}")
    return reactions_rows


def save_reactions_csv(reactions_rows: List[Dict[str, str]], output_dir: Path = OUTPUT_DIR, append_mode: bool = True) -> str:
    """
    Sauvegarde les réactions dans un CSV consolidé (append mode)
    
    Args:
        reactions_rows: Liste de dictionnaires représentant les lignes CSV
        output_dir: Répertoire de sortie
        append_mode: Si True, ajoute au fichier existant. Si False, crée un nouveau fichier.
    
    Returns:
        Chemin du fichier CSV
    """
    if not reactions_rows:
        logger.warning("Aucune réaction à sauvegarder")
        return ""
    
    today = datetime.now().strftime("%Y%m%d")
    csv_file = output_dir / f"all_reactions_{today}.csv"
    
    # Colonnes du CSV (avec nouvelles colonnes IA)
    fieldnames = [
        'company_name', 'post_url', 'post_date', 'reactor_name', 
        'reactor_urn', 'profile_url', 'reaction_type', 'headline', 
        'profile_picture_url', 'post_relevant', 'prospect_relevant',
        'relevance_score', 'relevance_reasoning', 'personalized_message'
    ]
    
    # Vérifier si le fichier existe pour déterminer si on doit écrire les en-têtes
    file_exists = csv_file.exists() and append_mode
    
    try:
        mode = 'a' if append_mode else 'w'
        with open(csv_file, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Écrire les en-têtes seulement si le fichier n'existe pas ou en mode write
            if not file_exists:
                writer.writeheader()
                if not append_mode or not csv_file.exists():
                    logger.info(f"Création du fichier CSV: {csv_file}")
            
            # Écrire les lignes
            for row in reactions_rows:
                writer.writerow(row)
            
            # Forcer l'écriture sur disque immédiatement
            f.flush()
            import os
            if hasattr(f, 'fileno'):
                try:
                    os.fsync(f.fileno())
                except (OSError, io.UnsupportedOperation):
                    pass  # Certains systèmes de fichiers ne supportent pas fsync
        
        logger.info(f"✓ {len(reactions_rows)} réaction(s) sauvegardée(s) dans: {csv_file}")
        return str(csv_file)
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du CSV: {e}", exc_info=True)
        return ""


def save_post(post_data: Dict[Any, Any], company_name: str, output_dir: Path = OUTPUT_DIR, ai_analysis: Optional[Dict[str, Any]] = None) -> str:
    """
    Sauvegarde le post dans un fichier JSON avec timestamp
    
    Args:
        post_data: Données du post à sauvegarder
        company_name: Nom de l'entreprise (pour le nom de fichier)
        output_dir: Répertoire de sortie
        ai_analysis: Analyse IA du post (optionnel)
    
    Returns:
        Chemin du fichier sauvegardé
    """
    # Créer un nom de fichier safe depuis le nom de l'entreprise
    safe_name = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_').lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{safe_name}_post_{timestamp}.json"
    
    output_data = {
        "retrieved_at": datetime.now().isoformat(),
        "company_name": company_name,
        "post": post_data
    }
    
    # Ajouter l'analyse IA si disponible
    if ai_analysis:
        output_data["ai_analysis"] = {
            "post_relevant": ai_analysis.get('relevant', False),
            "analysis": ai_analysis
        }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            # Forcer l'écriture sur disque immédiatement
            f.flush()
            import os
            if hasattr(f, 'fileno'):
                try:
                    os.fsync(f.fileno())
                except (OSError, io.UnsupportedOperation):
                    pass  # Certains systèmes de fichiers ne supportent pas fsync
        
        logger.info(f"✓ Post sauvegardé dans: {filename}")
        return str(filename)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du post: {e}", exc_info=True)
        return ""


def extract_post_url_from_posts_data(posts_data: Dict[Any, Any]) -> Optional[str]:
    """
    Extrait l'URL du premier (plus récent) post depuis les données
    
    Args:
        posts_data: Données des posts depuis l'API
    
    Returns:
        URL du post ou None
    """
    try:
        if posts_data.get('success') and 'data' in posts_data:
            posts = posts_data.get('data', {}).get('posts', [])
            if posts and len(posts) > 0:
                first_post = posts[0]
                # Chercher l'URL dans différents champs possibles
                post_url = (
                    first_post.get('post_url') or
                    first_post.get('url') or
                    first_post.get('linkedin_url') or
                    first_post.get('share_url')
                )
                if post_url:
                    return post_url
                else:
                    logger.warning("URL du post non trouvée dans les données")
                    return None
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction de l'URL du post: {e}")
        return None


def extract_post_date_from_posts_data(posts_data: Dict[Any, Any]) -> str:
    """
    Extrait la date du premier post depuis les données
    
    Args:
        posts_data: Données des posts depuis l'API
    
    Returns:
        Date du post (format ISO) ou date actuelle
    """
    try:
        if posts_data.get('success') and 'data' in posts_data:
            posts = posts_data.get('data', {}).get('posts', [])
            if posts and len(posts) > 0:
                first_post = posts[0]
                # Chercher la date dans différents champs possibles
                post_date = (
                    first_post.get('created_at') or
                    first_post.get('date') or
                    first_post.get('published_at') or
                    first_post.get('timestamp')
                )
                if post_date:
                    return str(post_date)
    except Exception as e:
        logger.warning(f"Erreur lors de l'extraction de la date du post: {e}")
    
    # Fallback: date actuelle
    return datetime.now().isoformat()


def load_company_profile(profile_file: Path = Path("company_profile.json")) -> Optional[Dict[str, Any]]:
    """
    Charge le profil de l'entreprise depuis company_profile.json
    
    Args:
        profile_file: Chemin vers le fichier de profil
    
    Returns:
        Dict contenant le profil de l'entreprise ou None en cas d'erreur
    """
    if not profile_file.exists():
        logger.warning(f"Fichier de profil introuvable: {profile_file}")
        logger.warning("L'analyse IA sera désactivée. Créez company_profile.json à partir de company_profile.json.example")
        return None
    
    try:
        with open(profile_file, 'r', encoding='utf-8') as f:
            profile = json.load(f)
            logger.info(f"Profil entreprise chargé depuis {profile_file}")
            
            # Validation basique de la structure
            required_fields = ["company_name", "company_description", "target_persona", "outreach_strategy"]
            missing_fields = [field for field in required_fields if field not in profile]
            if missing_fields:
                logger.warning(f"Champs manquants dans le profil: {', '.join(missing_fields)}")
            
            return profile
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON dans {profile_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors du chargement du profil: {e}", exc_info=True)
        return None


def analyze_post_relevance(post_data: Dict[str, Any], company_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyse la pertinence d'un post LinkedIn via OpenAI
    
    Args:
        post_data: Données du post depuis l'API
        company_profile: Profil de l'entreprise depuis company_profile.json
    
    Returns:
        Dict avec relevant (bool), score (float), reasoning (str), opportunity_signals (list)
    """
    if not OPENAI_ENABLED or not openai_client:
        logger.warning("OpenAI non disponible, analyse du post ignorée")
        return None
    
    try:
        # Extraire le texte du post
        posts = post_data.get('data', {}).get('posts', [])
        if not posts:
            return None
        
        first_post = posts[0]
        post_text = first_post.get('text', '') or first_post.get('content', '') or ''
        post_stats = first_post.get('stats', {})
        author_company = first_post.get('author', {}).get('name', '') or ''
        
        # Construire le prompt pour l'IA
        prompt = f"""Tu es un expert en marketing B2B et qualification de prospects.

Analyse ce post LinkedIn et détermine s'il représente une opportunité pour contacter les personnes qui y ont réagi au nom de {company_profile.get('company_name', 'notre entreprise')}.

Informations sur notre entreprise:
- Description: {company_profile.get('company_description', '')}
- Produits/services: {', '.join(company_profile.get('products_services', []))}
- Persona cible: {json.dumps(company_profile.get('target_persona', {}), ensure_ascii=False)}

Post à analyser:
- Auteur: {author_company}
- Texte: {post_text[:1000]}
- Stats: {json.dumps(post_stats, ensure_ascii=False)}

Contexte: {company_profile.get('competitor_companies', {}).get('why_contact_on_their_posts', '')}

Réponds UNIQUEMENT avec un JSON valide au format suivant:
{{
    "relevant": true/false,
    "score": 0.0 à 1.0,
    "reasoning": "Explication en français",
    "opportunity_signals": ["signal 1", "signal 2"]
}}

Score > 0.6 = post pertinent pour contacter les réacteurs."""
        
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en qualification de prospects B2B. Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans explications supplémentaires."},
                {"role": "user", "content": prompt}
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )
        
        content = response.choices[0].message.content.strip()
        
        # Nettoyer le contenu si markdown
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        result = json.loads(content)
        result['relevant'] = result.get('relevant', False) and result.get('score', 0) >= RELEVANCE_THRESHOLD
        
        logger.info(f"Analyse du post: relevant={result.get('relevant')}, score={result.get('score', 0):.2f}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON dans la réponse OpenAI: {e}")
        logger.debug(f"Contenu reçu: {content[:500]}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du post: {e}", exc_info=True)
        return None


def analyze_prospect_relevance(prospect_data: Dict[str, str], post_data: Dict[str, Any], 
                                company_profile: Dict[str, Any], post_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyse la pertinence d'un prospect (personne ayant réagi) via OpenAI
    
    Args:
        prospect_data: Données du prospect (reactor)
        post_data: Données du post
        company_profile: Profil de l'entreprise
        post_analysis: Résultat de l'analyse du post
    
    Returns:
        Dict avec relevant (bool), score (float), reasoning (str), match_criteria (list)
    """
    if not OPENAI_ENABLED or not openai_client:
        return None
    
    try:
        prospect_name = prospect_data.get('reactor_name', '')
        headline = prospect_data.get('headline', '')
        reaction_type = prospect_data.get('reaction_type', '')
        
        # Extraire le texte du post
        posts = post_data.get('data', {}).get('posts', [])
        post_text = ''
        if posts:
            first_post = posts[0]
            post_text = first_post.get('text', '') or first_post.get('content', '') or ''
        
        prompt = f"""Tu es un expert en qualification de prospects B2B.

Analyse ce prospect et détermine s'il correspond au persona cible de {company_profile.get('company_name', 'notre entreprise')}.

Profil du prospect:
- Nom: {prospect_name}
- Headline: {headline}
- Type de réaction au post: {reaction_type}

Post sur lequel il a réagi:
- Texte: {post_text[:500]}

Notre persona cible:
{json.dumps(company_profile.get('target_persona', {}), ensure_ascii=False)}

Signaux idéaux: {', '.join(company_profile.get('outreach_strategy', {}).get('ideal_signals', []))}

Réponds UNIQUEMENT avec un JSON valide:
{{
    "relevant": true/false,
    "score": 0.0 à 1.0,
    "reasoning": "Explication en français",
    "match_criteria": ["critère 1", "critère 2"]
}}"""
        
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en qualification de prospects B2B. Réponds UNIQUEMENT avec du JSON valide, sans markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )
        
        content = response.choices[0].message.content.strip()
        
        # Nettoyer le contenu
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        result = json.loads(content)
        result['relevant'] = result.get('relevant', False) and result.get('score', 0) >= RELEVANCE_THRESHOLD
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON pour prospect {prospect_data.get('reactor_name', 'Unknown')}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du prospect {prospect_data.get('reactor_name', 'Unknown')}: {e}")
        return None


def generate_personalized_message(prospect_data: Dict[str, str], post_data: Dict[str, Any],
                                   company_profile: Dict[str, Any], post_analysis: Dict[str, Any]) -> Optional[str]:
    """
    Génère un message personnalisé (icebreaker) via OpenAI pour un prospect pertinent
    
    Args:
        prospect_data: Données du prospect
        post_data: Données du post
        company_profile: Profil de l'entreprise
        post_analysis: Résultat de l'analyse du post
    
    Returns:
        Message personnalisé en français ou None
    """
    if not OPENAI_ENABLED or not openai_client:
        return None
    
    try:
        prospect_name = prospect_data.get('reactor_name', '')
        headline = prospect_data.get('headline', '')
        
        # Extraire le texte du post
        posts = post_data.get('data', {}).get('posts', [])
        post_text = ''
        author_company = ''
        if posts:
            first_post = posts[0]
            post_text = first_post.get('text', '') or first_post.get('content', '') or ''
            author_company = first_post.get('author', {}).get('name', '') or ''
        
        # Détecter l'entreprise du prospect depuis le headline
        prospect_company = ''
        if headline:
            # Chercher des patterns comme "@Company" ou "chez Company"
            match = re.search(r'(?:@|chez|at)\s*([A-Z][a-zA-Z\s]+)', headline)
            if match:
                prospect_company = match.group(1).strip()
        
        message_template = company_profile.get('outreach_strategy', {}).get('message_template', {})
        
        prompt = f"""Tu es un expert en outbound B2B. Génère un message personnalisé (icebreaker) LinkedIn pour ce prospect.

Prospect:
- Nom: {prospect_name}
- Headline: {headline}
- Entreprise (détectée): {prospect_company}

Post sur lequel il a réagi:
- Auteur: {author_company}
- Texte: {post_text[:800]}

Notre entreprise:
- Nom: {company_profile.get('company_name', '')}
- Description: {company_profile.get('company_description', '')}
- Ce qu'on offre: {company_profile.get('outreach_strategy', {}).get('what_offers', '')}
- Proposition de valeur: {company_profile.get('outreach_strategy', {}).get('value_proposition', '')}

Style souhaité:
- Ton: {message_template.get('tone', 'professionnel, amical')}
- Structure: {message_template.get('structure', '')}
- Points clés: {', '.join(message_template.get('key_points', []))}

Génère un message court (maximum 150 mots) en français qui:
1. Fait référence au post spécifique ("Je te contacte car j'ai vu que tu as réagi au post de [entreprise] sur [sujet]")
2. Connecte avec notre solution ("C'est quelque chose que nous faisons/résolvons chez [notre entreprise]")
3. Pose une question ouverte pertinente ("Est-ce une problématique que vous rencontrez chez [entreprise prospect] ?")

Réponds UNIQUEMENT avec le message, sans markdown, sans "Message:", sans guillemets, directement le texte du message."""
        
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un expert en rédaction de messages outbound B2B. Réponds UNIQUEMENT avec le message final, sans formatage supplémentaire."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Plus créatif pour les messages
            max_tokens=300
        )
        
        message = response.choices[0].message.content.strip()
        
        # Nettoyer le message
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        if message.startswith("Message:"):
            message = message[8:].strip()
        
        logger.info(f"Message généré pour {prospect_name}: {message[:50]}...")
        return message
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du message pour {prospect_data.get('reactor_name', 'Unknown')}: {e}")
        return None


def save_progress_on_interrupt(signum, frame):
    """
    Gestionnaire de signal pour sauvegarder les données en cas d'interruption (Ctrl+C)
    """
    global _current_progress, _save_on_interrupt_enabled
    
    if not _save_on_interrupt_enabled or not _current_progress.get('company'):
        logger.warning("\n⚠️ Interruption détectée mais aucune progression à sauvegarder")
        sys.exit(0)
    
    logger.warning("\n⚠️ Interruption détectée (Ctrl+C) - Sauvegarde des données en cours...")
    
    try:
        company_name = _current_progress.get('company', {}).get('company_name', 'Unknown')
        posts_data = _current_progress.get('posts_data')
        post_url = _current_progress.get('post_url')
        post_analysis = _current_progress.get('post_analysis')
        reactions_rows = _current_progress.get('reactions_rows', [])
        prospect_analyses = _current_progress.get('prospect_analyses', {})
        
        # Sauvegarder le post JSON avec analyse IA si disponible
        if posts_data:
            saved_file = save_post(posts_data, company_name, ai_analysis=post_analysis)
            logger.info(f"✓ Post sauvegardé: {saved_file}")
        
        # Sauvegarder les réactions récupérées jusqu'ici
        if reactions_rows:
            post_date = extract_post_date_from_posts_data(posts_data) if posts_data else datetime.now().isoformat()
            
            # Re-extraire les réactions avec les analyses si disponible
            # Pour simplifier, on sauvegarde directement les rows déjà extraites
            csv_file = save_reactions_csv(reactions_rows, append_mode=True)
            if csv_file:
                logger.info(f"✓ {len(reactions_rows)} réaction(s) sauvegardée(s) dans: {csv_file}")
            else:
                logger.warning("⚠️ Erreur lors de la sauvegarde des réactions")
        
        logger.info("✓ Sauvegarde d'urgence terminée - Données partiellement sauvegardées")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde d'urgence: {e}", exc_info=True)
    
    sys.exit(0)


# Enregistrer le gestionnaire de signaux
signal.signal(signal.SIGINT, save_progress_on_interrupt)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, save_progress_on_interrupt)


def check_if_already_fetched_today(post_url: str, company_name: str, output_dir: Path = OUTPUT_DIR) -> bool:
    """
    Vérifie si le post a déjà été traité aujourd'hui (en vérifiant dans le CSV consolidé)
    
    Args:
        post_url: URL du post
        company_name: Nom de l'entreprise
        output_dir: Répertoire contenant les fichiers
    
    Returns:
        True si déjà traité aujourd'hui, False sinon
    """
    today = datetime.now().strftime("%Y%m%d")
    csv_file = output_dir / f"all_reactions_{today}.csv"
    
    if not csv_file.exists():
        return False
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Vérifier si le post_url existe déjà pour cette entreprise
                if row.get('post_url') == post_url and row.get('company_name') == company_name:
                    logger.info(f"Le post {post_url[:50]}... a déjà été traité aujourd'hui pour {company_name}")
                    return True
        return False
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture du CSV pour vérifier les doublons: {e}")
        return False


def process_company(company: Dict[str, str]) -> bool:
    """
    Traite une entreprise : récupère le dernier post, analyse sa pertinence via IA,
    puis récupère les réactions et qualifie les prospects si pertinent
    
    Args:
        company: Dictionnaire contenant les infos de l'entreprise
    
    Returns:
        True si succès, False sinon
    """
    company_name = company.get('company_name', 'Unknown')
    
    if not company_name:
        logger.error(f"Nom d'entreprise manquant, entreprise ignorée")
        return False
    
    logger.info("=" * 60)
    logger.info(f"Traitement de: {company_name}")
    logger.info("=" * 60)
    
    # 1. Récupérer les posts de l'entreprise
    posts_data = get_company_posts(company_name)
    
    if not posts_data:
        logger.warning(f"Impossible de récupérer les posts pour {company_name}")
        return False
    
    # 2. Extraire l'URL du premier (plus récent) post
    post_url = extract_post_url_from_posts_data(posts_data)
    
    if not post_url:
        logger.warning(f"Impossible d'extraire l'URL du post pour {company_name}")
        return False
    
    logger.info(f"Post trouvé: {post_url}")
    
    # 3. Vérifier si le post a déjà été traité aujourd'hui
    if check_if_already_fetched_today(post_url, company_name):
        logger.info(f"Le post de {company_name} a déjà été traité aujourd'hui")
        return True
    
    # Activer la sauvegarde en cas d'interruption pour cette entreprise
    global _save_on_interrupt_enabled, _current_progress
    _save_on_interrupt_enabled = True
    _current_progress = {
        'company': company,
        'posts_data': posts_data,
        'post_url': post_url,
        'post_analysis': None,
        'reactions_rows': [],
        'prospect_analyses': {},
        'processed_reactors': set(),
        'page_number': 1
    }
    
    # 4. Charger le profil de l'entreprise pour l'analyse IA
    company_profile = None
    post_analysis = None
    
    if OPENAI_ENABLED:
        company_profile = load_company_profile()
        
        if company_profile:
            # 5. Analyser la pertinence du post AVANT de récupérer les réactions
            logger.info("🔍 Analyse IA de la pertinence du post...")
            post_analysis = analyze_post_relevance(posts_data, company_profile)
            _current_progress['post_analysis'] = post_analysis
            
            if post_analysis:
                is_relevant = post_analysis.get('relevant', False)
                score = post_analysis.get('score', 0)
                logger.info(f"  Résultat: {'✓ Post PERTINENT' if is_relevant else '✗ Post NON PERTINENT'} (score: {score:.2f})")
                
                if not is_relevant:
                    logger.info(f"  Le post n'est pas pertinent (score {score:.2f} < seuil {RELEVANCE_THRESHOLD})")
                    logger.info(f"  ⚠ Économie d'appels API: réactions non récupérées")
                    
                    # Sauvegarder le post avec l'analyse mais sans réactions
                    saved_file = save_post(posts_data, company_name, ai_analysis=post_analysis)
                    logger.info(f"  Post sauvegardé (sans réactions): {saved_file}")
                    
                    # Désactiver la sauvegarde d'interruption
                    _save_on_interrupt_enabled = False
                    return True
            else:
                logger.warning("  Analyse IA du post échouée, on continue quand même avec les réactions")
        else:
            logger.warning("  Profil entreprise non disponible, analyse IA désactivée")
    
    # 6. Si post pertinent (ou analyse IA désactivée), récupérer les réactions
    logger.info("📥 Récupération des réactions du post...")
    all_reactions_rows = []
    post_date = extract_post_date_from_posts_data(posts_data)
    page_number = 1
    total_reactions = 0
    all_reactions_flat = []  # Liste plate de toutes les réactions (pour éviter les doublons)
    prospect_analyses = {}
    _current_progress['page_number'] = page_number
    
    # D'abord, récupérer toutes les réactions avec pagination
    while True:
        reactions_data = get_post_reactions(post_url, page_number=page_number, reaction_type="ALL")
        _current_progress['page_number'] = page_number
        
        if not reactions_data:
            if page_number == 1:
                logger.warning(f"⚠ Impossible de récupérer les réactions détaillées pour {company_name}")
                break
            else:
                break
        
        # Obtenir le total de réactions (disponible dans la première réponse)
        if page_number == 1:
            total_reactions = reactions_data.get('data', {}).get('total_reactions', 0)
            logger.info(f"  {total_reactions} réaction(s) totale(s) trouvée(s)")
        
        # Extraire les réactions de cette page
        reactions = reactions_data.get('data', {}).get('reactions', [])
        if not reactions:
            break
        
        # Ajouter les réactions à la liste (format brut pour analyse)
        all_reactions_flat.extend(reactions)
        
        # Sauvegarder immédiatement cette page de réactions (sans analyses pour l'instant)
        if reactions:
            page_reactions_data = {
                'success': True,
                'data': {
                    'reactions': reactions,
                    'total_reactions': total_reactions
                }
            }
            page_reactions_rows = extract_reactions_to_csv(
                page_reactions_data, company_name, post_url, post_date,
                post_analysis=post_analysis,
                prospect_analyses={}  # Analyses pas encore faites
            )
            if page_reactions_rows:
                # Sauvegarder cette page au fur et à mesure
                csv_file = save_reactions_csv(page_reactions_rows, append_mode=True)
                all_reactions_rows.extend(page_reactions_rows)
                _current_progress['reactions_rows'] = all_reactions_rows
                logger.info(f"  ✓ Page {page_number}: {len(page_reactions_rows)} réaction(s) sauvegardée(s)")
        
        # Passer à la page suivante
        page_number += 1
        
        # Limite de sécurité pour éviter les boucles infinies
        if page_number > 50:
            logger.warning(f"  Limite de pages atteinte (50), arrêt de la pagination")
            break
        
        # Si on a toutes les réactions, arrêter
        if len(all_reactions_flat) >= total_reactions:
            break
    
    # 7. Analyser chaque prospect et générer des messages si post pertinent
    # Note: Les réactions sont déjà sauvegardées, on va maintenant les enrichir avec les analyses
    
    if OPENAI_ENABLED and company_profile and post_analysis and post_analysis.get('relevant', False):
        logger.info("🔍 Analyse IA des prospects et génération de messages...")
        
        # Créer un mapping reactor_urn -> row index pour mettre à jour les rows existantes
        reactor_to_row_index = {}
        for idx, row in enumerate(all_reactions_rows):
            urn = row.get('reactor_urn', '')
            if urn:
                reactor_to_row_index[urn] = idx
        
        # Parcourir toutes les réactions récupérées pour les analyser
        for reaction in all_reactions_flat:
            reactor = reaction.get('reactor', {})
            reactor_urn = str(reactor.get('urn') or '')
            
            if not reactor_urn or reactor_urn in prospect_analyses:
                continue  # Éviter les doublons
            
            prospect_data = {
                'reactor_name': reactor.get('name', ''),
                'reactor_urn': reactor_urn,
                'headline': reactor.get('headline', ''),
                'reaction_type': reaction.get('reaction_type', '')
            }
            
            # Analyser le prospect
            prospect_analysis = analyze_prospect_relevance(
                prospect_data, posts_data, company_profile, post_analysis
            )
            
            if prospect_analysis:
                prospect_relevant = prospect_analysis.get('relevant', False)
                message = None  # Initialiser message
                
                # Si prospect pertinent, générer un message personnalisé
                if prospect_relevant:
                    logger.info(f"  ✓ Prospect pertinent: {prospect_data.get('reactor_name', 'Unknown')}")
                    message = generate_personalized_message(
                        prospect_data, posts_data, company_profile, post_analysis
                    )
                    if message:
                        prospect_analysis['personalized_message'] = message
                else:
                    logger.debug(f"  Prospect non pertinent: {prospect_data.get('reactor_name', 'Unknown')}")
                
                prospect_analyses[reactor_urn] = prospect_analysis
                _current_progress['prospect_analyses'] = prospect_analyses
                
                # Mettre à jour la row correspondante dans all_reactions_rows
                if reactor_urn in reactor_to_row_index:
                    idx = reactor_to_row_index[reactor_urn]
                    row = all_reactions_rows[idx]
                    row['prospect_relevant'] = 'True' if prospect_relevant else 'False'
                    row['relevance_score'] = str(prospect_analysis.get('score', 0))
                    row['relevance_reasoning'] = prospect_analysis.get('reasoning', '').replace('\n', ' ').replace('\r', '')
                    if message:
                        row['personalized_message'] = message.replace('\n', ' ').replace('\r', '')
                
                # Sauvegarder immédiatement après chaque analyse (mettre à jour le CSV)
                if reactor_urn in reactor_to_row_index:
                    # Recréer le CSV avec toutes les données mises à jour
                    # Pour simplifier, on sauvegarde juste la row mise à jour dans un fichier temporaire
                    # et on met à jour le CSV principal périodiquement
                    _current_progress['reactions_rows'] = all_reactions_rows
            
            # Petit délai pour éviter les rate limits
            time.sleep(0.5)
        
        logger.info(f"  {len([a for a in prospect_analyses.values() if a.get('relevant', False)])} prospect(s) pertinent(s) trouvé(s)")
        
        # Sauvegarder le CSV final avec toutes les analyses
        # On recrée le CSV avec toutes les données enrichies
        today = datetime.now().strftime("%Y%m%d")
        csv_file = OUTPUT_DIR / f"all_reactions_{today}.csv"
        
        # Recréer le CSV complet avec toutes les analyses
        fieldnames = [
            'company_name', 'post_url', 'post_date', 'reactor_name', 
            'reactor_urn', 'profile_url', 'reaction_type', 'headline', 
            'profile_picture_url', 'post_relevant', 'prospect_relevant',
            'relevance_score', 'relevance_reasoning', 'personalized_message'
        ]
        
        # Lire les données existantes (sans les doublons de ce post)
        existing_rows = []
        if csv_file.exists():
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Exclure les rows de ce post (on va les réécrire avec les analyses)
                        if row.get('post_url') != post_url or row.get('company_name') != company_name:
                            existing_rows.append(row)
            except Exception as e:
                logger.warning(f"Erreur lors de la lecture du CSV existant: {e}")
        
        # Écrire le CSV complet avec toutes les données (existantes + mises à jour avec analyses)
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_rows)
                writer.writerows(all_reactions_rows)
            logger.info(f"✓ CSV mis à jour avec toutes les analyses: {csv_file}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du CSV: {e}", exc_info=True)
    
    # 8. Sauvegarder le post complet en JSON avec analyse IA (si pas déjà fait)
    saved_file = save_post(posts_data, company_name, ai_analysis=post_analysis)
    
    # 9. Afficher le résumé final
    if all_reactions_rows:
        today = datetime.now().strftime("%Y%m%d")
        csv_file = OUTPUT_DIR / f"all_reactions_{today}.csv"
        relevant_prospects = len([r for r in all_reactions_rows if r.get('prospect_relevant') == 'True'])
        logger.info(f"✓ {len(all_reactions_rows)} réaction(s) extraite(s) sur {total_reactions} totale(s) pour {company_name}")
        logger.info(f"  {relevant_prospects} prospect(s) pertinent(s) avec message généré")
        logger.info(f"  CSV: {csv_file}")
        
        if len(all_reactions_rows) < total_reactions:
            logger.warning(f"  Note: Il y a {total_reactions} réactions au total, mais seulement {len(all_reactions_rows)} ont été extraites")
    else:
        logger.warning(f"⚠ Aucune réaction n'a pu être extraite pour {company_name}")
        logger.warning(f"  Le post a été sauvegardé en JSON mais aucune réaction n'a été trouvée")
    
    # Afficher un résumé
    logger.info(f"✓ Post récupéré avec succès pour {company_name}")
    logger.info(f"  Fichier JSON: {saved_file}")
    
    # Désactiver la sauvegarde d'interruption après traitement complet
    _save_on_interrupt_enabled = False
    _current_progress = {
        'company': None,
        'posts_data': None,
        'post_url': None,
        'post_analysis': None,
        'reactions_rows': [],
        'prospect_analyses': {},
        'processed_reactors': set(),
        'page_number': 1
    }
    
    return True


def main():
    """Fonction principale"""
    logger.info("=" * 60)
    logger.info("Début de la récupération des posts LinkedIn")
    logger.info("=" * 60)
    
    # Charger les entreprises depuis le CSV
    companies = load_companies_from_csv()
    
    if not companies:
        logger.error("Aucune entreprise à traiter. Vérifiez le fichier companies_to_follow.csv")
        return
    
    # Traiter chaque entreprise
    success_count = 0
    error_count = 0
    
    for company in companies:
        try:
            if process_company(company):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {company.get('company_name', 'Unknown')}: {e}", exc_info=True)
            error_count += 1
    
    # Résumé final
    logger.info("=" * 60)
    logger.info("Résumé de l'exécution:")
    logger.info(f"  ✓ Entreprises traitées avec succès: {success_count}")
    logger.info(f"  ✗ Erreurs: {error_count}")
    logger.info(f"  Total: {len(companies)} entreprise(s)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
