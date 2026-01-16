"""
Gestionnaire d'export pour les données
"""
import pandas as pd
import json
from pathlib import Path
from typing import Optional


def export_to_csv(df: pd.DataFrame, output_path: Path) -> bool:
    """
    Exporte un DataFrame en CSV
    
    Args:
        df: DataFrame à exporter
        output_path: Chemin de sortie
    
    Returns:
        True si succès, False sinon
    """
    try:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"Erreur lors de l'export CSV: {e}")
        return False


def export_to_excel(df: pd.DataFrame, output_path: Path) -> bool:
    """
    Exporte un DataFrame en Excel
    
    Args:
        df: DataFrame à exporter
        output_path: Chemin de sortie
    
    Returns:
        True si succès, False sinon
    """
    try:
        df.to_excel(output_path, index=False, engine='openpyxl')
        return True
    except Exception as e:
        print(f"Erreur lors de l'export Excel: {e}")
        return False


def export_messages_to_txt(df: pd.DataFrame, output_path: Path) -> bool:
    """
    Exporte les messages personnalisés en fichier TXT
    
    Args:
        df: DataFrame avec les messages
        output_path: Chemin de sortie
    
    Returns:
        True si succès, False sinon
    """
    try:
        messages_df = df[df.get('personalized_message', '').astype(str).str.strip() != ''].copy()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for idx, row in messages_df.iterrows():
                name = row.get('reactor_name', 'Unknown')
                message = row.get('personalized_message', '')
                f.write(f"=== {name} ===\n\n")
                f.write(f"{message}\n\n")
                f.write("-" * 50 + "\n\n")
        
        return True
    except Exception as e:
        print(f"Erreur lors de l'export TXT: {e}")
        return False
