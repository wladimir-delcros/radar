"""
Utilitaire pour charger et traiter les données du scraper LinkedIn (SQLite)
"""
import pandas as pd
from pathlib import Path
from typing import Optional
import re

from utils.database import get_reactions


def load_all_reactions(client_id: int = None, data_dir: Path = None) -> pd.DataFrame:
    """
    Charge les reactions depuis SQLite

    Args:
        client_id: ID du client (optionnel, charge tous si None)
        data_dir: Ignore (garde pour compatibilite)

    Returns:
        DataFrame pandas avec toutes les reactions
    """
    reactions = get_reactions(client_id)

    if not reactions:
        return pd.DataFrame()

    # Convertir en DataFrame
    df = pd.DataFrame(reactions)

    # Renommer competitor_name en company_name pour compatibilite
    if 'competitor_name' in df.columns:
        df['company_name'] = df['competitor_name']

    # Colonnes attendues
    expected_cols = [
        'company_name', 'post_url', 'post_date', 'reactor_name',
        'reactor_urn', 'profile_url', 'reaction_type', 'headline',
        'profile_picture_url', 'post_relevant', 'prospect_relevant',
        'relevance_score', 'relevance_reasoning', 'personalized_message'
    ]

    # Ajouter les colonnes manquantes
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # Convertir les dates
    if 'post_date' in df.columns:
        df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')
    
    # Convertir created_at si disponible
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

    # Convertir les scores en float
    if 'relevance_score' in df.columns:
        df['relevance_score'] = pd.to_numeric(df['relevance_score'], errors='coerce').fillna(0.0)

    # Convertir les booleens
    for col in ['post_relevant', 'prospect_relevant']:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    # Extraire l'entreprise depuis le headline
    if 'headline' in df.columns:
        df['detected_company'] = df['headline'].apply(extract_company_from_headline)

    # Trier par date (plus recent en premier)
    if 'post_date' in df.columns:
        df = df.sort_values('post_date', ascending=False)

    return df


def extract_company_from_headline(headline: str) -> str:
    """
    Extrait le nom de l'entreprise depuis le headline

    Args:
        headline: Headline LinkedIn

    Returns:
        Nom de l'entreprise ou chaine vide
    """
    if pd.isna(headline) or not headline:
        return ""

    headline = str(headline)

    # Chercher des patterns comme "@Company", "chez Company", "at Company"
    patterns = [
        r'(?:@|chez|at)\s+([A-Z][a-zA-Z\s&]+)',
        r'@([A-Z][a-zA-Z\s&]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, headline)
        if match:
            company = match.group(1).strip()
            # Nettoyer (enlever les mots courts communs en fin)
            company = re.sub(r'\s+(Inc|Ltd|LLC|SA|SAS|SARL)\s*$', '', company, flags=re.IGNORECASE)
            return company

    return ""


def get_prospects_with_messages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtre les prospects qui ont un message personnalise

    Args:
        df: DataFrame avec toutes les reactions

    Returns:
        DataFrame filtre avec seulement les prospects pertinents
    """
    if df.empty:
        return df

    # Filtrer sur prospect_relevant=True et personalized_message non vide
    filtered = df.copy()

    if 'prospect_relevant' in df.columns:
        filtered = filtered[filtered['prospect_relevant'] == True]

    if 'personalized_message' in filtered.columns:
        filtered = filtered[filtered['personalized_message'].astype(str).str.strip() != '']
    else:
        return pd.DataFrame()

    return filtered


def get_stats(df: pd.DataFrame) -> dict:
    """
    Calcule des statistiques sur les donnees

    Args:
        df: DataFrame avec toutes les reactions

    Returns:
        Dictionnaire avec les statistiques
    """
    if df.empty:
        return {
            'total_prospects': 0,
            'relevant_prospects': 0,
            'messages_generated': 0,
            'avg_score': 0.0,
            'relevance_rate': 0.0
        }

    total = len(df)
    relevant = len(df[df.get('prospect_relevant', False) == True])
    messages = len(df[df.get('personalized_message', '').astype(str).str.strip() != ''])
    avg_score = df.get('relevance_score', pd.Series([0])).mean() if not df.empty else 0.0
    relevance_rate = (relevant / total * 100) if total > 0 else 0.0

    return {
        'total_prospects': total,
        'relevant_prospects': relevant,
        'messages_generated': messages,
        'avg_score': float(avg_score),
        'relevance_rate': float(relevance_rate)
    }
