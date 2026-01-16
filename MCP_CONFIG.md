# Configuration MCP pour LinkedIn Scraper API

Pour configurer le MCP (Model Context Protocol) pour LinkedIn Scraper API dans Cursor:

## Étape 1: Accéder aux paramètres Cursor

1. Ouvrez Cursor
2. Allez dans **File > Preferences > Settings** (ou `Ctrl+,`)
3. Cherchez "MCP" ou "Model Context Protocol"

## Étape 2: Ajouter la configuration MCP

Dans les paramètres Cursor, ajoutez cette configuration dans la section MCP:

```json
{
  "mcpServers": {
    "RapidAPI Hub - LinkedIn Scraper API (Real-time & Fast & Affordable)": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.rapidapi.com",
        "--header",
        "x-api-host: linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com",
        "--header",
        "x-api-key: 8d94f2d4b9msh384e09aab682e2bp173e86jsn7b448f5e8961"
      ]
    }
  }
}
```

## Alternative: Fichier de configuration

Si Cursor supporte les fichiers de configuration MCP, créez un fichier `.cursor/mcp.json` (créer le dossier `.cursor` s'il n'existe pas) avec le contenu ci-dessus.

## Vérification

Après configuration, redémarrez Cursor. Le MCP devrait être disponible pour accéder à l'API LinkedIn Scraper.
