"""
Module de scoring intelligent pour la qualification de prospects
Filtre les concurrents et calcule un score multi-critères basé sur le profil entreprise
"""
import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

CONFIG_FILE = Path(__file__).parent.parent / "config.json"
OPENAI_ENABLED = False
openai_client = None
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 1000


def init_openai_for_scoring():
    """Initialise le client OpenAI pour le scoring"""
    global OPENAI_ENABLED, openai_client, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS
    
    if not OPENAI_AVAILABLE:
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
                OPENAI_MAX_TOKENS = openai_config.get('max_tokens', 1000)
                logger.debug("Client OpenAI initialisé pour le scoring")
            else:
                OPENAI_ENABLED = False
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation OpenAI pour scoring: {e}")
        OPENAI_ENABLED = False


# Initialiser au chargement du module
init_openai_for_scoring()


def similarity_score(a: str, b: str) -> float:
    """Calcule un score de similarité entre deux chaînes (0-1)"""
    if not a or not b:
        return 0.0
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    return SequenceMatcher(None, a_lower, b_lower).ratio()


def extract_company_from_headline(headline: str) -> Optional[str]:
    """
    Extrait le nom de l'entreprise depuis un headline LinkedIn
    
    Args:
        headline: Headline du profil LinkedIn (ex: "CEO chez CompanyName")
    
    Returns:
        Nom de l'entreprise ou None
    """
    if not headline:
        return None
    
    # Patterns courants pour extraire l'entreprise
    patterns = [
        r'(?:chez|at|@|chez|chez)\s+([A-Z][a-zA-Z0-9\s&\-]+)',
        r'([A-Z][a-zA-Z0-9\s&\-]+)\s+(?:|Ltd|Inc|Corp|S\.A\.|SAS|SARL)',
        r'[A-Z][a-z]+\s+(?:chez|at|@)\s+([A-Z][a-zA-Z0-9\s&\-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, headline, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Filtrer les mots communs
            if company.lower() not in ['the', 'and', 'or', 'but', 'for', 'with', 'company']:
                return company
    
    return None


def check_if_competitor(prospect_data: Dict[str, Any], client_id: int,
                        competitors_list: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Vérifie si le prospect travaille pour un concurrent
    
    Args:
        prospect_data: Données du prospect (headline, profile_url, etc.)
        client_id: ID du client
        competitors_list: Liste des concurrents du client
    
    Returns:
        Tuple (is_competitor: bool, matched_competitor_name: Optional[str])
    """
    if not competitors_list:
        return False, None
    
    headline = prospect_data.get('headline', '') or ''
    profile_url = prospect_data.get('profile_url', '') or ''
    
    # Extraire l'entreprise du headline
    prospect_company = extract_company_from_headline(headline)
    
    # Comparer avec la liste des concurrents
    for competitor in competitors_list:
        competitor_name = competitor.get('company_name', '').lower().strip()
        if not competitor_name:
            continue
        
        # Vérification directe dans le headline
        if headline:
            headline_lower = headline.lower()
            # Recherche exacte ou partielle
            if competitor_name in headline_lower:
                return True, competitor['company_name']
            
            # Recherche avec similarité
            if prospect_company:
                similarity = similarity_score(prospect_company, competitor_name)
                if similarity > 0.8:  # Seuil de similarité élevé
                    return True, competitor['company_name']
        
        # Vérification dans l'URL du profil
        if profile_url and competitor_name in profile_url.lower():
            return True, competitor['company_name']
    
    return False, None


def calculate_job_title_score(job_title: str, target_job_titles: List[str]) -> float:
    """
    Calcule un score de correspondance pour le job title (0-0.3)
    
    Args:
        job_title: Titre du prospect (depuis headline)
        target_job_titles: Liste des titres cibles
    
    Returns:
        Score entre 0 et 0.3
    """
    if not job_title or not target_job_titles:
        return 0.0
    
    job_title_lower = job_title.lower()
    
    # Correspondance exacte
    for target_title in target_job_titles:
        target_lower = target_title.lower()
        if target_lower == job_title_lower:
            return 0.3
        
        # Correspondance partielle (mots clés)
        if target_lower in job_title_lower or job_title_lower in target_lower:
            return 0.2
        
        # Mots clés communs
        target_words = set(target_lower.split())
        job_words = set(job_title_lower.split())
        common_words = target_words.intersection(job_words)
        if len(common_words) >= 2:
            return 0.15
        
        # Domaine proche (similarité)
        similarity = similarity_score(job_title_lower, target_lower)
        if similarity > 0.6:
            return 0.1
    
    return 0.0


def calculate_company_match_score(prospect_company: str, target_persona: Dict[str, Any]) -> float:
    """
    Calcule un score de correspondance pour l'entreprise (0-0.25)
    
    Args:
        prospect_company: Nom de l'entreprise du prospect
        target_persona: Profil persona cible
    
    Returns:
        Score entre 0 et 0.25
    """
    if not prospect_company:
        return 0.0
    
    score = 0.0
    prospect_company_lower = prospect_company.lower()
    
    # Type d'entreprise (0.1)
    company_types = target_persona.get('company_types', [])
    for company_type in company_types:
        if company_type.lower() in prospect_company_lower:
            score += 0.1
            break
    
    # Industrie (0.1)
    industries = target_persona.get('industries', [])
    for industry in industries:
        if industry.lower() in prospect_company_lower:
            score += 0.1
            break
    
    # Taille d'entreprise (0.05) - difficile à détecter automatiquement
    # On pourrait utiliser des indicateurs dans le nom ou des APIs externes
    # Pour l'instant, on donne un petit bonus si on trouve des mots-clés
    company_size = target_persona.get('company_size', '').lower()
    if company_size:
        # Patterns de taille (ex: "startup", "PME", "grande entreprise")
        size_indicators = {
            'startup': ['startup', 'scale-up', 'scaleup'],
            'pme': ['pme', 'pmi', 'sme'],
            'grande entreprise': ['group', 'groupement', 'corporation', 'corp']
        }
        for size_key, indicators in size_indicators.items():
            if size_key in company_size:
                for indicator in indicators:
                    if indicator in prospect_company_lower:
                        score += 0.05
                        break
                break
    
    return min(score, 0.25)  # Limiter à 0.25


def calculate_location_score(prospect_location: str, target_location: str) -> float:
    """
    Calcule un score de correspondance géographique (0-0.15)
    
    Args:
        prospect_location: Localisation du prospect
        target_location: Localisation cible
    
    Returns:
        Score entre 0 et 0.15
    """
    if not prospect_location or not target_location:
        return 0.0
    
    prospect_lower = prospect_location.lower()
    target_lower = target_location.lower()
    
    # Correspondance exacte
    if target_lower == prospect_lower:
        return 0.15
    
    # Correspondance partielle (région, pays)
    if target_lower in prospect_lower or prospect_lower in target_lower:
        return 0.1
    
    # Similarité
    similarity = similarity_score(prospect_lower, target_lower)
    if similarity > 0.7:
        return 0.05
    
    return 0.0


def calculate_engagement_score(reaction_type: str) -> float:
    """
    Calcule un score basé sur le type d'engagement (0-0.15)
    
    Args:
        reaction_type: Type de réaction ('LIKE', 'COMMENT', 'REPOST', etc.)
    
    Returns:
        Score entre 0 et 0.15
    """
    reaction_type_upper = (reaction_type or '').upper()
    
    if 'COMMENT' in reaction_type_upper:
        return 0.15  # Commentaire = engagement fort
    elif 'REPOST' in reaction_type_upper or 'SHARE' in reaction_type_upper:
        return 0.1   # Repost = engagement moyen
    elif 'LIKE' in reaction_type_upper or 'PRAISE' in reaction_type_upper:
        return 0.05  # Like = engagement faible
    
    return 0.0


def calculate_prospect_score(prospect_data: Dict[str, Any], company_profile: Dict[str, Any],
                            post_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calcule un score multi-critères pour un prospect (0-1.0)
    
    Args:
        prospect_data: Données du prospect (headline, reaction_type, etc.)
        company_profile: Profil de l'entreprise client
        post_context: Contexte du post (optionnel)
    
    Returns:
        Dict avec:
        - total_score: float (0-1.0)
        - job_title_score: float
        - company_score: float
        - location_score: float
        - engagement_score: float
        - post_relevance_score: float
        - details: dict avec les détails
    """
    target_persona = company_profile.get('target_persona', {})
    
    headline = prospect_data.get('headline', '') or ''
    reaction_type = prospect_data.get('reaction_type', '') or ''
    
    # Extraire les informations du headline
    prospect_company = extract_company_from_headline(headline)
    job_title = headline.split('chez')[0].split('at')[0].strip() if 'chez' in headline or 'at' in headline else headline
    
    # Scores individuels
    job_title_score = calculate_job_title_score(
        job_title,
        target_persona.get('job_titles', [])
    )
    
    company_score = calculate_company_match_score(prospect_company, target_persona)
    
    location_score = calculate_location_score(
        prospect_data.get('location', ''),
        target_persona.get('geographic_location', '')
    )
    
    engagement_score = calculate_engagement_score(reaction_type)
    
    # Score de pertinence du post (si disponible)
    post_relevance_score = 0.0
    if post_context:
        post_relevant = post_context.get('post_relevant', False)
        post_score = post_context.get('post_score', 0.0)
        if post_relevant:
            post_relevance_score = min(post_score, 0.15)
    
    # Score total
    total_score = (
        job_title_score +
        company_score +
        location_score +
        engagement_score +
        post_relevance_score
    )
    
    return {
        'total_score': min(total_score, 1.0),
        'job_title_score': job_title_score,
        'company_score': company_score,
        'location_score': location_score,
        'engagement_score': engagement_score,
        'post_relevance_score': post_relevance_score,
        'details': {
            'job_title': job_title,
            'prospect_company': prospect_company,
            'reaction_type': reaction_type
        }
    }


def calculate_prospect_score_with_ai(prospect_data: Dict[str, Any], 
                                     company_profile: Dict[str, Any],
                                     post_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calcule un score IA précis pour un prospect en utilisant toutes les informations du profil entreprise
    et en se basant uniquement sur les personas pour la qualification.
    
    Cette fonction utilise OpenAI pour analyser en profondeur chaque prospect et générer un score
    nuancé et moins restrictif que le scoring basé sur des règles.
    
    Args:
        prospect_data: Données du prospect (headline, reaction_type, location, etc.)
        company_profile: Profil complet de l'entreprise (toutes les infos)
        post_context: Contexte du post (optionnel) - dict avec post_text, post_author, etc.
    
    Returns:
        Dict avec:
        - total_score: float (0.0-1.0) - Score global de pertinence
        - reasoning: str - Explication détaillée en français
        - breakdown: dict - Scores par critère
        - strengths: List[str] - Points forts du prospect
        - weaknesses: List[str] - Points faibles
        - recommendation: str - Recommandation d'action
        - job_title_score: float (pour compatibilité)
        - company_score: float (pour compatibilité)
        - location_score: float (pour compatibilité)
        - engagement_score: float (pour compatibilité)
        - post_relevance_score: float (pour compatibilité)
        - details: dict - Détails techniques
    """
    # Si OpenAI n'est pas disponible, fallback sur scoring classique
    if not OPENAI_ENABLED or not openai_client:
        logger.debug("OpenAI non disponible, utilisation du scoring classique")
        return calculate_prospect_score(prospect_data, company_profile, post_context)
    
    try:
        # Extraire les informations du prospect
        prospect_name = prospect_data.get('reactor_name', '')
        headline = prospect_data.get('headline', '') or ''
        reaction_type = prospect_data.get('reaction_type', '') or ''
        prospect_location = prospect_data.get('location', '')
        profile_url = prospect_data.get('profile_url', '')
        
        # Extraire l'entreprise du headline
        prospect_company = extract_company_from_headline(headline)
        
        # Extraire le contexte du post si disponible
        post_text = ''
        post_author = ''
        if post_context:
            post_text = post_context.get('post_text', '') or ''
            post_author = post_context.get('post_author', '') or ''
        
        # Préparer les informations du persona
        target_persona = company_profile.get('target_persona', {})
        persona_info = {
            'job_titles': target_persona.get('job_titles', []),
            'company_types': target_persona.get('company_types', []),
            'industries': target_persona.get('industries', []),
            'company_size': target_persona.get('company_size', ''),
            'geographic_location': target_persona.get('geographic_location', ''),
            'pain_points': target_persona.get('pain_points', []),
            'characteristics': target_persona.get('characteristics', [])
        }
        
        # Préparer les informations de l'entreprise
        company_name = company_profile.get('company_name', '')
        company_description = company_profile.get('company_description', '')
        products_services = company_profile.get('products_services', [])
        website = company_profile.get('website', '')
        
        # Préparer la stratégie d'outreach
        outreach_strategy = company_profile.get('outreach_strategy', {})
        what_offers = outreach_strategy.get('what_offers', '')
        value_proposition = outreach_strategy.get('value_proposition', '')
        ideal_signals = outreach_strategy.get('ideal_signals', [])
        
        # Construire le prompt expert
        prompt = f"""Tu es un expert en qualification de prospects B2B avec une expertise approfondie en analyse de personas et scoring de prospects.

## MISSION
Analyse ce prospect LinkedIn et détermine sa pertinence en te basant UNIQUEMENT sur le persona cible défini. 
Sois NUANCÉ et MOINS RESTRICTIF : accepte les prospects avec des correspondances partielles, des profils proches, 
ou des signaux d'intérêt même si tous les critères ne sont pas parfaitement remplis.

## INFORMATIONS SUR NOTRE ENTREPRISE

**Entreprise:** {company_name}
**Description:** {company_description}
**Site web:** {website}
**Produits/Services:** {', '.join(products_services) if products_services else 'Non spécifié'}

**Ce que nous offrons:** {what_offers}
**Proposition de valeur:** {value_proposition}
**Signaux idéaux recherchés:** {', '.join(ideal_signals) if ideal_signals else 'Non spécifié'}

## PERSONA CIBLE (CRITÈRES DE QUALIFICATION)

**Titres de poste cibles:** {', '.join(persona_info['job_titles']) if persona_info['job_titles'] else 'Non spécifié'}
**Types d'entreprises cibles:** {', '.join(persona_info['company_types']) if persona_info['company_types'] else 'Non spécifié'}
**Industries cibles:** {', '.join(persona_info['industries']) if persona_info['industries'] else 'Non spécifié'}
**Taille d'entreprise cible:** {persona_info['company_size'] or 'Non spécifié'}
**Localisation géographique cible:** {persona_info['geographic_location'] or 'Non spécifié'}
**Pain points cibles:** {', '.join(persona_info['pain_points']) if persona_info['pain_points'] else 'Non spécifié'}
**Caractéristiques recherchées:** {', '.join(persona_info['characteristics']) if persona_info['characteristics'] else 'Non spécifié'}

## PROFIL DU PROSPECT À ANALYSER

**Nom:** {prospect_name}
**Headline LinkedIn:** {headline}
**Entreprise détectée:** {prospect_company or 'Non détectée'}
**Localisation:** {prospect_location or 'Non spécifiée'}
**Type de réaction:** {reaction_type}
**URL profil:** {profile_url}

## CONTEXTE DU POST (si disponible)

**Auteur du post:** {post_author or 'Non spécifié'}
**Texte du post:** {post_text[:800] if post_text else 'Non disponible'}

## INSTRUCTIONS D'ANALYSE

1. **Analyse le prospect vs le persona** : Compare chaque élément du prospect avec les critères du persona
2. **Sois nuancé** : Un prospect peut être pertinent même avec des correspondances partielles
   - Exemple: Si le persona cherche "CMO" mais le prospect est "Head of Marketing", c'est un bon match
   - Exemple: Si le persona cherche "SaaS" mais le prospect est dans "Tech", c'est un match partiel valable
3. **Pondération des critères** :
   - Job title: 30% (très important)
   - Company/Industry: 25% (important)
   - Pain points/Characteristics: 20% (important pour l'alignement)
   - Location: 15% (modéré, peut être flexible)
   - Engagement: 10% (bonus, commentaire > repost > like)
4. **Signaux positifs à valoriser** :
   - Titre proche du persona même si pas exact
   - Industrie/secteur connexe
   - Pain points alignés
   - Engagement fort (commentaire)
   - Localisation dans la zone cible
5. **Ne sois pas trop restrictif** : Un score de 0.5-0.6 peut être acceptable si plusieurs critères partiels sont remplis

## FORMAT DE RÉPONSE REQUIS

Réponds UNIQUEMENT avec un JSON valide (sans markdown, sans code blocks):

{{
    "total_score": 0.0 à 1.0,
    "reasoning": "Explication détaillée en français (3-5 phrases) expliquant pourquoi ce score, quels critères correspondent, lesquels ne correspondent pas, et pourquoi le prospect est pertinent ou non",
    "breakdown": {{
        "job_title_match": 0.0 à 1.0,
        "company_match": 0.0 à 1.0,
        "location_match": 0.0 à 1.0,
        "engagement_level": 0.0 à 1.0,
        "persona_alignment": 0.0 à 1.0,
        "pain_points_match": 0.0 à 1.0,
        "characteristics_match": 0.0 à 1.0
    }},
    "strengths": ["point fort 1", "point fort 2", ...],
    "weaknesses": ["point faible 1", "point faible 2", ...],
    "recommendation": "Contact prioritaire" | "Contact recommandé" | "Contact possible" | "Non recommandé"
}}

## ÉCHELLE DE SCORING

- **0.8-1.0** : Excellent match, correspond parfaitement au persona, contact prioritaire
- **0.6-0.8** : Bon match, correspond globalement au persona, contact recommandé
- **0.4-0.6** : Match partiel, certaines correspondances, contact possible selon contexte
- **0.2-0.4** : Faible match, peu de correspondances, à évaluer manuellement
- **0.0-0.2** : Très faible match, ne correspond pas au persona, non recommandé

IMPORTANT: Sois généreux dans le scoring. Un prospect avec 2-3 critères partiels peut avoir un score de 0.5-0.6."""
        
        # Appel à OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "Tu es un expert en qualification de prospects B2B. Tu analyses les prospects en te basant uniquement sur les personas définis. Tu es nuancé et moins restrictif dans ton scoring. Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans code blocks, directement le JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )
        
        content = response.choices[0].message.content.strip()
        
        # Nettoyer le contenu (enlever markdown si présent)
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parser le JSON
        result = json.loads(content)
        
        # Extraire les valeurs
        total_score = float(result.get('total_score', 0.0))
        reasoning = result.get('reasoning', '')
        breakdown = result.get('breakdown', {})
        strengths = result.get('strengths', [])
        weaknesses = result.get('weaknesses', [])
        recommendation = result.get('recommendation', '')
        
        # Construire la réponse compatible avec l'ancien format
        return {
            'total_score': min(max(total_score, 0.0), 1.0),  # S'assurer que c'est entre 0 et 1
            'reasoning': reasoning,
            'breakdown': breakdown,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendation': recommendation,
            # Compatibilité avec l'ancien format
            'job_title_score': breakdown.get('job_title_match', 0.0) * 0.3,
            'company_score': breakdown.get('company_match', 0.0) * 0.25,
            'location_score': breakdown.get('location_match', 0.0) * 0.15,
            'engagement_score': breakdown.get('engagement_level', 0.0) * 0.1,
            'post_relevance_score': 0.0,  # Peut être enrichi plus tard
            'details': {
                'job_title': headline.split('chez')[0].split('at')[0].strip() if 'chez' in headline or 'at' in headline else headline,
                'prospect_company': prospect_company,
                'reaction_type': reaction_type,
                'location': prospect_location
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON pour prospect {prospect_data.get('reactor_name', 'Unknown')}: {e}")
        logger.debug(f"Contenu reçu: {content[:500] if 'content' in locals() else 'N/A'}")
        # Fallback sur scoring classique
        return calculate_prospect_score(prospect_data, company_profile, post_context)
    except Exception as e:
        logger.error(f"Erreur lors du scoring IA pour prospect {prospect_data.get('reactor_name', 'Unknown')}: {e}", exc_info=True)
        # Fallback sur scoring classique
        return calculate_prospect_score(prospect_data, company_profile, post_context)


def recalculate_prospect_scoring(client_id: int, reactor_urn: str, post_url: str,
                                  company_profile: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Recalcule le scoring d'un prospect spécifique et met à jour la base de données
    
    Args:
        client_id: ID du client
        reactor_urn: URN du prospect (reactor_urn)
        post_url: URL du post
        company_profile: Profil entreprise (optionnel, sera chargé si non fourni)
    
    Returns:
        Dict avec le nouveau scoring ou None en cas d'erreur
    """
    from utils.database import get_connection, get_client_profile_as_dict
    
    try:
        # Charger le profil entreprise si non fourni
        if not company_profile:
            company_profile = get_client_profile_as_dict(client_id)
            if not company_profile:
                logger.error(f"Profil entreprise non trouvé pour client {client_id}")
                return None
        
        # Récupérer les données du prospect depuis la base
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM reactions
                WHERE client_id = ? AND reactor_urn = ? AND post_url = ?
            """, (client_id, reactor_urn, post_url))
            row = cursor.fetchone()
            
            if not row:
                logger.error(f"Prospect non trouvé: {reactor_urn} / {post_url}")
                return None
            
            prospect_data = dict(row)
        
        # Préparer les données pour le scoring
        prospect_for_scoring = {
            'reactor_name': prospect_data.get('reactor_name', ''),
            'headline': prospect_data.get('headline', ''),
            'reaction_type': prospect_data.get('reaction_type', ''),
            'location': '',  # Pas stocké dans la DB actuellement
            'profile_url': prospect_data.get('profile_url', ''),
            'reactor_urn': reactor_urn
        }
        
        # Préparer le contexte du post
        post_context = {
            'post_text': '',  # Pas stocké dans la DB actuellement
            'post_author': prospect_data.get('competitor_name', '')
        }
        
        # Calculer le nouveau score avec IA
        scoring_result = calculate_prospect_score_with_ai(
            prospect_for_scoring,
            company_profile,
            post_context=post_context
        )
        
        # Mettre à jour dans la base de données
        reaction_data = {
            'company_name': prospect_data.get('competitor_name', ''),
            'post_url': post_url,
            'post_date': prospect_data.get('post_date', ''),
            'reactor_name': prospect_data.get('reactor_name', ''),
            'reactor_urn': reactor_urn,
            'profile_url': prospect_data.get('profile_url', ''),
            'reaction_type': prospect_data.get('reaction_type', ''),
            'headline': prospect_data.get('headline', ''),
            'profile_picture_url': prospect_data.get('profile_picture_url', ''),
            'post_relevant': prospect_data.get('post_relevant', False),
            'prospect_relevant': scoring_result.get('total_score', 0.0) >= 0.6,  # Seuil par défaut
            'relevance_score': scoring_result.get('total_score', 0.0),
            'relevance_reasoning': json.dumps(scoring_result, ensure_ascii=False),
            'personalized_message': prospect_data.get('personalized_message', '')
        }
        
        from utils.database import save_reaction
        save_reaction(client_id, reaction_data)
        
        logger.info(f"Scoring recalculé pour prospect {prospect_data.get('reactor_name', 'Unknown')}: {scoring_result.get('total_score', 0.0):.2f}")
        
        return scoring_result
        
    except Exception as e:
        logger.error(f"Erreur lors du recalcul du scoring pour prospect {reactor_urn}: {e}", exc_info=True)
        return None


def filter_competitors_from_reactions(reactions: List[Dict[str, Any]], 
                                     client_id: int,
                                     competitors_list: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Filtre les concurrents d'une liste de réactions
    
    Args:
        reactions: Liste des réactions à filtrer
        client_id: ID du client
        competitors_list: Liste des concurrents
    
    Returns:
        Tuple (filtered_reactions, filtered_count)
    """
    filtered_reactions = []
    filtered_count = 0
    
    logger.info(f"Analyse de {len(reactions)} réaction(s) pour détecter les concurrents...")
    
    for idx, reaction in enumerate(reactions, 1):
        # Vérifier si c'est un concurrent
        is_competitor, matched_competitor = check_if_competitor(
            reaction,
            client_id,
            competitors_list
        )
        
        if is_competitor:
            filtered_count += 1
            logger.debug(f"  → Prospect filtré (concurrent): {reaction.get('reactor_name')} - {matched_competitor}")
            continue
        
        filtered_reactions.append(reaction)
        
        # Log tous les 50 pour le suivi
        if idx % 50 == 0:
            logger.info(f"  → {idx}/{len(reactions)} analysé(s), {filtered_count} filtré(s)")
    
    return filtered_reactions, filtered_count


def analyze_prospect_match(prospect_data: Dict[str, Any], target_persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse détaillée de correspondance entre un prospect et le persona cible
    
    Args:
        prospect_data: Données du prospect
        target_persona: Persona cible
    
    Returns:
        Dict avec analyse détaillée
    """
    headline = prospect_data.get('headline', '') or ''
    prospect_company = extract_company_from_headline(headline)
    
    matches = {
        'job_title_match': False,
        'company_type_match': False,
        'industry_match': False,
        'location_match': False,
        'matched_criteria': []
    }
    
    # Job title
    target_job_titles = target_persona.get('job_titles', [])
    if calculate_job_title_score(headline, target_job_titles) > 0:
        matches['job_title_match'] = True
        matches['matched_criteria'].append('job_title')
    
    # Company type
    company_types = target_persona.get('company_types', [])
    if prospect_company:
        for ct in company_types:
            if ct.lower() in prospect_company.lower():
                matches['company_type_match'] = True
                matches['matched_criteria'].append('company_type')
                break
    
    # Industry
    industries = target_persona.get('industries', [])
    if prospect_company:
        for ind in industries:
            if ind.lower() in prospect_company.lower():
                matches['industry_match'] = True
                matches['matched_criteria'].append('industry')
                break
    
    # Location
    target_location = target_persona.get('geographic_location', '')
    prospect_location = prospect_data.get('location', '')
    if target_location and prospect_location:
        if calculate_location_score(prospect_location, target_location) > 0:
            matches['location_match'] = True
            matches['matched_criteria'].append('location')
    
    return matches
