"""
Script pour exécuter automatiquement les radars LinkedIn configurés
Permet de lancer tous les radars activés pour un client donné
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent))

from utils.database import (
    get_client, get_enabled_radars, update_radar_last_run,
    save_reaction, init_db
)
from utils.radar_manager import process_radar

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_scraper_radars.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def process_all_radars(client_id: int) -> Dict[str, Any]:
    """
    Traite tous les radars activés pour un client
    
    Args:
        client_id: ID du client
    
    Returns:
        Dict contenant les statistiques d'exécution
    """
    client = get_client(client_id)
    if not client:
        logger.error(f"Client {client_id} introuvable")
        return {
            'success': False,
            'message': f"Client {client_id} introuvable"
        }
    
    logger.info("=" * 60)
    logger.info(f"Exécution des radars pour: {client['name']}")
    logger.info("=" * 60)
    
    # Récupérer tous les radars activés
    radars = get_enabled_radars(client_id)
    
    if not radars:
        logger.warning(f"Aucun radar activé pour {client['name']}")
        return {
            'success': True,
            'total_radars': 0,
            'processed_radars': 0,
            'total_reactions': 0,
            'message': "Aucun radar activé"
        }
    
    logger.info(f"{len(radars)} radar(s) activé(s) à traiter")
    
    stats = {
        'total_radars': len(radars),
        'processed_radars': 0,
        'successful_radars': 0,
        'failed_radars': 0,
        'total_reactions': 0,
        'errors': []
    }
    
    # Traiter chaque radar
    for radar in radars:
        radar_name = radar.get('name', 'Unknown')
        radar_type = radar.get('radar_type', 'Unknown')
        radar_id = radar.get('id')
        
        logger.info("-" * 60)
        logger.info(f"Traitement du radar: {radar_name} (Type: {radar_type})")
        logger.info("-" * 60)
        
        try:
            # Traiter le radar
            reactions = process_radar(radar)
            
            if reactions:
                # Sauvegarder les réactions
                saved_count = 0
                for reaction in reactions:
                    try:
                        # Adapter les données pour save_reaction
                        reaction_data = {
                            'company_name': reaction.get('company_name') or reaction.get('keyword') or '',
                            'post_url': reaction.get('post_url', ''),
                            'post_date': reaction.get('post_date', ''),
                            'reactor_name': reaction.get('reactor_name', ''),
                            'reactor_urn': reaction.get('reactor_urn', ''),
                            'profile_url': reaction.get('profile_url', ''),
                            'reaction_type': reaction.get('reaction_type', ''),
                            'headline': reaction.get('headline', ''),
                            'profile_picture_url': reaction.get('profile_picture_url', ''),
                            'post_relevant': False,
                            'prospect_relevant': False,
                            'relevance_score': 0.0,
                            'relevance_reasoning': '',
                            'personalized_message': ''
                        }
                        save_reaction(client_id, reaction_data)
                        saved_count += 1
                    except Exception as e:
                        error_msg = f"Erreur lors de la sauvegarde d'une réaction: {e}"
                        logger.warning(error_msg)
                        stats['errors'].append(error_msg)
                
                # Mettre à jour la date de dernière exécution
                update_radar_last_run(radar_id)
                
                stats['processed_radars'] += 1
                stats['successful_radars'] += 1
                stats['total_reactions'] += saved_count
                
                logger.info(f"✓ Radar '{radar_name}' traité avec succès")
                logger.info(f"  {saved_count} réaction(s) collectée(s)")
            else:
                # Mettre à jour quand même la date de dernière exécution
                update_radar_last_run(radar_id)
                stats['processed_radars'] += 1
                stats['successful_radars'] += 1
                logger.info(f"✓ Radar '{radar_name}' traité (aucune réaction trouvée)")
                
        except Exception as e:
            error_msg = f"Erreur lors du traitement du radar '{radar_name}': {e}"
            logger.error(error_msg, exc_info=True)
            stats['processed_radars'] += 1
            stats['failed_radars'] += 1
            stats['errors'].append(error_msg)
    
    # Résumé final
    logger.info("=" * 60)
    logger.info("Résumé de l'exécution:")
    logger.info(f"  Total radars: {stats['total_radars']}")
    logger.info(f"  Radars traités: {stats['processed_radars']}")
    logger.info(f"  Succès: {stats['successful_radars']}")
    logger.info(f"  Échecs: {stats['failed_radars']}")
    logger.info(f"  Total réactions: {stats['total_reactions']}")
    logger.info("=" * 60)
    
    stats['success'] = True
    return stats


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Exécute les radars LinkedIn configurés')
    parser.add_argument('--client-id', type=int, default=1,
                       help='ID du client (défaut: 1)')
    parser.add_argument('--all-clients', action='store_true',
                       help='Exécute les radars pour tous les clients')
    
    args = parser.parse_args()
    
    # Initialiser la base de données
    init_db()
    
    if args.all_clients:
        # Traiter tous les clients
        from utils.database import get_all_clients
        clients = get_all_clients()
        
        for client in clients:
            logger.info(f"\n{'='*60}\n")
            process_all_radars(client['id'])
    else:
        # Traiter un seul client
        process_all_radars(args.client_id)


if __name__ == "__main__":
    main()
