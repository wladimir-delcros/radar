"""
Script pour exécuter automatiquement les radars LinkedIn planifiés
Utilise APScheduler pour exécuter les radars selon leur configuration de scheduling
"""
import logging
import signal
import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.append(str(Path(__file__).parent))

from utils.database import init_db, get_client
from utils.radar_scheduler import (
    start_scheduler, stop_scheduler, schedule_all_radars,
    get_scheduler_status
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_scraper_radars_scheduled.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêter proprement le scheduler"""
    logger.info("Signal d'arrêt reçu, arrêt du scheduler...")
    stop_scheduler()
    sys.exit(0)


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Exécute automatiquement les radars LinkedIn planifiés'
    )
    parser.add_argument(
        '--client-id',
        type=int,
        default=None,
        help='ID du client (tous les clients si non spécifié)'
    )
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Exécute une fois tous les radars planifiés puis quitte'
    )
    
    args = parser.parse_args()
    
    # Initialiser la base de données
    init_db()
    
    # Enregistrer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("Démarrage du scheduler de radars LinkedIn")
    logger.info("=" * 60)
    
    # Planifier tous les radars
    if args.client_id:
        client = get_client(args.client_id)
        if not client:
            logger.error(f"Client {args.client_id} introuvable")
            return
        logger.info(f"Planification des radars pour le client: {client['name']}")
        schedule_all_radars(args.client_id)
    else:
        logger.info("Planification de tous les radars")
        schedule_all_radars()
    
    # Vérifier le statut
    status = get_scheduler_status()
    logger.info(f"Statut du scheduler: {status}")
    
    if status['jobs_count'] == 0:
        logger.warning("Aucun radar planifié trouvé. Vérifiez la configuration des radars.")
        return
    
    if args.run_once:
        # Mode exécution unique
        logger.info("Mode exécution unique activé")
        from utils.radar_scheduler import run_scheduled_radars
        run_scheduled_radars()
        logger.info("Exécution terminée")
    else:
        # Mode continu avec scheduler
        # Démarrer le scheduler
        if start_scheduler():
            logger.info("Scheduler démarré avec succès")
            logger.info("Appuyez sur Ctrl+C pour arrêter")
            
            try:
                # Maintenir le script en vie
                while True:
                    time.sleep(1)
                    # Vérifier périodiquement que le scheduler tourne toujours
                    status = get_scheduler_status()
                    if not status.get('running', False):
                        logger.error("Le scheduler s'est arrêté de manière inattendue")
                        break
            except KeyboardInterrupt:
                logger.info("Arrêt demandé par l'utilisateur")
            finally:
                stop_scheduler()
                logger.info("Scheduler arrêté")
        else:
            logger.error("Impossible de démarrer le scheduler")


if __name__ == "__main__":
    main()
