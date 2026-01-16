"""
Module de scheduling automatique pour les radars LinkedIn
Utilise APScheduler pour exécuter automatiquement les radars selon leur configuration
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))

from utils.database import get_scheduled_radars, get_radar, update_radar_last_run
from utils.radar_manager import process_radar_with_scoring
from utils.database import get_client, get_client_profile_as_dict, get_competitors

logger = logging.getLogger(__name__)

# Scheduler global
scheduler = None
job_ids = {}  # Mapping radar_id -> job_id


def get_scheduler() -> Optional[Any]:
    """Retourne le scheduler global ou en crée un nouveau"""
    global scheduler
    
    if not APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler non disponible. Installez-le avec: pip install APScheduler")
        return None
    
    if scheduler is None:
        scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC'
        )
    
    return scheduler


def calculate_next_run_time(schedule_type: str, schedule_interval: int) -> datetime:
    """
    Calcule la prochaine heure d'exécution
    
    Args:
        schedule_type: Type de planification ('minutes', 'hours', 'days')
        schedule_interval: Intervalle en minutes/heures/jours
    
    Returns:
        datetime de la prochaine exécution
    """
    now = datetime.now()
    
    if schedule_type == 'minutes':
        return now + timedelta(minutes=schedule_interval)
    elif schedule_type == 'hours':
        return now + timedelta(hours=schedule_interval)
    elif schedule_type == 'days':
        return now + timedelta(days=schedule_interval)
    else:
        return now


def schedule_radar(radar_id: int) -> bool:
    """
    Planifie un radar selon sa configuration
    
    Args:
        radar_id: ID du radar
    
    Returns:
        True si planifié avec succès, False sinon
    """
    global job_ids
    
    scheduler_obj = get_scheduler()
    if not scheduler_obj:
        return False
    
    radar = get_radar(radar_id)
    if not radar:
        logger.error(f"Radar {radar_id} introuvable")
        return False
    
    schedule_type = radar.get('schedule_type', 'manual')
    schedule_interval = radar.get('schedule_interval', 0)
    
    if schedule_type == 'manual' or schedule_interval <= 0:
        logger.info(f"Radar {radar_id} n'a pas de scheduling configuré")
        return False
    
    # Retirer le job existant s'il existe
    unschedule_radar(radar_id)
    
    # Créer le trigger selon le type
    if schedule_type == 'minutes':
        trigger = IntervalTrigger(minutes=schedule_interval)
    elif schedule_type == 'hours':
        trigger = IntervalTrigger(hours=schedule_interval)
    elif schedule_type == 'days':
        trigger = IntervalTrigger(days=schedule_interval)
    else:
        logger.error(f"Type de scheduling invalide: {schedule_type}")
        return False
    
    # Créer le job
    job_id = f"radar_{radar_id}"
    scheduler_obj.add_job(
        run_radar_job,
        trigger=trigger,
        args=[radar_id],
        id=job_id,
        replace_existing=True,
        max_instances=1
    )
    
    job_ids[radar_id] = job_id
    
    next_run = calculate_next_run_time(schedule_type, schedule_interval)
    logger.info(f"Radar {radar_id} planifié: {schedule_type}={schedule_interval}, prochaine exécution: {next_run}")
    
    return True


def unschedule_radar(radar_id: int) -> bool:
    """
    Désactive la planification d'un radar
    
    Args:
        radar_id: ID du radar
    
    Returns:
        True si désactivé avec succès, False sinon
    """
    global job_ids
    
    scheduler_obj = get_scheduler()
    if not scheduler_obj:
        return False
    
    job_id = job_ids.get(radar_id)
    if job_id:
        try:
            scheduler_obj.remove_job(job_id)
            del job_ids[radar_id]
            logger.info(f"Planification du radar {radar_id} désactivée")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation du radar {radar_id}: {e}")
            return False
    
    return False


def run_radar_job(radar_id: int):
    """
    Fonction exécutée par le scheduler pour un radar
    
    Args:
        radar_id: ID du radar
    """
    logger.info(f"Exécution automatique du radar {radar_id}")
    
    try:
        radar = get_radar(radar_id)
        if not radar:
            logger.error(f"Radar {radar_id} introuvable lors de l'exécution")
            return
        
        if not radar.get('enabled', False):
            logger.info(f"Radar {radar_id} désactivé, exécution annulée")
            return
        
        # Traiter le radar
        client_id = radar.get('client_id')
        client = get_client(client_id)
        company_profile = get_client_profile_as_dict(client_id)
        competitors = get_competitors(client_id)
        
        # Exécuter le radar avec scoring
        reactions = process_radar_with_scoring(
            radar,
            client_id,
            company_profile,
            competitors,
            min_score_threshold=radar.get('min_score_threshold', 0.6),
            filter_competitors=radar.get('filter_competitors', True)
        )
        
        # Mettre à jour la date de dernière exécution
        update_radar_last_run(radar_id, scheduled=True)
        
        logger.info(f"Radar {radar_id} exécuté avec succès: {len(reactions)} réaction(s) collectée(s)")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution automatique du radar {radar_id}: {e}", exc_info=True)


def schedule_all_radars(client_id: int = None):
    """
    Planifie tous les radars avec scheduling activé
    
    Args:
        client_id: ID du client (optionnel, tous les clients si None)
    """
    scheduler_obj = get_scheduler()
    if not scheduler_obj:
        logger.error("Scheduler non disponible")
        return
    
    radars = get_scheduled_radars(client_id)
    logger.info(f"Planification de {len(radars)} radar(s)")
    
    scheduled_count = 0
    for radar in radars:
        if schedule_radar(radar['id']):
            scheduled_count += 1
    
    logger.info(f"{scheduled_count} radar(s) planifié(s) avec succès")


def unschedule_all_radars():
    """Désactive la planification de tous les radars"""
    global job_ids
    
    scheduler_obj = get_scheduler()
    if not scheduler_obj:
        return
    
    radar_ids = list(job_ids.keys())
    for radar_id in radar_ids:
        unschedule_radar(radar_id)


def start_scheduler():
    """Démarre le scheduler"""
    scheduler_obj = get_scheduler()
    if not scheduler_obj:
        logger.error("Scheduler non disponible")
        return False
    
    if not scheduler_obj.running:
        scheduler_obj.start()
        logger.info("Scheduler démarré")
        return True
    else:
        logger.info("Scheduler déjà en cours d'exécution")
        return False


def stop_scheduler():
    """Arrête le scheduler"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler arrêté")
        return True
    return False


def get_next_run_time(radar_id: int) -> Optional[datetime]:
    """
    Affiche la prochaine exécution d'un radar
    
    Args:
        radar_id: ID du radar
    
    Returns:
        datetime de la prochaine exécution ou None
    """
    scheduler_obj = get_scheduler()
    if not scheduler_obj:
        return None
    
    job_id = job_ids.get(radar_id)
    if not job_id:
        return None
    
    try:
        job = scheduler_obj.get_job(job_id)
        if job:
            return job.next_run_time
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la prochaine exécution: {e}")
    
    return None


def run_scheduled_radars():
    """
    Exécute manuellement tous les radars planifiés qui sont dus
    Utile pour tester ou pour une exécution manuelle
    """
    radars = get_scheduled_radars()
    
    for radar in radars:
        schedule_type = radar.get('schedule_type', 'manual')
        schedule_interval = radar.get('schedule_interval', 0)
        last_scheduled_run = radar.get('last_scheduled_run')
        
        if schedule_type == 'manual' or schedule_interval <= 0:
            continue
        
        # Vérifier si le radar est dû
        if last_scheduled_run:
            last_run = datetime.fromisoformat(last_scheduled_run.replace('Z', '+00:00'))
            next_run = calculate_next_run_time(schedule_type, schedule_interval)
            if datetime.now() < next_run:
                continue
        
        # Exécuter le radar
        run_radar_job(radar['id'])


def get_scheduler_status() -> Dict[str, Any]:
    """
    Retourne le statut du scheduler
    
    Returns:
        Dict avec informations sur le scheduler
    """
    scheduler_obj = get_scheduler()
    
    if not scheduler_obj:
        return {
            'available': False,
            'running': False,
            'jobs_count': 0
        }
    
    return {
        'available': True,
        'running': scheduler_obj.running if scheduler_obj else False,
        'jobs_count': len(scheduler_obj.get_jobs()) if scheduler_obj else 0,
        'scheduled_radars': list(job_ids.keys())
    }
