"""
Gestionnaire de configuration pour l'interface
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_config(config_file: Path = Path("config.json")) -> Dict[str, Any]:
    """
    Charge la configuration depuis config.json
    
    Args:
        config_file: Chemin vers le fichier de configuration
    
    Returns:
        Dictionnaire de configuration
    """
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement de la config: {e}")
        return {}


def save_config(config: Dict[str, Any], config_file: Path = Path("config.json")) -> bool:
    """
    Sauvegarde la configuration dans config.json
    
    Args:
        config: Dictionnaire de configuration
        config_file: Chemin vers le fichier de configuration
    
    Returns:
        True si succès, False sinon
    """
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la config: {e}")
        return False


def load_company_profile(profile_file: Path = Path("company_profile.json")) -> Dict[str, Any]:
    """
    Charge le profil entreprise depuis company_profile.json
    
    Args:
        profile_file: Chemin vers le fichier de profil
    
    Returns:
        Dictionnaire de profil
    """
    if not profile_file.exists():
        return {}
    
    try:
        with open(profile_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement du profil: {e}")
        return {}


def save_company_profile(profile: Dict[str, Any], profile_file: Path = Path("company_profile.json")) -> bool:
    """
    Sauvegarde le profil entreprise dans company_profile.json
    
    Args:
        profile: Dictionnaire de profil
        profile_file: Chemin vers le fichier de profil
    
    Returns:
        True si succès, False sinon
    """
    try:
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du profil: {e}")
        return False
