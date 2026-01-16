# Testeur de Résolution de Slugs LinkedIn

Script de test pour convertir les URLs LinkedIn avec IDs (ex: `linkedin.com/in/ACoAAA...`) en vrais slugs (ex: `linkedin.com/in/john-doe`).

## Installation des dépendances

```bash
pip install beautifulsoup4 requests
```

Ou installez toutes les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

### Méthode 1 : Ligne de commande avec URL
```bash
python test_profile_slug_resolver.py "https://www.linkedin.com/in/ACoAAA1pe-0BshJ1-fAY_L-H0NSApuQHswGi0Lo"
```

### Méthode 2 : Mode interactif
```bash
python test_profile_slug_resolver.py
```
Le script vous demandera d'entrer une URL à tester.

## Méthodes testées

### 1. Méthode gratuite (redirections HTTP + scraping)
- ✅ Gratuite
- ✅ Suit les redirections HTTP (301/302)
- ✅ Scrape les meta tags HTML (`og:url`, `canonical`)
- ⚠️ Ne fonctionne que pour les profils publics
- ⚠️ Peut être bloquée par LinkedIn (rate limiting)
- ⚠️ Peut violer les ToS si utilisée de manière abusive

### 2. Méthode API (coûteux)
- ⚠️ Coûte de l'argent (appels API)
- ✅ Plus fiable
- ✅ Fonctionne même pour les profils privés (si autorisé)

## Résultats

Le script affiche :
- Le statut de chaque méthode testée
- Le slug trouvé (si disponible)
- Les erreurs rencontrées
- Les méthodes utilisées pour trouver le slug

## Exemple de sortie

```
============================================================
TEST POUR: https://www.linkedin.com/in/ACoAAA1pe-0BshJ1...
============================================================

TEST: Résolution via redirections pour: https://www.linkedin.com/in/ACoAAA1pe-0BshJ1...
URL complète: https://www.linkedin.com/in/ACoAAA1pe-0BshJ1...
Envoi de la requête HTTP...
URL finale après redirection: https://www.linkedin.com/in/john-doe
Slug extrait de l'URL finale: john-doe
✓ Slug trouvé via redirection: https://www.linkedin.com/in/john-doe

Résultat méthode redirection:
  - Slug trouvé: True
  - Slug: https://www.linkedin.com/in/john-doe
```

## Notes importantes

1. **Les URLs avec IDs fonctionnent toujours** : Les URLs comme `linkedin.com/in/ACoAAA...` sont valides et fonctionnelles sur LinkedIn, elles sont juste moins lisibles.

2. **Résolution gratuite limitée** : La méthode gratuite ne fonctionne que si :
   - Le profil est public
   - LinkedIn redirige vers le slug
   - Les meta tags contiennent le slug

3. **Respect des ToS** : Utilisez ce script de manière responsable et respectez les conditions d'utilisation de LinkedIn.
