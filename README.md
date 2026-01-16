# LinkedIn Scraper - Multi-Entreprises

Script Python pour récupérer automatiquement le dernier post LinkedIn de plusieurs entreprises quotidiennement et extraire les réactions dans un CSV consolidé. Les entreprises à suivre sont définies dans le fichier `companies_to_follow.csv`.

## Installation

1. **Installer Python** (3.7 ou supérieur)
   - Télécharger depuis [python.org](https://www.python.org/downloads/)

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

## Configuration

### Fichier config.json

Le fichier `config.json` contient les paramètres de configuration généraux et l'analyse IA :

```json
{
  "api_key": "votre_clé_api",
  "api_host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com",
  "limit": 1,
  "output_directory": "data",
  "openai": {
    "api_key": "votre_clé_openai",
    "model": "gpt-4o-mini",
    "temperature": 0.3,
    "max_tokens": 500,
    "enabled": true,
    "relevance_threshold": 0.6
  }
}
```

- `api_key`: Votre clé API RapidAPI
- `api_host`: Host de l'API LinkedIn Scraper
- `limit`: Nombre de posts à récupérer par entreprise (1 = dernier post uniquement)
- `output_directory`: Dossier où seront sauvegardés les posts et le CSV des réactions
- `openai`: Configuration de l'analyse IA (voir section dédiée ci-dessous)

### Configuration OpenAI (Analyse IA)

La section `openai` dans `config.json` permet de configurer l'analyse IA automatique :

- `api_key`: Votre clé API OpenAI (obligatoire si `enabled: true`)
- `model`: Modèle OpenAI à utiliser (par défaut: `gpt-4o-mini` pour économiser les coûts)
- `temperature`: Créativité des réponses (0.0-1.0, par défaut: 0.3 pour des analyses plus déterministes)
- `max_tokens`: Nombre maximum de tokens par réponse (par défaut: 500)
- `enabled`: Activer/désactiver l'analyse IA (par défaut: `true`)
- `relevance_threshold`: Seuil de pertinence pour filtrer les posts (0.0-1.0, par défaut: 0.6)

**Note** : Si `enabled: false` ou si la clé API OpenAI est manquante, le script fonctionnera normalement mais sans analyse IA (comportement par défaut).

### Fichier company_profile.json

Le fichier `company_profile.json` contient le profil de votre entreprise utilisé par l'IA pour qualifier les prospects et générer des messages personnalisés.

**Créez ce fichier à partir de `company_profile.json.example`** :

```bash
copy company_profile.json.example company_profile.json
```

Puis personnalisez-le avec vos informations :

- `company_name`: Nom de votre entreprise
- `company_description`: Description détaillée de ce que fait votre entreprise
- `products_services`: Liste de vos produits/services
- `target_persona`: Définition de votre persona cible
  - `job_titles`: Titres de poste ciblés
  - `company_types`: Types d'entreprises ciblées
  - `industries`: Secteurs d'activité ciblés
  - `company_size`: Taille des entreprises ciblées
  - `geographic_location`: Zones géographiques
  - `pain_points`: Problématiques ciblées
  - `characteristics`: Caractéristiques du persona
- `competitor_companies`: Entreprises concurrentes surveillées
  - `scraped_companies`: Liste des entreprises à suivre (celles dans `companies_to_follow.csv`)
  - `why_contact_on_their_posts`: Raison stratégique pour contacter les personnes qui réagissent
- `outreach_strategy`: Stratégie d'outreach
  - `what_offers`: Ce que vous proposez
  - `value_proposition`: Proposition de valeur
  - `ideal_signals`: Signaux indiquant un bon prospect
  - `message_template`: Template pour générer les messages
    - `tone`: Ton souhaité (professionnel, amical, etc.)
    - `structure`: Structure du message
    - `key_points`: Points clés à toujours mentionner
    - `call_to_action`: Type d'action souhaitée
    - `example`: Exemple de message type

**Exemple minimal** : Consultez `company_profile.json.example` pour un exemple complet et commenté.

### Fichier companies_to_follow.csv

Le fichier `companies_to_follow.csv` contient la liste des entreprises à suivre :

```csv
company_name,company_url,company_id,company_query
Growthroom,https://www.linkedin.com/company/growthroom/,25049482,25049482
```

- `company_name`: **Obligatoire** - Nom de l'entreprise utilisé par l'API (ex: "growthroom", "nvidia")
- `company_url`: URL LinkedIn de l'entreprise (optionnel, pour référence)
- `company_id`: ID numérique de l'entreprise (optionnel, pour référence)
- `company_query`: Query à utiliser pour l'API (optionnel, non utilisé par la nouvelle API)

**Note** : La nouvelle API utilise uniquement `company_name` (en minuscules) pour identifier l'entreprise. Les autres champs sont conservés pour référence mais ne sont pas utilisés par l'API.

## Utilisation

### Exécution manuelle

```bash
python linkedin_scraper_company.py
```

Le script va :
- Lire la liste des entreprises depuis `companies_to_follow.csv`
- Charger le profil entreprise depuis `company_profile.json` (si analyse IA activée)
- Pour chaque entreprise :
  - Récupérer les posts via l'API (endpoint `/company/posts`)
  - Extraire le dernier post (le plus récent)
  - Vérifier s'il n'a pas déjà été traité aujourd'hui (via `post_url` dans le CSV)
  - **🔍 Analyser la pertinence du post via IA** (si activée) - AVANT de récupérer les réactions
  - **Si post pertinent** (score > seuil) :
    - Récupérer les réactions du post (endpoint `/post/reactions` avec pagination)
    - **🔍 Qualifier chaque prospect via IA** (nom, headline, réaction)
    - **✉️ Générer un message personnalisé** pour chaque prospect pertinent
    - Sauvegarder le post complet dans `data/{company_name}_post_YYYYMMDD_HHMMSS.json`
    - Extraire les réactions enrichies et les ajouter au CSV consolidé `data/all_reactions_YYYYMMDD.csv`
  - **Si post non pertinent** :
    - Sauvegarder le post JSON avec l'analyse (sans réactions)
    - Ne pas récupérer les réactions (économie d'appels API)
- Logger les activités dans `linkedin_scraper_company.log`

### Planification automatique (Windows)

#### Option 1: PowerShell (recommandé)

Exécuter en tant qu'administrateur :

```powershell
.\schedule_task_windows.ps1
```

Ce script va créer une tâche planifiée qui s'exécute **tous les jours à 9h00**.

#### Option 2: Planificateur de tâches Windows (manuel)

1. Ouvrir le **Planificateur de tâches** (`taskschd.msc`)
2. Créer une **tâche de base**
3. Déclencheur : **Quotidien**, à 9h00
4. Action : **Démarrer un programme**
   - Programme : `python.exe` (ou chemin complet)
   - Arguments : `linkedin_scraper_company.py`
   - Dossier de départ : Chemin du projet

### Planification automatique (Linux/Mac)

Utiliser cron :

```bash
# Ouvrir le crontab
crontab -e

# Ajouter cette ligne pour exécuter tous les jours à 9h00
0 9 * * * cd /chemin/vers/projet && /usr/bin/python3 linkedin_scraper_company.py >> linkedin_scraper_company.log 2>&1
```

## Structure des fichiers

```
.
├── linkedin_scraper_company.py  # Script principal
├── companies_to_follow.csv      # Liste des entreprises à suivre
├── config.json                  # Configuration API
├── requirements.txt             # Dépendances Python
├── schedule_task_windows.ps1    # Script de planification Windows
├── README.md                    # Ce fichier
├── data/                        # Dossier de sortie (créé automatiquement)
│   ├── growthroom_post_YYYYMMDD_HHMMSS.json
│   ├── {company_name}_post_YYYYMMDD_HHMMSS.json
│   └── all_reactions_YYYYMMDD.csv  # CSV consolidé des réactions
└── linkedin_scraper_company.log # Logs du script
```

## Fichiers de sortie

### Fichiers JSON (posts)

Chaque exécution crée un fichier JSON dans le dossier `data/` pour chaque entreprise avec :
- `retrieved_at`: Date/heure de récupération (ISO format)
- `company_name`: Nom de l'entreprise
- `post`: Données complètes du post LinkedIn (incluant les posts récupérés via `/company/posts`)
- `ai_analysis` (si analyse IA activée) : Résultat de l'analyse IA du post
  - `post_relevant`: `true`/`false` - Le post est-il pertinent ?
  - `analysis`: Détails de l'analyse (score, reasoning, opportunity_signals)

Format du nom : `{company_name}_post_YYYYMMDD_HHMMSS.json`

Exemple : `growthroom_post_20260110_120000.json`

**Note** : Si le post est marqué comme non pertinent, le fichier JSON contiendra quand même l'analyse mais pas de réactions (économie d'appels API).

### Fichier CSV consolidé (réactions)

Un fichier CSV consolidé est créé/jour dans `data/all_reactions_YYYYMMDD.csv` contenant toutes les réactions de tous les posts traités.

**Colonnes du CSV** :

**Colonnes de base** :
- `company_name`: Nom de l'entreprise
- `post_url`: URL complète du post LinkedIn
- `post_date`: Date du post (format ISO)
- `reactor_name`: Nom de la personne qui a réagi
- `reactor_urn`: URN unique de la personne
- `profile_url`: URL du profil LinkedIn
- `reaction_type`: Type de réaction (LIKE, APPRECIATION, EMPATHY, etc.)
- `headline`: Titre/profession de la personne
- `profile_picture_url`: URL de la photo de profil (format medium)

**Colonnes d'analyse IA** (ajoutées si analyse IA activée) :
- `post_relevant`: `True`/`False` - Le post est-il pertinent pour contacter les réacteurs ?
- `prospect_relevant`: `True`/`False` - Ce prospect correspond-il au persona cible ?
- `relevance_score`: Score de pertinence (0.0 à 1.0) - Score du prospect si pertinent, sinon score du post
- `relevance_reasoning`: Explication textuelle de l'IA sur pourquoi le prospect est pertinent ou non
- `personalized_message`: Message personnalisé généré par l'IA (seulement si `prospect_relevant=True`)

**Note** : Le CSV devient ainsi une **liste de prospects qualifiés avec messages prêts à envoyer** pour l'outbound. Filtrez sur `prospect_relevant=True` pour obtenir uniquement les prospects pertinents avec leurs messages.

**Format du nom** : `all_reactions_YYYYMMDD.csv`

Exemple : `all_reactions_20260110.csv`

Le fichier CSV utilise le mode **append** : les nouvelles réactions sont ajoutées au fichier existant du jour sans écraser les données précédentes.

## Logs

Les logs sont enregistrés dans `linkedin_scraper_company.log` et affichés dans la console. Ils incluent :
- Les entreprises traitées
- Les requêtes API pour chaque entreprise
- Les succès/erreurs
- Les vérifications de doublons
- Les sauvegardes
- Un résumé final avec le nombre d'entreprises traitées avec succès

## Détection de doublons

Le script vérifie automatiquement si le post a déjà été traité aujourd'hui en vérifiant si le `post_url` existe déjà dans le CSV consolidé `all_reactions_YYYYMMDD.csv` pour cette entreprise. Si c'est le cas, il ne traite pas à nouveau le post et ne crée pas de nouveau fichier JSON.

## Gestion des erreurs

Le script gère :
- Erreurs de connexion réseau
- Erreurs d'API (rate limiting, clé invalide, etc.)
- Erreurs de parsing JSON
- Erreurs de fichiers (permissions, espace disque)

Toutes les erreurs sont loggées dans `linkedin_scraper.log`.

## API RapidAPI

Ce script utilise l'API **LinkedIn Scraper API** de RapidAPI :
- Documentation : [RapidAPI Hub](https://rapidapi.com/hub)
- Host : `linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com`
- Endpoints utilisés :
  - `/company/posts` : Récupère les posts d'une entreprise via `company_name`
  - `/post/reactions` : Récupère les réactions d'un post via `post_url` avec pagination (paramètres: `page_number`, `reaction_type`)
- Authentification : Headers `x-rapidapi-key` et `x-rapidapi-host`

**Structure de réponse** :
- `/company/posts` : `{success: true, data: {posts: [...]}}`
- `/post/reactions` : `{success: true, data: {reactions: [...], total_reactions: N}}`

**Pagination** : L'endpoint `/post/reactions` supporte la pagination via le paramètre `page_number`. Le script récupère automatiquement toutes les pages jusqu'à obtenir toutes les réactions.

## Sécurité

⚠️ **Important** : 
- Ne committez **jamais** vos clés API dans un dépôt public
- Les fichiers `config.json` et `company_profile.json` sont dans `.gitignore`
- Envisagez d'utiliser des variables d'environnement pour les clés API en production
- La clé OpenAI est particulièrement sensible - protégez-la comme un mot de passe

## Dépannage

### Le script ne trouve pas Python
- Vérifier que Python est dans le PATH
- Utiliser le chemin complet vers `python.exe` dans le Planificateur de tâches

### Erreur 401/403 de l'API
- Vérifier que la clé API est valide et active
- Vérifier les quotas de votre plan RapidAPI

### Aucun post récupéré
- Vérifier que le `company_name` dans `companies_to_follow.csv` correspond exactement au nom utilisé par LinkedIn (généralement en minuscules, ex: "growthroom", "nvidia")
- Vérifier que l'entreprise a bien publié des posts récemment
- Vérifier les logs pour voir les erreurs spécifiques pour chaque entreprise
- Tester manuellement l'API avec curl pour vérifier que le `company_name` fonctionne

### Ajouter une nouvelle entreprise
1. Ouvrir `companies_to_follow.csv`
2. Ajouter une nouvelle ligne avec les informations :
   ```csv
   NomEntreprise,https://www.linkedin.com/company/slug-entreprise/,ID_NUMERIQUE,ID_NUMERIQUE
   ```
   **Important** : Le `company_name` doit être le nom exact utilisé par LinkedIn (généralement le slug en minuscules)
3. Sauvegarder le fichier
4. Réexécuter le script

### Le CSV des réactions est vide
- Vérifier que le post a bien des réactions (certains posts peuvent n'en avoir aucune)
- **Si analyse IA activée** : Vérifier que le post a été marqué comme pertinent (voir logs)
- Vérifier les logs pour voir si l'API a retourné des réactions
- Vérifier que l'URL du post est valide et accessible

### L'analyse IA ne fonctionne pas
- Vérifier que `openai.enabled: true` dans `config.json`
- Vérifier que la clé OpenAI est valide et présente dans `config.json`
- Vérifier que `company_profile.json` existe et est correctement formaté (JSON valide)
- Vérifier que le package `openai` est installé : `pip install openai`
- Consulter les logs pour les erreurs spécifiques

### Aucun message généré dans le CSV
- Vérifier que des prospects ont été marqués comme `prospect_relevant=True`
- Augmenter le `relevance_threshold` dans `config.json` si trop strict (par défaut 0.6)
- Vérifier que `company_profile.json` contient bien votre stratégie d'outreach
- Consulter les logs pour voir si des erreurs sont survenues lors de la génération

### La tâche planifiée ne s'exécute pas
- Vérifier dans le Planificateur de tâches que la tâche est activée
- Vérifier les logs Windows (Observateur d'événements)
- Tester manuellement avec : `python linkedin_scraper_company.py`

## Analyse IA et Qualification Automatique

Le script intègre une **analyse IA via OpenAI** pour transformer le système en une **machine à intent et outbound** automatique.

### Fonctionnalités IA

1. **Analyse de pertinence des posts** (avant récupération des réactions)
   - L'IA analyse le contenu du post, son sujet, les stats
   - Détermine si le post représente une opportunité pour contacter les réacteurs
   - **Optimisation** : Si le post n'est pas pertinent (score < seuil), les réactions ne sont PAS récupérées (économie d'appels API)

2. **Qualification automatique des prospects**
   - Pour chaque personne ayant réagi, l'IA analyse :
     - Le titre de poste (headline)
     - Le secteur d'activité
     - Le type de réaction
     - Le contexte du post
   - Compare avec votre persona cible défini dans `company_profile.json`
   - Génère un score de pertinence (0.0-1.0) et un raisonnement détaillé

3. **Génération de messages personnalisés (icebreaker)**
   - Pour chaque prospect qualifié (`prospect_relevant=True`), l'IA génère automatiquement un message personnalisé
   - Le message fait référence au post spécifique sur lequel le prospect a réagi
   - Connecte avec votre solution/entreprise
   - Pose une question ouverte pour engager

### Structure des messages générés

Les messages générés suivent cette structure :

1. **Référence au post** : "Bonjour [Nom], je te contacte car j'ai vu que tu as réagi au post de [Entreprise] sur [sujet]"
2. **Connexion avec votre solution** : "C'est une problématique que nous résolvons/quelque chose que nous faisons chez [Votre entreprise] via [solution]"
3. **Question ouverte** : "Est-ce que c'est quelque chose que vous rencontrez chez [Entreprise prospect] ?"

**Exemple de message généré** :
```
Bonjour Charles,

Je te contacte car j'ai vu que tu as réagi au post de Growthroom sur l'optimisation des campagnes LinkedIn. C'est une problématique que nous résolvons chez Uclic via notre plateforme d'automatisation des campagnes B2B.

Est-ce que c'est quelque chose que vous rencontrez chez Growth Room ? Je serais ravi d'échanger sur vos défis actuels.

Bien à toi,
```

### Interprétation des scores

- **Score 0.8-1.0** : Prospect très pertinent, correspond parfaitement au persona
- **Score 0.6-0.8** : Prospect pertinent, correspond globalement au persona
- **Score 0.4-0.6** : Prospect moyennement pertinent, certaines correspondances
- **Score 0.0-0.4** : Prospect peu pertinent, ne correspond pas vraiment au persona

Le seuil par défaut est **0.6** (`relevance_threshold` dans `config.json`). Un prospect avec un score >= 0.6 sera marqué comme `prospect_relevant=True` et recevra un message personnalisé.

### Utilisation pour l'outbound

Le CSV enrichi (`all_reactions_YYYYMMDD.csv`) devient votre **liste de prospects qualifiés avec messages prêts à envoyer** :

1. **Filtrez les prospects pertinents** : `prospect_relevant=True`
2. **Triez par score** : `relevance_score` (du plus élevé au plus bas)
3. **Utilisez les messages générés** : Colonne `personalized_message`
4. **Personnalisez si nécessaire** : Les messages peuvent être ajustés avant envoi

Vous pouvez :
- Importer le CSV dans votre outil d'outbound (Lemlist, Instantly, etc.)
- Utiliser les colonnes `profile_url` et `reactor_name` pour contacter directement
- Filtrer par `reaction_type` pour prioriser certains types de réactions

### Coûts et Performance

- **Coût API OpenAI** : 
  - 1 appel par post analysé
  - 1 appel par prospect pour la qualification
  - 1 appel par prospect pertinent pour générer le message
  - Exemple : 1 post pertinent avec 50 prospects dont 10 pertinents = 1 + 50 + 10 = **61 appels API**

- **Optimisation** : L'analyse du post AVANT les réactions permet d'économiser tous les appels de qualification si le post n'est pas pertinent

- **Performance** : L'analyse de 100+ prospects peut prendre quelques minutes. Un délai de 0.5s entre chaque analyse est ajouté pour éviter les rate limits.

- **Désactivation** : Vous pouvez désactiver l'analyse IA via `openai.enabled: false` dans `config.json` pour économiser les coûts

## Workflow détaillé

### Workflow sans IA (analyse désactivée)

1. **Récupération des posts** : Le script appelle `/company/posts?company_name={company_name}` pour obtenir la liste des posts
2. **Sélection du dernier post** : Le premier post de la liste (le plus récent) est sélectionné
3. **Vérification des doublons** : Le script vérifie si le `post_url` existe déjà dans le CSV du jour
4. **Récupération des réactions** : Si le post n'a pas été traité, le script appelle `/post/reactions?post_url={post_url}` pour obtenir les réactions (avec pagination)
5. **Sauvegarde JSON** : Le post complet est sauvegardé dans un fichier JSON
6. **Extraction CSV** : Les réactions sont extraites et ajoutées au CSV consolidé du jour

### Workflow avec IA (analyse activée)

1. **Récupération des posts** : Le script appelle `/company/posts?company_name={company_name}`
2. **Sélection du dernier post** : Le premier post de la liste (le plus récent) est sélectionné
3. **Vérification des doublons** : Vérification si le `post_url` existe déjà dans le CSV du jour
4. **Chargement du profil entreprise** : Chargement de `company_profile.json`
5. **🔍 Analyse IA du post** : Analyse de la pertinence du post via OpenAI
   - Si post non pertinent (score < seuil) → Sauvegarde JSON avec analyse, arrêt (économie d'appels API)
   - Si post pertinent (score >= seuil) → Continuer
6. **Récupération des réactions** : Appel `/post/reactions?post_url={post_url}` avec pagination
7. **🔍 Qualification des prospects** : Pour chaque prospect, analyse IA de sa pertinence
8. **✉️ Génération de messages** : Pour chaque prospect pertinent, génération d'un message personnalisé
9. **Sauvegarde JSON** : Le post complet est sauvegardé avec les analyses IA
10. **Extraction CSV enrichie** : Les réactions sont extraites avec toutes les analyses et messages, ajoutées au CSV consolidé

**Résultat** : CSV enrichi avec prospects qualifiés et messages prêts à envoyer pour l'outbound
# radar
