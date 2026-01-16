# Guide de Déploiement - LeadFlow

Ce guide vous explique comment déployer votre application Streamlit sur différentes plateformes.

## 🚀 Options de Déploiement

### 1. Streamlit Cloud (⭐ RECOMMANDÉ - Gratuit & Facile)

**Avantages :**
- ✅ Gratuit
- ✅ Déploiement en 2 minutes
- ✅ Intégration GitHub directe
- ✅ Mises à jour automatiques
- ✅ Support natif Streamlit

**Limitations :**
- ⚠️ Base de données SQLite réinitialisée à chaque redémarrage (utilisez une DB externe pour la persistance)
- ⚠️ Limite de mémoire (1GB)

**Instructions :**

1. **Créer un compte** : https://share.streamlit.io/
2. **Connecter votre repo GitHub** : `wladimir-delcros/radar`
3. **Configurer les secrets** :
   - Dans Streamlit Cloud → Settings → Secrets
   - Ajoutez vos variables d'environnement :
   ```toml
   [secrets]
   RAPIDAPI_KEY = "votre_clé_rapidapi"
   RAPIDAPI_HOST = "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
   OPENAI_API_KEY = "votre_clé_openai"
   APP_PASSWORD_HASH = "hash_du_mot_de_passe"
   ```
4. **Déployer** : Cliquez sur "Deploy"

**Note** : Vous devrez modifier le code pour utiliser les secrets Streamlit au lieu de `config.json`.

---

### 2. Railway (⭐ BON POUR SQLITE)

**Avantages :**
- ✅ Persistance de la base de données SQLite
- ✅ Gratuit avec limitations (500h/mois)
- ✅ Déploiement simple
- ✅ Variables d'environnement faciles

**Instructions :**

1. **Créer un compte** : https://railway.app/
2. **Nouveau projet** → "Deploy from GitHub repo"
3. **Sélectionner votre repo** : `wladimir-delcros/radar`
4. **Configurer** :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. **Variables d'environnement** :
   - `RAPIDAPI_KEY`
   - `RAPIDAPI_HOST`
   - `OPENAI_API_KEY`
   - `APP_PASSWORD_HASH`
6. **Déployer**

**Fichier `railway.json` nécessaire** :
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "streamlit run app.py --server.port $PORT --server.address 0.0.0.0",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

### 3. Render (Gratuit avec limitations)

**Avantages :**
- ✅ Gratuit (avec limitations)
- ✅ Persistance possible
- ✅ Déploiement simple

**Limitations :**
- ⚠️ L'app se met en veille après 15 min d'inactivité (gratuit)
- ⚠️ Redémarrage lent après veille

**Instructions :**

1. **Créer un compte** : https://render.com/
2. **New → Web Service**
3. **Connecter GitHub** → Sélectionner `wladimir-delcros/radar`
4. **Configuration** :
   - **Name** : `leadflow`
   - **Environment** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. **Variables d'environnement** : Ajouter toutes vos clés API
6. **Déployer**

---

### 4. Fly.io (Moderne & Performant)

**Avantages :**
- ✅ Persistance avec volumes
- ✅ Bonne performance
- ✅ Gratuit avec limitations

**Instructions :**

1. **Installer Fly CLI** : https://fly.io/docs/getting-started/installing-flyctl/
2. **Créer un compte** : `fly auth signup`
3. **Créer l'app** : `fly launch`
4. **Configurer `fly.toml`** (voir ci-dessous)
5. **Déployer** : `fly deploy`

---

### 5. Heroku (Payant maintenant)

**Avantages :**
- ✅ Très stable
- ✅ Add-ons disponibles

**Limitations :**
- ❌ Payant (à partir de $5/mois)

---

## 📋 Fichiers de Configuration Nécessaires

### Pour Railway

Créez `railway.json` :
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "streamlit run app.py --server.port $PORT --server.address 0.0.0.0",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Pour Fly.io

Créez `fly.toml` :
```toml
app = "leadflow"
primary_region = "cdg"

[build]

[env]
  PORT = "8501"

[[services]]
  internal_port = 8501
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [services.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

[[services.http_checks]]
  interval = "10s"
  timeout = "2s"
  grace_period = "5s"
  method = "GET"
  path = "/_stcore/health"
```

### Pour Render

Créez `render.yaml` :
```yaml
services:
  - type: web
    name: leadflow
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
    envVars:
      - key: RAPIDAPI_KEY
        sync: false
      - key: RAPIDAPI_HOST
        value: linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com
      - key: OPENAI_API_KEY
        sync: false
      - key: APP_PASSWORD_HASH
        sync: false
```

---

## ⚙️ Modifications Nécessaires pour le Déploiement

### 1. Utiliser les Variables d'Environnement

Vous devrez modifier `utils/config_manager.py` et `utils/radar_manager.py` pour lire depuis les variables d'environnement au lieu de `config.json` :

```python
import os

# Dans config_manager.py
def load_config():
    # Essayer d'abord les variables d'environnement
    if os.getenv('RAPIDAPI_KEY'):
        return {
            'api_key': os.getenv('RAPIDAPI_KEY'),
            'api_host': os.getenv('RAPIDAPI_HOST', 'linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com'),
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'enabled': bool(os.getenv('OPENAI_API_KEY')),
                # ... autres configs
            }
        }
    # Sinon charger depuis config.json (développement local)
    # ...
```

### 2. Gérer la Base de Données

Pour la persistance sur Streamlit Cloud, utilisez une base de données externe :
- **Supabase** (gratuit) : PostgreSQL
- **PlanetScale** (gratuit) : MySQL
- **Neon** (gratuit) : PostgreSQL

Ou utilisez Railway/Render qui persiste le système de fichiers.

### 3. Secrets Streamlit Cloud

Pour Streamlit Cloud, créez un fichier `.streamlit/secrets.toml` (localement, pas commité) :

```toml
[secrets]
RAPIDAPI_KEY = "votre_clé"
RAPIDAPI_HOST = "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
OPENAI_API_KEY = "votre_clé"
APP_PASSWORD_HASH = "hash_du_mot_de_passe"
```

Puis dans le code :
```python
import streamlit as st

# Lire depuis secrets
rapidapi_key = st.secrets.get('RAPIDAPI_KEY') or os.getenv('RAPIDAPI_KEY')
```

---

## 🎯 Recommandation

**Pour commencer rapidement** : **Streamlit Cloud**
- Gratuit
- Déploiement en 2 minutes
- Parfait pour tester

**Pour la production** : **Railway**
- Persistance de la DB
- Plus stable
- Bonne performance

---

## 📝 Checklist de Déploiement

- [ ] Repo GitHub privé configuré
- [ ] Variables d'environnement préparées
- [ ] Code modifié pour utiliser les variables d'environnement
- [ ] Fichiers de configuration créés (railway.json, fly.toml, etc.)
- [ ] Base de données externe configurée (si nécessaire)
- [ ] Test local avec variables d'environnement
- [ ] Déploiement effectué
- [ ] Test de l'application déployée
- [ ] Configuration du mot de passe sur l'app déployée

---

## 🔒 Sécurité

⚠️ **IMPORTANT** :
- Ne jamais committer les clés API
- Utiliser les secrets/variables d'environnement
- Activer l'authentification par mot de passe
- Utiliser HTTPS (automatique sur toutes les plateformes)
