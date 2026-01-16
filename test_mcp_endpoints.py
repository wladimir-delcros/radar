"""
Script de test pour analyser les endpoints MCP LinkedIn Scraper API
"""
import json
from pathlib import Path

# Note: Ce script nécessite que les fonctions MCP soient appelées via l'interface Cursor
# Il documente les endpoints disponibles et leur utilisation

print("=" * 80)
print("ANALYSE DES ENDPOINTS MCP - LINKEDIN SCRAPER API")
print("=" * 80)
print()

endpoints = {
    "Health Check": {
        "endpoint": "/health",
        "description": "Vérifie que l'API est opérationnelle",
        "utilisé": False,
        "utilité": "Monitoring"
    },
    "Company Detail": {
        "endpoint": "/companies/detail",
        "description": "Récupère les informations détaillées d'une entreprise",
        "utilisé": True,
        "utilité": "Haute - Pour récupérer les infos des concurrents"
    },
    "Company Posts": {
        "endpoint": "/company/posts",
        "description": "Récupère les posts d'une entreprise",
        "utilisé": True,
        "utilité": "Haute - Utilisé dans radars competitor_last_post"
    },
    "Company Search": {
        "endpoint": "/companies/search",
        "description": "Recherche d'entreprises par mot-clé",
        "utilisé": False,
        "utilité": "Moyenne - Pour trouver automatiquement des entreprises"
    },
    "Profile Detail": {
        "endpoint": "/profile/detail",
        "description": "Informations détaillées d'un profil",
        "utilisé": False,
        "utilité": "Haute - Pour enrichir les profils prospects"
    },
    "Profile Posts": {
        "endpoint": "/profile/posts",
        "description": "Posts récents d'un utilisateur",
        "utilisé": True,
        "utilité": "Haute - Utilisé dans radars person_last_post"
    },
    "Profile Comments": {
        "endpoint": "/profile/comments",
        "description": "Commentaires récents d'un utilisateur",
        "utilisé": False,
        "utilité": "Moyenne - Pour analyser l'engagement"
    },
    "Profile Reactions": {
        "endpoint": "/profile/reactions",
        "description": "Réactions récentes d'un utilisateur",
        "utilisé": False,
        "utilité": "Moyenne - Pour voir qui réagit"
    },
    "Profile Contact": {
        "endpoint": "/profile/contact",
        "description": "Informations de contact (email, etc.)",
        "utilisé": False,
        "utilité": "TRÈS HAUTE - Pour récupérer les emails des prospects"
    },
    "Post Detail": {
        "endpoint": "/post/detail",
        "description": "Détails complets d'un post",
        "utilisé": False,
        "utilité": "Haute - Pour améliorer le scoring avec plus de contexte"
    },
    "Post Comments": {
        "endpoint": "/post/comments",
        "description": "Commentaires d'un post avec métriques",
        "utilisé": False,
        "utilité": "TRÈS HAUTE - Pour récupérer les commentaires comme engagements"
    },
    "Post Reactions": {
        "endpoint": "/post/reactions",
        "description": "Réactions d'un post",
        "utilisé": True,
        "utilité": "Haute - Utilisé dans tous les radars"
    },
    "Post Reposts": {
        "endpoint": "/post/reposts",
        "description": "Reposts d'un post",
        "utilisé": False,
        "utilité": "Moyenne - Pour voir qui partage"
    },
    "Posts Search": {
        "endpoint": "/posts/search",
        "description": "Recherche de posts par mot-clé",
        "utilisé": True,
        "utilité": "Haute - Utilisé dans radars keyword_posts"
    },
    "Jobs Search": {
        "endpoint": "/jobs/search",
        "description": "Recherche d'emplois avec filtres",
        "utilisé": False,
        "utilité": "Basse - Pour identifier des opportunités business"
    },
    "Job Detail": {
        "endpoint": "/jobs/detail",
        "description": "Détails d'une offre d'emploi",
        "utilisé": False,
        "utilité": "Basse"
    }
}

print("[RESUME] RESUME PAR CATEGORIE")
print("-" * 80)

# Endpoints utilisés
used = [name for name, info in endpoints.items() if info["utilisé"]]
unused_high = [name for name, info in endpoints.items() if not info["utilisé"] and ("TRÈS HAUTE" in info["utilité"] or "Haute" in info["utilité"])]

print(f"\n[OK] Endpoints actuellement utilises ({len(used)}):")
for name in used:
    print(f"   - {name} ({endpoints[name]['endpoint']})")

print(f"\n[WARN] Endpoints non utilises mais tres utiles ({len(unused_high)}):")
for name in unused_high:
    print(f"   - {name} ({endpoints[name]['endpoint']}) - {endpoints[name]['utilité']}")

print("\n" + "=" * 80)
print("[INFO] RECOMMANDATIONS")
print("=" * 80)
print("""
1. PRIORITE 1: Utiliser /post/comments
   -> Les commentaires sont des engagements de qualite superieure aux reactions
   -> Permet de recuperer plus de prospects pertinents

2. PRIORITE 2: Utiliser /profile/contact
   -> Recupere les emails et contacts des prospects
   -> Ameliore considerablement la qualite des leads

3. PRIORITE 3: Utiliser /post/detail
   -> Recupere le contenu complet du post
   -> Ameliore le scoring IA avec plus de contexte

4. NOUVEAU TYPE DE RADAR: "Comments Radar"
   -> Creer un nouveau type de radar qui suit les commentaires
   -> Alternative ou complement aux radars de reactions

5. AMELIORATION: Utiliser /companies/search
   -> Permettre de rechercher automatiquement des entreprises
   -> Facilite l'ajout de concurrents
""")

print("=" * 80)
print("[INFO] FONCTIONS MCP DISPONIBLES")
print("=" * 80)
print("""
Les fonctions MCP suivantes sont disponibles dans Cursor:

1. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast6ff5e99  → /health
2. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast54a9a3d → /companies/detail
3. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fastf956ccd → /company/posts
4. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast90651b9 → /companies/search
5. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast91cc253 → /profile/detail
6. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast5bec835 → /profile/posts
7. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast2e2e8ff → /profile/comments
8. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast86522b7 → /profile/reactions
9. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast916550b → /profile/contact
10. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fastaf3e9cf → /post/detail
11. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fastc8f7e23 → /post/comments
12. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast83b3646 → /post/reactions
13. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast01ff49b → /post/reposts
14. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast0e457bb → /posts/search
15. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast66d7392 → /jobs/search
16. mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fasta532502 → /jobs/detail
""")
