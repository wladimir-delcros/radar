# Analyse des Endpoints MCP - LinkedIn Scraper API

## 📋 Vue d'ensemble

L'API LinkedIn Scraper (RapidAPI) expose plusieurs endpoints via MCP pour récupérer des données LinkedIn en temps réel.

## 🔍 Endpoints Disponibles

### 1. Health Check
**Endpoint:** `/health`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast6ff5e99`  
**Description:** Vérifie que l'API est opérationnelle  
**Méthode:** GET  
**Paramètres:** Aucun  
**Retour:** Status et timestamp

### 2. Company Detail (Détails d'une entreprise)
**Endpoint:** `/companies/detail`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast54a9a3d`  
**Description:** Récupère les informations détaillées d'une entreprise  
**Méthode:** GET  
**Paramètres:**
- `identifier` (requis): Nom de l'entreprise, URL LinkedIn ou URN
  - Exemples: "youtube", "https://www.linkedin.com/company/youtube/", "1035"

**Utilisation actuelle:** Utilisé pour récupérer les informations des concurrents

### 3. Company Posts (Posts d'une entreprise)
**Endpoint:** `/company/posts`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fastf956ccd`  
**Description:** Récupère les posts d'une entreprise  
**Méthode:** GET  
**Paramètres:**
- `company_name` (requis): Nom de l'entreprise, URL LinkedIn ou URN
  - Exemples: "google", "https://www.linkedin.com/company/google/", "1035"

**Utilisation actuelle:** Utilisé dans les radars de type "competitor_last_post"

### 4. Company Search (Recherche d'entreprises)
**Endpoint:** `/companies/search`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast90651b9`  
**Description:** Recherche des entreprises par mot-clé avec filtres optionnels  
**Méthode:** GET  
**Paramètres:**
- `keyword` (requis): Nom de l'entreprise ou URL LinkedIn ou URN
- `industry_ids` (optionnel): IDs d'industries séparés par des virgules (ex: '6,4')
- `location_ids` (optionnel): IDs de localisations séparés par des virgules (ex: '106693272,103644278')
- `page_number` (optionnel, défaut: 1): Numéro de page pour la pagination

**Utilisation actuelle:** Non utilisé - pourrait être utile pour trouver des entreprises

### 5. Profile Detail (Détails d'un profil)
**Endpoint:** `/profile/detail`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast91cc253`  
**Description:** Récupère les informations détaillées d'un profil LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `username` (requis): Nom d'utilisateur LinkedIn (ex: 'neal-mohan' depuis https://www.linkedin.com/in/neal-mohan/)

**Utilisation actuelle:** Non utilisé - pourrait être utile pour enrichir les profils de prospects

### 6. Profile Posts (Posts d'un profil)
**Endpoint:** `/profile/posts`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast5bec835`  
**Description:** Récupère les posts récents d'un utilisateur LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `username` (requis): Nom d'utilisateur LinkedIn (ex: 'satyanadella' ou 'linkedin.com/in/satyanadella')
- `page_number` (optionnel, défaut: 1): Numéro de page
- `pagination_token` (optionnel): Token de pagination pour les pages suivantes

**Utilisation actuelle:** Utilisé dans les radars de type "person_last_post"

### 7. Profile Comments (Commentaires d'un profil)
**Endpoint:** `/profile/comments`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast2e2e8ff`  
**Description:** Récupère les commentaires récents d'un utilisateur LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `username` (requis): Nom d'utilisateur LinkedIn
- `page_number` (optionnel, défaut: 1): Numéro de page
- `pagination_token` (optionnel): Token de pagination

**Utilisation actuelle:** Non utilisé - pourrait être utile pour analyser l'engagement d'une personne

### 8. Profile Reactions (Réactions d'un profil)
**Endpoint:** `/profile/reactions`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast86522b7`  
**Description:** Récupère les réactions récentes d'un utilisateur LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `username` (requis): Nom d'utilisateur LinkedIn
- `page_number` (optionnel, défaut: 1): Numéro de page
- `pagination_token` (optionnel): Token de pagination

**Utilisation actuelle:** Non utilisé - pourrait être utile pour voir qui réagit aux posts d'une personne

### 9. Profile Contact (Informations de contact d'un profil)
**Endpoint:** `/profile/contact`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast916550b`  
**Description:** Récupère les informations de contact d'un utilisateur LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `username` (requis): Nom d'utilisateur LinkedIn

**Utilisation actuelle:** Non utilisé - pourrait être très utile pour récupérer les emails/contacts

### 10. Post Detail (Détails d'un post)
**Endpoint:** `/post/detail`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fastaf3e9cf`  
**Description:** Récupère les détails d'un post LinkedIn spécifique  
**Méthode:** GET  
**Paramètres:**
- `post_url` (requis): URL ou URN du post LinkedIn

**Utilisation actuelle:** Partiellement utilisé - pourrait être mieux exploité pour le scoring

### 11. Post Comments (Commentaires d'un post)
**Endpoint:** `/post/comments`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fastc8f7e23`  
**Description:** Récupère les commentaires d'un post avec métriques d'engagement  
**Méthode:** GET  
**Paramètres:**
- `post_url` (requis): URL ou URN du post LinkedIn
- `page_number` (optionnel, défaut: 1): Numéro de page
- `sort_order` (optionnel): "Most relevant" ou "Most recent" (défaut: "Most relevant")

**Utilisation actuelle:** Non utilisé - pourrait être très utile pour les radars (commentaires = engagements)

### 12. Post Reactions (Réactions d'un post)
**Endpoint:** `/post/reactions`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast83b3646`  
**Description:** Récupère les réactions d'un post LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `post_url` (requis): URL ou URN du post LinkedIn
- `page_number` (optionnel, défaut: "1"): Numéro de page
- `reaction_type` (optionnel): "ALL", "LIKE", "PRAISE", "EMPATHY", "APPRECIATION", "INTEREST" (défaut: "ALL")

**Utilisation actuelle:** Utilisé dans les radars pour récupérer les réactions des posts

### 13. Post Reposts (Reposts d'un post)
**Endpoint:** `/post/reposts`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast01ff49b`  
**Description:** Récupère les reposts d'un post LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `post_url` (requis): URL ou URN du post LinkedIn
- `page_number` (optionnel): Numéro de page

**Utilisation actuelle:** Non utilisé - pourrait être utile pour voir qui partage les posts

### 14. Posts Search (Recherche de posts par mot-clé)
**Endpoint:** `/posts/search`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast0e457bb`  
**Description:** Recherche des posts LinkedIn par mot-clé avec filtres  
**Méthode:** GET  
**Paramètres:**
- `keyword` (requis): Mot-clé à rechercher
- `date_filter` (optionnel): "past-24h", "past-week", "past-month"
- `sort_type` (optionnel): "date_posted" ou "relevance" (défaut: "date_posted")
- `page_number` (optionnel, défaut: 1): Numéro de page

**Utilisation actuelle:** Utilisé dans les radars de type "keyword_posts"

### 15. Jobs Search (Recherche d'emplois)
**Endpoint:** `/jobs/search`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fast66d7392`  
**Description:** Recherche d'emplois sur LinkedIn avec filtres avancés  
**Méthode:** GET  
**Paramètres:**
- `keywords` (requis): Mots-clés de recherche (par défaut: "United States")
- `location` (optionnel): Pays ou ville (défaut: "United States")
- `experience` (optionnel): "internship", "entry", "associate", "mid_senior", "director", "executive"
- `job_type` (optionnel): "fulltime", "parttime", "contract", "internship", "other"
- `remote` (optionnel): "onsite", "remote", "hybrid"
- `date_posted` (optionnel): "month", "week", "day"
- `easy_apply` (optionnel): Booléen pour Easy Apply uniquement
- `under_10_applicants` (optionnel): Booléen pour jobs avec moins de 10 candidats
- `sort` (optionnel): "relevant" ou "recent"
- `page_number` (optionnel, défaut: 1): Numéro de page

**Utilisation actuelle:** Non utilisé - pourrait être utile pour identifier des opportunités

### 16. Job Detail (Détails d'une offre d'emploi)
**Endpoint:** `/jobs/detail`  
**Fonction MCP:** `mcp_RapidAPI_Hub_-_LinkedIn_Scraper_API__Real-time___Fasta532502`  
**Description:** Récupère les détails d'une offre d'emploi LinkedIn  
**Méthode:** GET  
**Paramètres:**
- `job_id` (requis): ID LinkedIn de l'offre d'emploi (ex: 4011051212)

**Utilisation actuelle:** Non utilisé

## 📊 Récapitulatif des Endpoints par Catégorie

### Entreprises
- ✅ `/companies/detail` - **Utilisé**
- ✅ `/company/posts` - **Utilisé**
- ⚠️ `/companies/search` - Non utilisé (pourrait être utile)

### Profils Utilisateurs
- ✅ `/profile/posts` - **Utilisé**
- ⚠️ `/profile/detail` - Non utilisé
- ⚠️ `/profile/comments` - Non utilisé
- ⚠️ `/profile/reactions` - Non utilisé
- ⚠️ `/profile/contact` - **Très utile** (emails/contacts)

### Posts
- ✅ `/posts/search` - **Utilisé**
- ✅ `/post/reactions` - **Utilisé**
- ⚠️ `/post/detail` - Partiellement utilisé
- ⚠️ `/post/comments` - **Très utile** (pour radars)
- ⚠️ `/post/reposts` - Non utilisé

### Emplois
- ⚠️ `/jobs/search` - Non utilisé
- ⚠️ `/jobs/detail` - Non utilisé

## 🚀 Recommandations d'Amélioration

### 1. Utiliser `/post/comments` pour les Radars
Les commentaires sont aussi des engagements intéressants. Actuellement, on récupère seulement les réactions. Il faudrait aussi récupérer les commentaires.

### 2. Utiliser `/profile/contact` pour enrichir les Prospects
Cet endpoint pourrait fournir les emails et autres informations de contact des prospects.

### 3. Utiliser `/post/detail` pour mieux scorer
Récupérer le contenu complet du post pourrait améliorer le scoring IA en ayant plus de contexte.

### 4. Ajouter un type de radar "Comments"
Créer un nouveau type de radar qui suit les commentaires au lieu des réactions.

### 5. Utiliser `/companies/search` pour trouver des concurrents
Permettre de rechercher automatiquement des entreprises similaires.
