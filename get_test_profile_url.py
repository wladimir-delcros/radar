"""
Script rapide pour récupérer une URL de profil avec ID depuis la base de données
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from utils.database import get_connection

# Récupérer une URL de profil avec ID depuis la DB
with get_connection() as conn:
    cursor = conn.cursor()
    # Chercher un profil avec un ID (commence par ACo)
    cursor.execute("""
        SELECT profile_url, reactor_name, reactor_urn
        FROM reactions
        WHERE profile_url LIKE '%/in/ACo%'
        LIMIT 1
    """)
    row = cursor.fetchone()
    
    if row:
        profile_url = dict(row)['profile_url']
        reactor_name = dict(row)['reactor_name']
        reactor_urn = dict(row)['reactor_urn']
        print(f"Profil trouvé:")
        print(f"  Nom: {reactor_name}")
        print(f"  URN: {reactor_urn}")
        print(f"  URL: {profile_url}")
        print(f"\nCommande pour tester:")
        print(f'python test_profile_slug_resolver.py "{profile_url}"')
    else:
        print("Aucun profil avec ID trouvé dans la base de données")
        # Chercher n'importe quel profil
        cursor.execute("""
            SELECT profile_url, reactor_name
            FROM reactions
            WHERE profile_url IS NOT NULL AND profile_url != ''
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            profile_url = dict(row)['profile_url']
            reactor_name = dict(row)['reactor_name']
            print(f"\nProfil trouvé (peut ne pas avoir d'ID):")
            print(f"  Nom: {reactor_name}")
            print(f"  URL: {profile_url}")
            print(f"\nCommande pour tester:")
            print(f'python test_profile_slug_resolver.py "{profile_url}"')
