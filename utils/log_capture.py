"""
Module pour capturer les logs en temps réel dans Streamlit
"""
import logging
import sys
from typing import List
from io import StringIO


class StreamlitLogHandler(logging.Handler):
    """Handler de logging qui accumule les logs dans une liste"""
    
    def __init__(self):
        super().__init__()
        self.logs: List[str] = []
        
    def emit(self, record):
        """Enregistre un log"""
        try:
            msg = self.format(record)
            self.logs.append(msg)
        except Exception:
            self.handleError(record)
    
    def clear(self):
        """Efface tous les logs"""
        self.logs = []
    
    def get_logs(self) -> List[str]:
        """Retourne tous les logs"""
        return self.logs.copy()


def setup_log_capture():
    """Configure la capture de logs pour les modules de radars"""
    handler = StreamlitLogHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Ajouter aux loggers pertinents
    loggers = [
        'utils.radar_manager',
        'utils.intelligent_scoring',
        'utils.ai_analyzer'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return handler


def format_log_for_display(log: str) -> str:
    """Formate un log pour l'affichage HTML"""
    # Déterminer la couleur selon le niveau
    if 'ERROR' in log.upper() or 'ERREUR' in log.upper():
        color = '#ef4444'  # Rouge
    elif 'WARNING' in log.upper() or 'WARN' in log.upper():
        color = '#f59e0b'  # Orange
    elif 'SUCCESS' in log.upper() or 'SUCCES' in log.upper() or '✓' in log:
        color = '#22c55e'  # Vert
    elif 'INFO' in log.upper():
        color = '#3b82f6'  # Bleu
    else:
        color = '#94a3b8'  # Gris
    
    return f'<div style="color: {color}; margin: 2px 0;">{log}</div>'
