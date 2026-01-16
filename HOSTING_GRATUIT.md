# 🆓 Options d'Hébergement GRATUIT

## 🏆 Top 3 Options Gratuites (avec persistance DB)

### 1. Railway (⭐ RECOMMANDÉ - Le meilleur gratuit)

**Gratuit :**
- ✅ 500 heures/mois gratuites
- ✅ $5 de crédit gratuit/mois
- ⚠️ Peut demander une carte bancaire (mais ne facture pas si vous restez dans les limites)

**Avantages :**
- ✅ **Persistance automatique** de SQLite
- ✅ Support repos privés GitHub
- ✅ Déploiement automatique
- ✅ Pas de mise en veille
- ✅ Très stable

**Instructions :**
1. Aller sur https://railway.app/
2. "Start a New Project" → "Deploy from GitHub repo"
3. Sélectionner `wladimir-delcros/radar`
4. Ajouter les variables d'environnement (voir ci-dessous)
5. C'est tout ! Railway déploie automatiquement

---

### 2. Render (100% Gratuit, sans carte)

**Gratuit :**
- ✅ Illimité (plan gratuit)
- ✅ Pas besoin de carte bancaire
- ⚠️ Mise en veille après 15 min d'inactivité (redémarrage lent ~30s)

**Avantages :**
- ✅ **Persistance de SQLite**
- ✅ Support repos privés
- ✅ Déploiement automatique
- ✅ 100% gratuit sans limite

**Instructions :**
1. Aller sur https://render.com/
2. Se connecter avec GitHub
3. "New" → "Web Service"
4. Sélectionner le repo `wladimir-delcros/radar`
5. Configuration :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
6. Ajouter les variables d'environnement
7. "Create Web Service"

**Note** : Le fichier `render.yaml` est déjà configuré dans votre repo.

---

### 3. Fly.io (Gratuit avec limitations)

**Gratuit :**
- ✅ 3 VMs gratuites partagées
- ✅ 160GB sortie/mois
- ✅ Pas besoin de carte pour commencer

**Avantages :**
- ✅ Persistance avec volumes
- ✅ Bonne performance
- ✅ Support repos privés

**Instructions :**
1. Installer Fly CLI : https://fly.io/docs/getting-started/installing-flyctl/
2. `fly auth signup`
3. `fly launch` (dans le dossier du projet)
4. Suivre les instructions

---

## 🔐 Variables d'Environnement à Configurer

Pour **toutes** les plateformes, ajoutez ces variables :

### Railway
Dans Railway → Variables :
```
RAPIDAPI_KEY = votre_clé_rapidapi
RAPIDAPI_HOST = linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com
OPENAI_API_KEY = votre_clé_openai
APP_PASSWORD_HASH = 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
```

### Render
Dans Render → Environment :
```
RAPIDAPI_KEY = votre_clé_rapidapi
RAPIDAPI_HOST = linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com
OPENAI_API_KEY = votre_clé_openai
APP_PASSWORD_HASH = 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
```

### Fly.io
Dans Fly.io → Secrets :
```bash
fly secrets set RAPIDAPI_KEY="votre_clé"
fly secrets set RAPIDAPI_HOST="linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
fly secrets set OPENAI_API_KEY="votre_clé"
fly secrets set APP_PASSWORD_HASH="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
```

---

## 🎯 Comparaison Rapide

| Plateforme | Gratuit | Carte Requise | Persistance DB | Mise en Veille | Recommandation |
|------------|---------|---------------|----------------|----------------|----------------|
| **Railway** | 500h/mois | Possible | ✅ Oui | ❌ Non | ⭐⭐⭐⭐⭐ |
| **Render** | Illimité | ❌ Non | ✅ Oui | ⚠️ 15 min | ⭐⭐⭐⭐ |
| **Fly.io** | 3 VMs | ❌ Non | ✅ Oui | ❌ Non | ⭐⭐⭐⭐ |
| Streamlit Cloud | Illimité | ❌ Non | ❌ Non | ❌ Non | ⭐⭐ (pas de DB) |

---

## 🚀 Recommandation Finale

### Si vous voulez le MEILLEUR (même si carte requise) :
→ **Railway** : Le plus stable, pas de mise en veille, persistance garantie

### Si vous voulez 100% GRATUIT sans carte :
→ **Render** : Parfait, juste une mise en veille après 15 min (redémarrage en 30s)

### Si vous voulez une alternative moderne :
→ **Fly.io** : Bon compromis, gratuit, performant

---

## 📋 Checklist de Déploiement

- [ ] Choisir une plateforme (Railway ou Render recommandé)
- [ ] Créer un compte
- [ ] Connecter le repo GitHub `wladimir-delcros/radar`
- [ ] Configurer les variables d'environnement
- [ ] Déployer
- [ ] Tester l'application
- [ ] Vérifier que la DB persiste (créer un client, redémarrer, vérifier qu'il existe toujours)

---

## ⚡ Déploiement Express sur Render (5 minutes)

1. **Aller sur** https://render.com/
2. **Se connecter** avec GitHub
3. **New → Web Service**
4. **Sélectionner** `wladimir-delcros/radar`
5. **Configurer** :
   - Name: `leadflow`
   - Build: `pip install -r requirements.txt`
   - Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
6. **Variables** → Ajouter les 4 variables d'environnement
7. **Create Web Service**
8. **Attendre 2-3 minutes** → Votre app est en ligne ! 🎉

---

## 🆘 Besoin d'aide ?

- **Railway** : https://docs.railway.app/
- **Render** : https://render.com/docs
- **Fly.io** : https://fly.io/docs/
