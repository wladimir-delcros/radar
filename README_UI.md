# Interface Utilisateur - LinkedIn Scraper

## Installation

L'interface utilisateur utilise Streamlit. Toutes les dépendances sont dans `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Lancement

Pour lancer l'interface web :

```bash
streamlit run app.py
```

L'interface s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`.

## Pages disponibles

1. **📊 Dashboard** : Vue d'ensemble avec métriques et graphiques
2. **👥 Prospects** : Liste complète des prospects avec filtres et recherche
3. **💬 Messages** : Gestion et édition des messages personnalisés
4. **⚙️ Scraper** : Contrôle et monitoring du scraper
5. **📈 Statistiques** : Graphiques et analyses détaillées
6. **⚙️ Configuration** : Gestion de la configuration (API, profil entreprise, entreprises à suivre)

## Fonctionnalités

### Dashboard
- Métriques clés (total prospects, pertinents, messages générés, score moyen)
- Graphiques d'évolution par jour
- Répartition par type de réaction

### Prospects
- Tableau interactif avec toutes les données
- Filtres avancés (date, score, type de réaction, entreprise, recherche texte)
- Export CSV et Excel
- Tri personnalisable

### Messages
- Liste des messages personnalisés
- Édition des messages avec sauvegarde
- Restauration des messages originaux
- Export TXT et CSV des messages

### Scraper
- Lancement manuel du scraper
- Monitoring des logs en temps réel
- Sélection des entreprises à traiter
- Activation/désactivation de l'analyse IA

### Statistiques
- Graphiques interactifs (Plotly)
- Évolution par jour
- Répartition par type
- Distribution des scores
- Top entreprises

### Configuration
- Édition de la configuration API (RapidAPI, OpenAI)
- Édition du profil entreprise (JSON)
- Gestion des entreprises à suivre (ajout/suppression)

## Notes

- Les données sont mises en cache pendant 5 minutes pour améliorer les performances
- Utilisez le bouton "Actualiser" pour recharger les données
- Les messages édités sont sauvegardés dans `data/edited_messages.json`
- Les exports sont sauvegardés dans le dossier `data/`
