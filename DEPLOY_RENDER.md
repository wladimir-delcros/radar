# 🚀 Déploiement sur Render (100% Gratuit)

## ⚡ Déploiement en 5 minutes

### Étape 1 : Créer un compte Render

1. Aller sur **https://render.com/**
2. Cliquer sur **"Get Started for Free"**
3. Se connecter avec **GitHub**
4. Autoriser l'accès à votre repo

### Étape 2 : Créer un Web Service

1. Dans le dashboard Render, cliquer sur **"New +"**
2. Sélectionner **"Web Service"**
3. Connecter votre repo GitHub :
   - Cliquer sur **"Connect account"** si nécessaire
   - Sélectionner le repo : **`wladimir-delcros/radar`**
   - Cliquer sur **"Connect"**

### Étape 3 : Configurer le service

Remplir le formulaire :

- **Name** : `leadflow` (ou le nom que vous voulez)
- **Region** : Choisir la région la plus proche (ex: `Frankfurt` pour l'Europe)
- **Branch** : `main`
- **Root Directory** : (laisser vide)
- **Environment** : `Python 3`
- **Build Command** : `pip install -r requirements.txt`
- **Start Command** : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

### Étape 4 : Ajouter les variables d'environnement

**AVANT de cliquer sur "Create Web Service"**, ajouter les variables :

1. Cliquer sur **"Advanced"** en bas du formulaire
2. Dans **"Environment Variables"**, ajouter :

| Key | Value |
|-----|-------|
| `RAPIDAPI_KEY` | `votre_clé_rapidapi` |
| `RAPIDAPI_HOST` | `linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com` |
| `OPENAI_API_KEY` | `votre_clé_openai` |
| `APP_PASSWORD_HASH` | `8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918` |

**Comment ajouter :**
- Cliquer sur **"Add Environment Variable"**
- Entrer le **Key** et la **Value**
- Répéter pour chaque variable

### Étape 5 : Créer et déployer

1. Cliquer sur **"Create Web Service"**
2. Render va :
   - Cloner votre repo
   - Installer les dépendances (`pip install -r requirements.txt`)
   - Démarrer l'application
3. Attendre 2-3 minutes pour le build
4. Votre app sera disponible sur : `https://leadflow.onrender.com` (ou le nom que vous avez choisi)

---

## ✅ Vérification

1. **Ouvrir l'URL** fournie par Render
2. **Se connecter** avec vos identifiants (configurés dans Configuration → Sécurité)
3. **Tester** :
   - Créer un client
   - Créer un radar
   - Vérifier que tout fonctionne

---

## 🔄 Déploiement Automatique

Render déploie automatiquement à chaque push sur la branche `main` :
- Vous faites un `git push`
- Render détecte le changement
- Render redéploie automatiquement (2-3 minutes)

---

## 📝 Notes Importantes

- ⚠️ **Mise en veille** : L'app se met en veille après 15 min d'inactivité (plan gratuit)
- ✅ **Redémarrage** : Le premier accès après veille prend ~30 secondes
- ✅ **Base de données** : SQLite est **persistante** sur Render (contrairement à Streamlit Cloud)
- ✅ **Repos privés** : Supportés gratuitement

---

## 🆘 Dépannage

### L'app ne démarre pas
- Vérifier les **logs** dans Render → Logs
- Vérifier que toutes les **variables d'environnement** sont définies
- Vérifier que `requirements.txt` est à jour

### Erreur "Module not found"
- Vérifier que toutes les dépendances sont dans `requirements.txt`
- Vérifier les logs pour voir quelle dépendance manque

### La base de données est vide
- Normal au premier démarrage
- Créer vos clients et radars via l'interface
- Les données **persisteront** après redémarrage

---

## 🎉 C'est tout !

Votre application est maintenant en production sur Render, **100% gratuit** avec persistance de la base de données !
