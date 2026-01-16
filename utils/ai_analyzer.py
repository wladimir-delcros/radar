"""
Module d'analyse IA pour la qualification de prospects LinkedIn
Analyse améliorée avec filtrage des concurrents et scoring détaillé
"""
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configuration OpenAI depuis config.json
CONFIG_FILE = Path(__file__).parent.parent / "config.json"

OPENAI_ENABLED = False
openai_client = None
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 500
RELEVANCE_THRESHOLD = 0.6


def init_openai():
    """Initialise le client OpenAI depuis la configuration"""
    global OPENAI_ENABLED, openai_client, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS, RELEVANCE_THRESHOLD
    
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI package non disponible. Installez-le avec: pip install openai")
        return
    
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            openai_config = config.get('openai', {})
            OPENAI_ENABLED = openai_config.get('enabled', False)
            OPENAI_API_KEY = openai_config.get('api_key')
            
            if OPENAI_ENABLED and OPENAI_API_KEY:
                openai_client = OpenAI(api_key=OPENAI_API_KEY)
                OPENAI_MODEL = openai_config.get('model', 'gpt-4o-mini')
                OPENAI_TEMPERATURE = openai_config.get('temperature', 0.3)
                OPENAI_MAX_TOKENS = openai_config.get('max_tokens', 500)
                RELEVANCE_THRESHOLD = openai_config.get('relevance_threshold', 0.6)
                logger.info("Client OpenAI initialisé avec succès")
            else:
                OPENAI_ENABLED = False
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation OpenAI: {e}")
        OPENAI_ENABLED = False


# Initialiser au chargement du module
init_openai()


def analyze_post_relevance(post_data: Dict[str, Any], company_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analyse la pertinence d'un post LinkedIn via OpenAI
    
    Args:
        post_data: Données du post depuis l'API
        company_profile: Profil de l'entreprise
    
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


def analyze_prospect_with_competitor_filter(prospect_data: Dict[str, Any], 
                                           post_data: Dict[str, Any],
                                           company_profile: Dict[str, Any], 
                                           post_analysis: Dict[str, Any],
                                           competitors_list: List[Dict[str, Any]],
                                           filter_competitors: bool = True) -> Optional[Dict[str, Any]]:
    """
    Analyse la pertinence d'un prospect avec vérification des concurrents
    
    Args:
        prospect_data: Données du prospect (reactor)
        post_data: Données du post
        company_profile: Profil de l'entreprise
        post_analysis: Résultat de l'analyse du post
        competitors_list: Liste des concurrents
        filter_competitors: Activer le filtrage des concurrents
    
    Returns:
        Dict avec relevant (bool), score (float), reasoning (str), match_criteria (list),
        is_competitor (bool), competitor_name (Optional[str])
    """
    # Vérifier d'abord si c'est un concurrent
    is_competitor = False
    competitor_name = None
    
    if filter_competitors:
        from utils.intelligent_scoring import check_if_competitor
        is_competitor, competitor_name = check_if_competitor(
            prospect_data,
            company_profile.get('client_id', 0),
            competitors_list
        )
        
        if is_competitor:
            return {
                'relevant': False,
                'score': 0.0,
                'reasoning': f'Prospect travaille pour un concurrent: {competitor_name}',
                'match_criteria': [],
                'is_competitor': True,
                'competitor_name': competitor_name
            }
    
    # Analyser le prospect normalement
    result = analyze_prospect_relevance(prospect_data, post_data, company_profile, post_analysis)
    
    if result:
        result['is_competitor'] = False
        result['competitor_name'] = None
        return result
    
    return None


def analyze_prospect_relevance(prospect_data: Dict[str, Any], 
                               post_data: Dict[str, Any], 
                               company_profile: Dict[str, Any], 
                               post_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        
        # Liste des concurrents pour mention dans le prompt
        competitors_names = []
        if 'competitor_companies' in company_profile:
            competitors_names = company_profile.get('competitor_companies', {}).get('scraped_companies', [])
        
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

IMPORTANT - Concurrence à éviter:
Liste des concurrents à NE PAS contacter: {', '.join(competitors_names) if competitors_names else 'Aucun'}
Si le prospect travaille pour un de ces concurrents, le score doit être 0.0.

Réponds UNIQUEMENT avec un JSON valide:
{{
    "relevant": true/false,
    "score": 0.0 à 1.0,
    "reasoning": "Explication en français détaillée",
    "match_criteria": ["critère 1", "critère 2"],
    "strengths": ["point fort 1", "point fort 2"],
    "weaknesses": ["point faible 1"]
}}

Le score doit être précis: 0.8-1.0 = excellent match, 0.6-0.8 = bon match, 0.4-0.6 = match partiel, <0.4 = faible match."""
        
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


def generate_scoring_details(prospect_data: Dict[str, Any],
                            company_profile: Dict[str, Any],
                            scoring_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Génère un rapport détaillé de scoring pour un prospect
    
    Args:
        prospect_data: Données du prospect
        company_profile: Profil entreprise
        scoring_result: Résultat du scoring
    
    Returns:
        Dict avec détails du scoring
    """
    target_persona = company_profile.get('target_persona', {})
    
    details = {
        'prospect_name': prospect_data.get('reactor_name', ''),
        'headline': prospect_data.get('headline', ''),
        'total_score': scoring_result.get('total_score', 0.0),
        'breakdown': {
            'job_title': {
                'score': scoring_result.get('job_title_score', 0.0),
                'max_score': 0.3,
                'details': scoring_result.get('details', {}).get('job_title', '')
            },
            'company': {
                'score': scoring_result.get('company_score', 0.0),
                'max_score': 0.25,
                'details': scoring_result.get('details', {}).get('prospect_company', '')
            },
            'location': {
                'score': scoring_result.get('location_score', 0.0),
                'max_score': 0.15,
                'details': ''
            },
            'engagement': {
                'score': scoring_result.get('engagement_score', 0.0),
                'max_score': 0.15,
                'details': scoring_result.get('details', {}).get('reaction_type', '')
            },
            'post_relevance': {
                'score': scoring_result.get('post_relevance_score', 0.0),
                'max_score': 0.15,
                'details': ''
            }
        },
        'recommendation': ''
    }
    
    # Générer une recommandation basée sur le score
    total_score = details['total_score']
    if total_score >= 0.8:
        details['recommendation'] = 'Excellente cible - Contact prioritaire recommandé'
    elif total_score >= 0.6:
        details['recommendation'] = 'Bonne cible - Contact recommandé'
    elif total_score >= 0.4:
        details['recommendation'] = 'Cible potentielle - À évaluer selon contexte'
    else:
        details['recommendation'] = 'Faible correspondance - Non recommandé'
    
    return details


def check_company_match(prospect_company: str, target_persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Vérifie si la company du prospect correspond aux critères
    
    Args:
        prospect_company: Nom de l'entreprise du prospect
        target_persona: Persona cible
    
    Returns:
        Dict avec match (bool), details (dict)
    """
    if not prospect_company:
        return {'match': False, 'details': {'reason': 'Aucune entreprise détectée'}}
    
    prospect_lower = prospect_company.lower()
    matches = {
        'company_type': False,
        'industry': False,
        'size': False
    }
    
    # Company types
    company_types = target_persona.get('company_types', [])
    for ct in company_types:
        if ct.lower() in prospect_lower:
            matches['company_type'] = True
            break
    
    # Industries
    industries = target_persona.get('industries', [])
    for ind in industries:
        if ind.lower() in prospect_lower:
            matches['industry'] = True
            break
    
    # Size (approximatif)
    company_size = target_persona.get('company_size', '').lower()
    if company_size and any(word in prospect_lower for word in ['group', 'corp', 'corporation']):
        matches['size'] = True
    
    match_score = sum(matches.values()) / len(matches) if matches else 0
    
    return {
        'match': match_score > 0,
        'match_score': match_score,
        'details': matches
    }


def generate_personalized_message(prospect_data: Dict[str, Any], 
                                  post_data: Dict[str, Any],
                                  company_profile: Dict[str, Any], 
                                  post_analysis: Dict[str, Any]) -> Optional[str]:
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
        from utils.intelligent_scoring import extract_company_from_headline
        prospect_company = extract_company_from_headline(headline)
        
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


def generate_message_for_prospect(client_id: int, prospect_data: Dict[str, Any], 
                                  company_profile: Optional[Dict[str, Any]] = None,
                                  radar_message_template: Optional[str] = None) -> Optional[str]:
    """
    Génère un message personnalisé pour un prospect spécifique
    Utilise les données du prospect pour créer le message sans nécessiter les détails complets du post
    
    Args:
        client_id: ID du client
        prospect_data: Données du prospect depuis la base de données
        company_profile: Profil de l'entreprise (optionnel, sera récupéré si non fourni)
        radar_message_template: Message template du radar (optionnel, prioritaire sur le template du profil)
    
    Returns:
        Message personnalisé en français ou None
    """
    if not OPENAI_ENABLED or not openai_client:
        logger.warning("OpenAI non disponible, génération de message ignorée")
        return None
    
    try:
        # Récupérer le profil entreprise si non fourni
        if not company_profile:
            from utils.database import get_client_profile_as_dict
            company_profile = get_client_profile_as_dict(client_id)
            if not company_profile:
                logger.error("Profil entreprise non trouvé")
                return None
        
        prospect_name = prospect_data.get('reactor_name', '')
        headline = prospect_data.get('headline', '')
        post_url = prospect_data.get('post_url', '')
        competitor_name = prospect_data.get('company_name', '') or prospect_data.get('competitor_name', '')
        
        # Détecter l'entreprise du prospect depuis le headline
        from utils.intelligent_scoring import extract_company_from_headline
        prospect_company = extract_company_from_headline(headline)
        
        # Utiliser le message template du radar si disponible, sinon celui du profil entreprise
        if radar_message_template:
            # Le message template du radar est utilisé comme base
            message_template_text = radar_message_template
            message_template = {}  # Pas de template du profil si on utilise celui du radar
        else:
            # Utiliser le template du profil entreprise
            message_template = company_profile.get('outreach_strategy', {}).get('message_template', {})
            message_template_text = message_template.get('structure', '') or company_profile.get('outreach_strategy', {}).get('message_example', '')
        
        # Créer un prompt simplifié qui utilise les données disponibles
        prompt = f"""Tu es un expert en outbound B2B. Génère un message personnalisé (icebreaker) LinkedIn pour ce prospect.

Prospect:
- Nom: {prospect_name}
- Headline: {headline}
- Entreprise (détectée): {prospect_company}

Contexte:
- Le prospect a réagi à un post de {competitor_name}
- Post: {post_url}

Notre entreprise:
- Nom: {company_profile.get('company_name', '')}
- Description: {company_profile.get('company_description', '')}
- Ce qu'on offre: {company_profile.get('outreach_strategy', {}).get('what_offers', '')}
- Proposition de valeur: {company_profile.get('outreach_strategy', {}).get('value_proposition', '')}

Style souhaité:
- Ton: {message_template.get('tone', 'professionnel, amical') if not radar_message_template else 'professionnel, amical'}
- Structure/Template: {message_template_text if message_template_text else 'Message personnalisé basé sur la réaction du prospect'}
- Points clés: {', '.join(message_template.get('key_points', [])) if not radar_message_template else 'Personnalisation basée sur le template du radar'}

Génère un message court (maximum 150 mots) en français qui:
{f'1. Suit le template du radar: "{message_template_text}"' if radar_message_template else '1. Fait référence à la réaction du prospect ("Je te contacte car j\'ai vu que tu as réagi à un post de ' + competitor_name + '")'}
2. Connecte avec notre solution en se basant sur le titre/headline du prospect
3. Pose une question ouverte pertinente basée sur le persona et ce que nous offrons
4. Est naturel, personnel et engageant
{f'5. Remplace les variables du template ([entreprise], [sujet], [notre entreprise]) par les valeurs réelles' if radar_message_template else ''}

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
