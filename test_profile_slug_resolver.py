"""
Script de test pour résoudre les slugs LinkedIn à partir d'IDs/URNs
Teste différentes méthodes: redirections HTTP, scraping, API
"""
import sys
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le chemin du projet
sys.path.append(str(Path(__file__).parent))

def test_redirect_method(profile_url: str) -> dict:
    """
    Teste la méthode de résolution via redirections HTTP et scraping
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: Résolution via redirections pour: {profile_url}")
    logger.info(f"{'='*60}")
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # S'assurer que c'est une URL complète
        if not profile_url.startswith('http'):
            if '/in/' in profile_url:
                profile_url = f"https://www.{profile_url.lstrip('/')}"
            else:
                profile_url = f"https://www.linkedin.com/in/{profile_url}"
        
        logger.info(f"URL complète: {profile_url}")
        
        # Headers avancés pour bypasser la protection anti-bot
        import random
        import time
        
        # User-Agents variés pour éviter la détection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/',
        }
        
        # Créer une session pour maintenir les cookies
        session = requests.Session()
        session.headers.update(headers)
        
        # Délai aléatoire pour éviter la détection
        time.sleep(random.uniform(1, 3))
        
        # Suivre les redirections avec la session
        logger.info("Envoi de la requête HTTP avec headers anti-bot...")
        response = session.get(profile_url, timeout=15, allow_redirects=True)
        
        result = {
            'method': 'redirect',
            'status_code': response.status_code,
            'final_url': response.url,
            'slug_found': False,
            'slug': None,
            'methods_tried': []
        }
        
        # Gérer les erreurs 999 (LinkedIn anti-bot)
        if response.status_code == 999:
            logger.warning("✗ Erreur 999 détectée (protection anti-bot LinkedIn)")
            logger.info("Tentative avec une approche différente...")
            
            # Essayer avec selenium si disponible (plus réaliste)
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                logger.info("Utilisation de Selenium pour bypasser la protection...")
                
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                try:
                    driver.get(profile_url)
                    time.sleep(3)  # Attendre le chargement
                    
                    final_url = driver.current_url
                    logger.info(f"URL finale avec Selenium: {final_url}")
                    
                    if '/in/' in final_url:
                        final_slug = final_url.split('/in/')[-1].split('/')[0].split('?')[0]
                        if not final_slug.startswith('ACo') and len(final_slug) > 3:
                            result['slug_found'] = True
                            result['slug'] = final_url.split('?')[0].rstrip('/')
                            result['method_used'] = 'selenium'
                            logger.info(f"✓ Slug trouvé via Selenium: {result['slug']}")
                            driver.quit()
                            return result
                    
                    # Scraper avec Selenium
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    
                    # Chercher dans og:url
                    og_url = soup.find('meta', property='og:url')
                    if og_url and og_url.get('content'):
                        og_content = og_url.get('content')
                        if '/in/' in og_content:
                            slug = og_content.split('/in/')[-1].split('/')[0].split('?')[0]
                            if not slug.startswith('ACo') and len(slug) > 3:
                                result['slug_found'] = True
                                result['slug'] = og_content.split('?')[0].rstrip('/')
                                result['method_used'] = 'selenium_og'
                                logger.info(f"✓ Slug trouvé via Selenium + og:url: {result['slug']}")
                                driver.quit()
                                return result
                    
                    driver.quit()
                except Exception as e:
                    logger.error(f"Erreur Selenium: {e}")
                    try:
                        driver.quit()
                    except:
                        pass
                        
            except ImportError:
                logger.warning("Selenium non installé. Installez avec: pip install selenium")
                logger.warning("Ou utilisez une autre méthode (API, etc.)")
            except Exception as e:
                logger.error(f"Erreur lors de l'utilisation de Selenium: {e}")
            
            result['error'] = "HTTP 999 - Protection anti-bot LinkedIn"
            return result
        
        if response.status_code == 200:
            # Méthode 1: Vérifier l'URL finale après redirection
            final_url = response.url
            logger.info(f"URL finale après redirection: {final_url}")
            result['methods_tried'].append('redirect_final_url')
            
            if '/in/' in final_url:
                final_slug = final_url.split('/in/')[-1].split('/')[0].split('?')[0]
                logger.info(f"Slug extrait de l'URL finale: {final_slug}")
                
                # Si ce n'est plus un ID (ACo), c'est probablement le vrai slug
                if not final_slug.startswith('ACo') and len(final_slug) > 3:
                    result['slug_found'] = True
                    result['slug'] = final_url.split('?')[0].rstrip('/')
                    logger.info(f"✓ Slug trouvé via redirection: {result['slug']}")
                    return result
            
            # Méthode 2: Scraper les meta tags
            logger.info("Tentative de scraping des meta tags...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Chercher dans og:url
            og_url = soup.find('meta', property='og:url')
            if og_url and og_url.get('content'):
                og_content = og_url.get('content')
                logger.info(f"og:url trouvé: {og_content}")
                result['methods_tried'].append('og_url')
                
                if '/in/' in og_content:
                    slug = og_content.split('/in/')[-1].split('/')[0].split('?')[0]
                    if not slug.startswith('ACo') and len(slug) > 3:
                        result['slug_found'] = True
                        result['slug'] = og_content.split('?')[0].rstrip('/')
                        logger.info(f"✓ Slug trouvé via og:url: {result['slug']}")
                        return result
            
            # Chercher dans canonical
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                canonical_href = canonical.get('href')
                logger.info(f"canonical trouvé: {canonical_href}")
                result['methods_tried'].append('canonical')
                
                if '/in/' in canonical_href:
                    slug = canonical_href.split('/in/')[-1].split('/')[0].split('?')[0]
                    if not slug.startswith('ACo') and len(slug) > 3:
                        result['slug_found'] = True
                        result['slug'] = canonical_href.split('?')[0].rstrip('/')
                        logger.info(f"✓ Slug trouvé via canonical: {result['slug']}")
                        return result
            
            logger.warning("✗ Aucun slug valide trouvé via les méthodes de scraping")
        else:
            logger.warning(f"✗ Erreur HTTP: {response.status_code}")
            result['error'] = f"HTTP {response.status_code}"
        
        return result
        
    except ImportError as e:
        logger.error(f"✗ Bibliothèque manquante: {e}")
        logger.error("Installez avec: pip install beautifulsoup4 requests")
        return {'error': 'missing_dependencies', 'method': 'redirect'}
    except Exception as e:
        logger.error(f"✗ Erreur: {e}")
        return {'error': str(e), 'method': 'redirect'}


def test_api_method(profile_url: str) -> dict:
    """
    Teste la méthode de résolution via API (coûteux)
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: Résolution via API pour: {profile_url}")
    logger.info(f"{'='*60}")
    
    try:
        from utils.radar_manager import extract_username_from_url, API_BASE_URL, API_KEY, API_HOST, make_api_request_with_retry
        
        # Extraire l'ID
        current_id = extract_username_from_url(profile_url)
        if not current_id:
            return {'error': 'cannot_extract_id', 'method': 'api'}
        
        logger.info(f"ID extrait: {current_id}")
        
        # Utiliser l'API
        url = f"{API_BASE_URL}/profile/detail"
        headers = {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST
        }
        params = {"username": current_id}
        
        logger.warning("⚠️ Appel API coûteux en cours...")
        response = make_api_request_with_retry(url, headers, params)
        
        result = {
            'method': 'api',
            'api_called': True,
            'slug_found': False,
            'slug': None
        }
        
        if response and response.status_code == 200:
            data = response.json()
            profile_data = data.get('data', {})
            
            real_slug = (
                profile_data.get('profile_url') or
                profile_data.get('username') or
                profile_data.get('public_identifier')
            )
            
            if real_slug:
                if real_slug.startswith('http'):
                    result['slug'] = real_slug.strip().rstrip('/')
                else:
                    result['slug'] = f"https://www.linkedin.com/in/{real_slug}".strip().rstrip('/')
                result['slug_found'] = True
                logger.info(f"✓ Slug trouvé via API: {result['slug']}")
            else:
                logger.warning("✗ Aucun slug dans la réponse API")
        else:
            logger.warning(f"✗ Erreur API: {response.status_code if response else 'No response'}")
            result['error'] = f"API error: {response.status_code if response else 'No response'}"
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Erreur: {e}")
        return {'error': str(e), 'method': 'api'}


def main():
    """
    Fonction principale pour tester différentes URLs
    """
    print("\n" + "="*60)
    print("TESTEUR DE RÉSOLUTION DE SLUGS LINKEDIN")
    print("="*60)
    
    # URLs de test (remplacez par vos vraies URLs)
    test_urls = [
        # Exemple avec ID (à remplacer)
        "https://www.linkedin.com/in/ACoAAA1pe-0BshJ1-fAY_L-H0NSApuQHswGi0Lo",
        # Exemple avec slug (devrait fonctionner)
        # "https://www.linkedin.com/in/john-doe",
    ]
    
    # Ou demander à l'utilisateur
    if len(sys.argv) > 1:
        test_urls = [sys.argv[1]]
    else:
        user_input = input("\nEntrez une URL LinkedIn à tester (ou appuyez sur Entrée pour utiliser les exemples): ").strip()
        if user_input:
            test_urls = [user_input]
    
    for url in test_urls:
        print(f"\n{'#'*60}")
        print(f"TEST POUR: {url}")
        print(f"{'#'*60}")
        
        # Test 1: Méthode gratuite (redirections)
        result_redirect = test_redirect_method(url)
        print(f"\nRésultat méthode redirection:")
        print(f"  - Slug trouvé: {result_redirect.get('slug_found', False)}")
        if result_redirect.get('slug'):
            print(f"  - Slug: {result_redirect['slug']}")
        if result_redirect.get('error'):
            print(f"  - Erreur: {result_redirect['error']}")
        
        # Test 2: Méthode API (coûteux - demander confirmation seulement si interactif)
        try:
            use_api = input("\nVoulez-vous tester la méthode API (coûteux) ? (o/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            # Mode non-interactif (script lancé avec argument)
            use_api = 'n'
            print("\nMode non-interactif: test API ignoré")
        
        if use_api == 'o':
            result_api = test_api_method(url)
            print(f"\nRésultat méthode API:")
            print(f"  - Slug trouvé: {result_api.get('slug_found', False)}")
            if result_api.get('slug'):
                print(f"  - Slug: {result_api['slug']}")
            if result_api.get('error'):
                print(f"  - Erreur: {result_api['error']}")
        
        print("\n" + "-"*60)


if __name__ == "__main__":
    main()
