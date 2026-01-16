# 🚀 Guide de Déploiement en Production

## Option Recommandée : Railway (⭐ MEILLEUR POUR LA PRODUCTION)

Railway est la meilleure option car :
- ✅ **Persistance automatique** de la base de données SQLite
- ✅ Support des repos privés GitHub
- ✅ Gratuit avec limitations (500h/mois)
- ✅ Déploiement automatique depuis GitHub
- ✅ Variables d'environnement faciles à configurer

---

## 📋 Étapes de Déploiement sur Railway

### 1. Créer un compte Railway

1. Aller sur https://railway.app/
2. Cliquer sur "Start a New Project"
3. Se connecter avec GitHub
4. Autoriser l'accès à votre repo `wladimir-delcros/radar`

### 2. Créer un nouveau projet

1. Cliquer sur "New Project"
2. Sélectionner "Deploy from GitHub repo"
3. Choisir votre repo : `wladimir-delcros/radar`
4. Railway détectera automatiquement le projet Python

### 3. Configurer les variables d'environnement

Dans Railway → Variables :

Ajoutez ces variables :

```
RAPIDAPI_KEY = votre_clé_rapidapi
RAPIDAPI_HOST = linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com
OPENAI_API_KEY = votre_clé_openai
APP_PASSWORD_HASH = 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
```

**Comment ajouter :**
1. Dans votre projet Railway → Onglet "Variables"
2. Cliquer sur "New Variable"
3. Ajouter chaque variable une par une

### 4. Configurer le déploiement

Railway détectera automatiquement :
- **Build Command** : `pip install -r requirements.txt`
- **Start Command** : Défini dans `railway.json`

Le fichier `railway.json` est déjà configuré dans votre repo.

### 5. Déployer

1. Railway déploiera automatiquement
2. Attendre la fin du build (2-3 minutes)
3. Votre app sera disponible sur une URL Railway (ex: `votre-app.railway.app`)

### 6. Configurer un domaine personnalisé (optionnel)

Dans Railway → Settings → Domains :
- Ajouter un domaine personnalisé si vous en avez un

---

## 🔧 Configuration Alternative : Render

Si vous préférez Render :

### 1. Créer un compte Render

1. Aller sur https://render.com/
2. Se connecter avec GitHub

### 2. Créer un nouveau Web Service

1. New → Web Service
2. Connecter le repo `wladimir-delcros/radar`
3. Configuration :
   - **Name** : `leadflow`
   - **Environment** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

### 3. Variables d'environnement

Dans Render → Environment :
- Ajouter les mêmes variables que Railway

### 4. Déployer

Render déploiera automatiquement.

**Note** : Render met l'app en veille après 15 min d'inactivité (plan gratuit).

---

## 🔐 Configuration des Secrets

### Pour Railway

Dans Railway → Variables, ajoutez :

| Variable | Valeur |
|----------|--------|
| `RAPIDAPI_KEY` | Votre clé RapidAPI |
| `RAPIDAPI_HOST` | `linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com` |
| `OPENAI_API_KEY` | Votre clé OpenAI |
| `APP_PASSWORD_HASH` | Hash de votre mot de passe (déjà dans config.json) |

### Pour Render

Même chose dans Render → Environment Variables

---

## ✅ Vérification Post-Déploiement

1. **Accéder à l'application** : Ouvrir l'URL fournie par Railway/Render
2. **Se connecter** : Utiliser les identifiants configurés
3. **Vérifier la base de données** : 
   - Créer un client
   - Créer un radar
   - Vérifier que les données persistent après redémarrage

---

## 🎯 Recommandation Finale

**Utilisez Railway** pour la production :
- ✅ Persistance automatique de SQLite
- ✅ Pas besoin de modifier le code
- ✅ Déploiement automatique depuis GitHub
- ✅ Support repos privés
- ✅ Gratuit avec limitations généreuses

---

## 📝 Notes Importantes

- ⚠️ **Ne jamais committer** les clés API dans le code
- ✅ Utilisez toujours les variables d'environnement
- ✅ Testez localement avant de déployer
- ✅ La base de données sera persistante sur Railway/Render (contrairement à Streamlit Cloud)

---

## 🆘 Dépannage

### L'app ne démarre pas
- Vérifier les logs dans Railway/Render
- Vérifier que toutes les variables d'environnement sont définies
- Vérifier que `requirements.txt` est à jour

### La base de données est vide
- Normal au premier démarrage
- Créer vos clients et radars via l'interface
- Les données persisteront après redémarrage

### Erreur de connexion API
- Vérifier que `RAPIDAPI_KEY` est correcte
- Vérifier que `RAPIDAPI_HOST` est correct
- Vérifier les quotas de votre plan RapidAPI
