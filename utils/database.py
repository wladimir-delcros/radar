"""
Module de gestion de la base de données SQLite (multi-tenant)
"""
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "linkedin_scraper.db"


def get_db_path():
    """Retourne le chemin de la base de données"""
    return DB_PATH


@contextmanager
def get_connection():
    """Context manager pour obtenir une connexion à la DB"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialise la base de données avec toutes les tables"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Table clients
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                website TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table client_profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL UNIQUE,
                products_services TEXT,
                job_titles TEXT,
                company_types TEXT,
                industries TEXT,
                company_size TEXT,
                geographic_location TEXT,
                pain_points TEXT,
                characteristics TEXT,
                what_offers TEXT,
                value_proposition TEXT,
                ideal_signals TEXT,
                message_tone TEXT,
                message_structure TEXT,
                message_key_points TEXT,
                message_cta TEXT,
                message_example TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Table competitors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                company_url TEXT,
                company_id TEXT,
                company_query TEXT,
                why_contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Table target_persons pour les personnes à scraper
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS target_persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                person_name TEXT,
                profile_url TEXT NOT NULL,
                why_contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Table reactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                competitor_name TEXT,
                post_url TEXT,
                post_date TIMESTAMP,
                reactor_name TEXT,
                reactor_urn TEXT,
                profile_url TEXT,
                reaction_type TEXT,
                headline TEXT,
                profile_picture_url TEXT,
                post_relevant BOOLEAN,
                prospect_relevant BOOLEAN,
                relevance_score REAL,
                relevance_reasoning TEXT,
                personalized_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Index unique pour éviter les doublons
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_reactions_unique
            ON reactions(client_id, reactor_urn, post_url)
        """)

        # Table company_details pour stocker les informations d'entreprise enrichies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT UNIQUE,
                company_name TEXT,
                company_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index pour recherche rapide par company_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_company_details_id
            ON company_details(company_id)
        """)

        # Table edited_messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edited_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                reactor_urn TEXT NOT NULL,
                edited_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(client_id, reactor_urn),
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Table radars
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS radars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                radar_type TEXT NOT NULL,
                target_identifier TEXT NOT NULL,
                target_value TEXT,
                keyword TEXT,
                post_count INTEGER DEFAULT 1,
                enabled BOOLEAN DEFAULT 1,
                last_run_at TIMESTAMP,
                schedule_type TEXT DEFAULT 'manual',
                schedule_interval INTEGER DEFAULT 0,
                targets_json TEXT,
                last_scheduled_run TIMESTAMP,
                filter_competitors BOOLEAN DEFAULT 1,
                min_score_threshold REAL DEFAULT 0.6,
                message_template TEXT,
                max_extractions INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        
        # Migration : ajouter message_template si la colonne n'existe pas
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN message_template TEXT")
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà

        # Table radar_targets pour relations many-to-many
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS radar_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                radar_id INTEGER NOT NULL,
                target_type TEXT NOT NULL,
                target_value TEXT NOT NULL,
                target_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (radar_id) REFERENCES radars(id) ON DELETE CASCADE
            )
        """)

        # Index pour les radars
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_radars_client_enabled
            ON radars(client_id, enabled)
        """)
        
        # Index pour radar_targets
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_radar_targets_radar
            ON radar_targets(radar_id)
        """)
        
        # Migration: Ajouter les nouvelles colonnes si elles n'existent pas
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN schedule_type TEXT DEFAULT 'manual'")
        except sqlite3.OperationalError:
            pass  # Colonne existe déjà
        
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN schedule_interval INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN targets_json TEXT")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN last_scheduled_run TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN filter_competitors BOOLEAN DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN min_score_threshold REAL DEFAULT 0.6")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE radars ADD COLUMN max_extractions INTEGER DEFAULT NULL")
        except sqlite3.OperationalError:
            pass


# ============== CLIENTS ==============

def get_all_clients():
    """Récupère tous les clients"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


def get_client(client_id: int):
    """Récupère un client par son ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_client_by_name(name: str):
    """Récupère un client par son nom"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_client(name: str, description: str = "", website: str = ""):
    """Ajoute un nouveau client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clients (name, description, website) VALUES (?, ?, ?)",
            (name, description, website)
        )
        client_id = cursor.lastrowid
        # Créer un profil vide pour ce client
        cursor.execute(
            "INSERT INTO client_profiles (client_id) VALUES (?)",
            (client_id,)
        )
        return client_id


def update_client(client_id: int, name: str, description: str = "", website: str = ""):
    """Met à jour un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE clients SET name = ?, description = ?, website = ? WHERE id = ?",
            (name, description, website, client_id)
        )
        return cursor.rowcount > 0


def delete_client(client_id: int):
    """Supprime un client (cascade sur toutes les données liées)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        return cursor.rowcount > 0


# ============== CLIENT PROFILES ==============

def get_client_profile(client_id: int):
    """Récupère le profil d'un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM client_profiles WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
        if not row:
            return None

        profile = dict(row)
        # Convertir les champs JSON en listes
        json_fields = [
            'products_services', 'job_titles', 'company_types', 'industries',
            'pain_points', 'characteristics', 'ideal_signals', 'message_key_points'
        ]
        for field in json_fields:
            if profile.get(field):
                try:
                    profile[field] = json.loads(profile[field])
                except json.JSONDecodeError:
                    profile[field] = []
            else:
                profile[field] = []

        return profile


def save_client_profile(client_id: int, profile_data: dict):
    """Sauvegarde le profil d'un client"""
    json_fields = [
        'products_services', 'job_titles', 'company_types', 'industries',
        'pain_points', 'characteristics', 'ideal_signals', 'message_key_points'
    ]

    # Convertir les listes en JSON
    data = profile_data.copy()
    for field in json_fields:
        if field in data and isinstance(data[field], list):
            data[field] = json.dumps(data[field], ensure_ascii=False)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE client_profiles SET
                products_services = ?,
                job_titles = ?,
                company_types = ?,
                industries = ?,
                company_size = ?,
                geographic_location = ?,
                pain_points = ?,
                characteristics = ?,
                what_offers = ?,
                value_proposition = ?,
                ideal_signals = ?,
                message_tone = ?,
                message_structure = ?,
                message_key_points = ?,
                message_cta = ?,
                message_example = ?
            WHERE client_id = ?
        """, (
            data.get('products_services', '[]'),
            data.get('job_titles', '[]'),
            data.get('company_types', '[]'),
            data.get('industries', '[]'),
            data.get('company_size', ''),
            data.get('geographic_location', ''),
            data.get('pain_points', '[]'),
            data.get('characteristics', '[]'),
            data.get('what_offers', ''),
            data.get('value_proposition', ''),
            data.get('ideal_signals', '[]'),
            data.get('message_tone', ''),
            data.get('message_structure', ''),
            data.get('message_key_points', '[]'),
            data.get('message_cta', ''),
            data.get('message_example', ''),
            client_id
        ))
        return cursor.rowcount > 0


def get_client_profile_as_dict(client_id: int):
    """Récupère le profil d'un client au format JSON compatible avec l'ancien format"""
    client = get_client(client_id)
    profile = get_client_profile(client_id)
    competitors = get_competitors(client_id)

    if not client or not profile:
        return None

    return {
        "company_name": client['name'],
        "company_description": client['description'] or '',
        "website": client['website'] or '',
        "products_services": profile.get('products_services', []),
        "target_persona": {
            "job_titles": profile.get('job_titles', []),
            "company_types": profile.get('company_types', []),
            "industries": profile.get('industries', []),
            "company_size": profile.get('company_size', ''),
            "geographic_location": profile.get('geographic_location', ''),
            "pain_points": profile.get('pain_points', []),
            "characteristics": profile.get('characteristics', [])
        },
        "competitor_companies": {
            "scraped_companies": [c['company_name'] for c in competitors],
            "why_contact_on_their_posts": competitors[0]['why_contact'] if competitors else ''
        },
        "outreach_strategy": {
            "what_offers": profile.get('what_offers', ''),
            "value_proposition": profile.get('value_proposition', ''),
            "ideal_signals": profile.get('ideal_signals', []),
            "message_template": {
                "tone": profile.get('message_tone', ''),
                "structure": profile.get('message_structure', ''),
                "key_points": profile.get('message_key_points', []),
                "call_to_action": profile.get('message_cta', ''),
                "example": profile.get('message_example', '')
            }
        }
    }


# ============== COMPETITORS ==============

def get_competitors(client_id: int):
    """Récupère les concurrents d'un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM competitors WHERE client_id = ? ORDER BY company_name",
            (client_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def add_competitor(client_id: int, company_name: str, company_url: str = "",
                   company_id: str = "", company_query: str = "", why_contact: str = ""):
    """Ajoute un concurrent"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO competitors (client_id, company_name, company_url, company_id, company_query, why_contact)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, company_name, company_url, company_id, company_query, why_contact))
        return cursor.lastrowid


def update_competitor(competitor_id: int, company_name: str, company_url: str = "",
                      company_id: str = "", company_query: str = "", why_contact: str = ""):
    """Met à jour un concurrent"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE competitors SET
                company_name = ?, company_url = ?, company_id = ?, company_query = ?, why_contact = ?
            WHERE id = ?
        """, (company_name, company_url, company_id, company_query, why_contact, competitor_id))
        return cursor.rowcount > 0


def delete_competitor(competitor_id: int):
    """Supprime un concurrent"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
        return cursor.rowcount > 0


# ============== TARGET PERSONS ==============

def get_target_persons(client_id: int):
    """Récupère les personnes à scraper d'un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM target_persons WHERE client_id = ? ORDER BY person_name, profile_url",
            (client_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def add_target_person(client_id: int, profile_url: str, person_name: str = "", why_contact: str = ""):
    """Ajoute une personne à scraper"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO target_persons (client_id, profile_url, person_name, why_contact)
            VALUES (?, ?, ?, ?)
        """, (client_id, profile_url, person_name, why_contact))
        return cursor.lastrowid


def update_target_person(person_id: int, profile_url: str = None, person_name: str = None, why_contact: str = None):
    """Met à jour une personne à scraper"""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if profile_url is not None:
            updates.append("profile_url = ?")
            params.append(profile_url)
        if person_name is not None:
            updates.append("person_name = ?")
            params.append(person_name)
        if why_contact is not None:
            updates.append("why_contact = ?")
            params.append(why_contact)
        
        if not updates:
            return False
        
        params.append(person_id)
        cursor.execute(f"UPDATE target_persons SET {', '.join(updates)} WHERE id = ?", params)
        return cursor.rowcount > 0


def delete_target_person(person_id: int):
    """Supprime une personne à scraper"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM target_persons WHERE id = ?", (person_id,))
        return cursor.rowcount > 0


def get_persons_from_radars(client_id: int):
    """Récupère les personnes utilisées dans les radars de type person_last_post"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT 
                target_value as profile_url,
                name as radar_name,
                id as radar_id
            FROM radars 
            WHERE client_id = ? 
            AND radar_type = 'person_last_post'
            AND target_value IS NOT NULL 
            AND target_value != ''
            UNION
            SELECT DISTINCT
                rt.target_value as profile_url,
                r.name as radar_name,
                r.id as radar_id
            FROM radar_targets rt
            JOIN radars r ON rt.radar_id = r.id
            WHERE r.client_id = ?
            AND r.radar_type = 'person_last_post'
            AND rt.target_type = 'person'
            AND rt.target_value IS NOT NULL
            AND rt.target_value != ''
        """, (client_id, client_id))
        return [dict(row) for row in cursor.fetchall()]


def sync_persons_from_radars(client_id: int):
    """Synchronise les personnes des radars vers la table target_persons"""
    persons_from_radars = get_persons_from_radars(client_id)
    existing_persons = get_target_persons(client_id)
    existing_urls = {p['profile_url'] for p in existing_persons}
    
    synced_count = 0
    for person_data in persons_from_radars:
        profile_url = person_data['profile_url']
        if profile_url not in existing_urls:
            # Extraire le nom d'utilisateur de l'URL si possible
            person_name = None
            if '/in/' in profile_url:
                username = profile_url.split('/in/')[-1].split('/')[0].split('?')[0]
                person_name = username.replace('-', ' ').title()
            
            add_target_person(
                client_id=client_id,
                profile_url=profile_url,
                person_name=person_name,
                why_contact=f"Sync depuis le radar: {person_data.get('radar_name', 'N/A')}"
            )
            synced_count += 1
            existing_urls.add(profile_url)  # Pour éviter les doublons dans cette session
    
    return synced_count


# ============== REACTIONS ==============

def get_reactions(client_id: int = None):
    """Récupère les réactions, optionnellement filtrées par client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if client_id:
            cursor.execute("""
                SELECT * FROM reactions
                WHERE client_id = ?
                ORDER BY post_date DESC
            """, (client_id,))
        else:
            cursor.execute("SELECT * FROM reactions ORDER BY post_date DESC")
        return [dict(row) for row in cursor.fetchall()]


def save_reaction(client_id: int, reaction_data: dict):
    """Sauvegarde une réaction (upsert)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reactions (
                client_id, competitor_name, post_url, post_date, reactor_name,
                reactor_urn, profile_url, reaction_type, headline, profile_picture_url,
                post_relevant, prospect_relevant, relevance_score, relevance_reasoning,
                personalized_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(client_id, reactor_urn, post_url) DO UPDATE SET
                competitor_name = excluded.competitor_name,
                post_date = excluded.post_date,
                reactor_name = excluded.reactor_name,
                profile_url = excluded.profile_url,
                reaction_type = excluded.reaction_type,
                headline = excluded.headline,
                profile_picture_url = excluded.profile_picture_url,
                post_relevant = excluded.post_relevant,
                prospect_relevant = excluded.prospect_relevant,
                relevance_score = excluded.relevance_score,
                relevance_reasoning = excluded.relevance_reasoning,
                personalized_message = excluded.personalized_message
        """, (
            client_id,
            reaction_data.get('company_name', reaction_data.get('competitor_name', '')),
            reaction_data.get('post_url', ''),
            reaction_data.get('post_date', ''),
            reaction_data.get('reactor_name', ''),
            reaction_data.get('reactor_urn', ''),
            reaction_data.get('profile_url', ''),
            reaction_data.get('reaction_type', ''),
            reaction_data.get('headline', ''),
            reaction_data.get('profile_picture_url', ''),
            reaction_data.get('post_relevant', False),
            reaction_data.get('prospect_relevant', False),
            reaction_data.get('relevance_score', 0.0),
            reaction_data.get('relevance_reasoning', ''),
            reaction_data.get('personalized_message', '')
        ))
        return cursor.lastrowid


def save_reactions_batch(client_id: int, reactions: list):
    """Sauvegarde plusieurs réactions en batch"""
    for reaction in reactions:
        save_reaction(client_id, reaction)


def delete_reaction(client_id: int, reactor_urn: str, post_url: str):
    """
    Supprime une réaction (prospect) de la base de données
    
    Args:
        client_id: ID du client
        reactor_urn: URN du prospect (reactor_urn)
        post_url: URL du post
    
    Returns:
        True si la suppression a réussi, False sinon
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM reactions WHERE client_id = ? AND reactor_urn = ? AND post_url = ?",
            (client_id, reactor_urn, post_url)
        )
        return cursor.rowcount > 0


def delete_reactions_batch(client_id: int, reactions_data: list):
    """
    Supprime plusieurs réactions en batch
    
    Args:
        client_id: ID du client
        reactions_data: Liste de dicts avec 'reactor_urn' et 'post_url'
    
    Returns:
        Nombre de réactions supprimées
    """
    deleted_count = 0
    for reaction_data in reactions_data:
        reactor_urn = reaction_data.get('reactor_urn', '')
        post_url = reaction_data.get('post_url', '')
        if reactor_urn and post_url:
            if delete_reaction(client_id, reactor_urn, post_url):
                deleted_count += 1
    return deleted_count


# ============== EDITED MESSAGES ==============

def get_edited_messages(client_id: int):
    """Récupère les messages édités pour un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reactor_urn, edited_message FROM edited_messages WHERE client_id = ?",
            (client_id,)
        )
        return {row['reactor_urn']: row['edited_message'] for row in cursor.fetchall()}


def save_edited_message(client_id: int, reactor_urn: str, message: str):
    """Sauvegarde un message édité"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO edited_messages (client_id, reactor_urn, edited_message, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(client_id, reactor_urn) DO UPDATE SET
                edited_message = excluded.edited_message,
                updated_at = excluded.updated_at
        """, (client_id, reactor_urn, message, datetime.now().isoformat()))
        return cursor.lastrowid


def delete_edited_message(client_id: int, reactor_urn: str):
    """Supprime un message édité (restaure l'original)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM edited_messages WHERE client_id = ? AND reactor_urn = ?",
            (client_id, reactor_urn)
        )
        return cursor.rowcount > 0


# ============== RADARS ==============

def get_radars(client_id: int):
    """Récupère tous les radars d'un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM radars WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_radar(radar_id: int):
    """Récupère un radar par son ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM radars WHERE id = ?", (radar_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_enabled_radars(client_id: int):
    """Récupère uniquement les radars activés d'un client"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM radars WHERE client_id = ? AND enabled = 1 ORDER BY created_at DESC",
            (client_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def add_radar(client_id: int, name: str, radar_type: str, target_identifier: str,
              target_value: str = None, keyword: str = None, post_count: int = 1,
              schedule_type: str = 'manual', schedule_interval: int = 0,
              filter_competitors: bool = True, min_score_threshold: float = 0.6,
              max_extractions: int = None):
    """
    Ajoute un nouveau radar
    
    Args:
        client_id: ID du client
        name: Nom du radar
        radar_type: Type de radar ('competitor_last_post', 'person_last_post', 'keyword_posts')
        target_identifier: Identifiant de la cible (nom entreprise, profil personne, etc.)
        target_value: Valeur de la cible (optionnel, selon le type)
        keyword: Mot-clé pour les radars de type 'keyword_posts'
        post_count: Nombre de posts à récupérer (pour keyword_posts)
        schedule_type: Type de planification ('manual', 'minutes', 'hours', 'days')
        schedule_interval: Intervalle de planification
        filter_competitors: Activer le filtrage des concurrents
        min_score_threshold: Score minimum pour qualifier un prospect
        max_extractions: Nombre maximum de prospects à extraire par exécution (None = illimité)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO radars (client_id, name, radar_type, target_identifier, target_value, 
                               keyword, post_count, schedule_type, schedule_interval, 
                               filter_competitors, min_score_threshold, max_extractions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (client_id, name, radar_type, target_identifier, target_value, keyword, post_count,
              schedule_type, schedule_interval, 1 if filter_competitors else 0, min_score_threshold, max_extractions))
        return cursor.lastrowid


# Objet sentinel pour distinguer "non fourni" de "None"
_SENTINEL = object()

def update_radar(radar_id: int, name: str = None, enabled: bool = None,
                target_identifier: str = None, target_value: str = None,
                keyword: str = None, post_count: int = None,
                schedule_type: str = None, schedule_interval: int = None,
                filter_competitors: bool = None, min_score_threshold: float = None,
                max_extractions = _SENTINEL):
    """Met à jour un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if target_identifier is not None:
            updates.append("target_identifier = ?")
            params.append(target_identifier)
        if target_value is not None:
            updates.append("target_value = ?")
            params.append(target_value)
        if keyword is not None:
            updates.append("keyword = ?")
            params.append(keyword)
        if post_count is not None:
            updates.append("post_count = ?")
            params.append(post_count)
        if schedule_type is not None:
            updates.append("schedule_type = ?")
            params.append(schedule_type)
        if schedule_interval is not None:
            updates.append("schedule_interval = ?")
            params.append(schedule_interval)
        if filter_competitors is not None:
            updates.append("filter_competitors = ?")
            params.append(1 if filter_competitors else 0)
        if min_score_threshold is not None:
            updates.append("min_score_threshold = ?")
            params.append(min_score_threshold)
        # max_extractions peut être None (pour supprimer la limite) ou un nombre
        # On utilise un sentinel pour distinguer "non fourni" de "None"
        if max_extractions is not _SENTINEL:
            updates.append("max_extractions = ?")
            params.append(max_extractions)
        
        if not updates:
            return False
        
        params.append(radar_id)
        cursor.execute(
            f"UPDATE radars SET {', '.join(updates)} WHERE id = ?",
            params
        )
        return cursor.rowcount > 0


def update_radar_last_run(radar_id: int, scheduled: bool = False):
    """Met à jour la date de dernière exécution d'un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        if scheduled:
            cursor.execute(
                "UPDATE radars SET last_run_at = ?, last_scheduled_run = ? WHERE id = ?",
                (now, now, radar_id)
            )
        else:
            cursor.execute(
                "UPDATE radars SET last_run_at = ? WHERE id = ?",
                (now, radar_id)
            )
        return cursor.rowcount > 0


def delete_radar(radar_id: int):
    """Supprime un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM radars WHERE id = ?", (radar_id,))
        return cursor.rowcount > 0


# ============== RADAR TARGETS ==============

def get_radar_targets(radar_id: int):
    """Récupère toutes les cibles d'un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM radar_targets WHERE radar_id = ? ORDER BY target_order",
            (radar_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_radar_message_template(radar_id: int) -> Optional[str]:
    """Récupère le message template d'un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT message_template FROM radars WHERE id = ?", (radar_id,))
        row = cursor.fetchone()
        return row['message_template'] if row and row['message_template'] else None


def save_radar_message_template(radar_id: int, message_template: str):
    """Sauvegarde le message template d'un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE radars SET message_template = ? WHERE id = ?",
            (message_template, radar_id)
        )


def update_profile_url_with_real_slug(client_id: int, reactor_urn: str, real_profile_url: str) -> bool:
    """
    Met à jour l'URL du profil avec le vrai slug (au lieu de l'ID/URN)
    
    Args:
        client_id: ID du client
        reactor_urn: URN du prospect
        real_profile_url: URL complète avec le vrai slug
    
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reactions
            SET profile_url = ?
            WHERE client_id = ? AND reactor_urn = ?
        """, (real_profile_url, client_id, reactor_urn))
        return cursor.rowcount > 0


def check_prospect_exists(client_id: int, reactor_urn: str) -> bool:
    """
    Vérifie si un prospect existe déjà dans la base de données pour ce client
    
    Args:
        client_id: ID du client
        reactor_urn: URN du prospect
    
    Returns:
        True si le prospect existe déjà, False sinon
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM reactions
            WHERE client_id = ? AND reactor_urn = ?
        """, (client_id, reactor_urn))
        return cursor.fetchone()[0] > 0


def save_company_detail(company_id: str, company_name: str, company_data: Dict[str, Any]) -> bool:
    """
    Sauvegarde les détails d'une entreprise dans la base de données
    
    Args:
        company_id: Identifiant unique de l'entreprise (peut être le nom, URN, etc.)
        company_name: Nom de l'entreprise
        company_data: Dictionnaire contenant toutes les données de l'entreprise
    
    Returns:
        True si la sauvegarde a réussi, False sinon
    """
    import json
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            company_data_json = json.dumps(company_data)
            cursor.execute("""
                INSERT INTO company_details (company_id, company_name, company_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(company_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    company_data = excluded.company_data,
                    updated_at = CURRENT_TIMESTAMP
            """, (company_id, company_name, company_data_json))
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des détails d'entreprise: {e}")
            return False


def get_company_detail_from_db(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les détails d'une entreprise depuis la base de données
    
    Args:
        company_id: Identifiant unique de l'entreprise
    
    Returns:
        Dict contenant les données de l'entreprise ou None si non trouvé
    """
    import json
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT company_data FROM company_details WHERE company_id = ?
        """, (company_id,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return None
        return None


def get_existing_prospect_urns(client_id: int) -> set:
    """
    Récupère tous les reactor_urn existants pour un client (pour déduplication rapide)
    
    Args:
        client_id: ID du client
    
    Returns:
        Set de reactor_urn existants
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT reactor_urn FROM reactions
            WHERE client_id = ? AND reactor_urn IS NOT NULL AND reactor_urn != ''
        """, (client_id,))
        return {row[0] for row in cursor.fetchall()}


def get_reactions_with_id_profile_urls(client_id: int) -> List[dict]:
    """
    Récupère toutes les réactions qui ont des profile_url avec des IDs/URNs (commençant par ACo ou urn:)
    
    Args:
        client_id: ID du client
    
    Returns:
        Liste de dictionnaires contenant les réactions avec des IDs dans profile_url
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM reactions
            WHERE client_id = ?
            AND profile_url LIKE '%/in/ACo%'
        """, (client_id,))
        return [dict(row) for row in cursor.fetchall()]


def find_radar_by_identifier(client_id: int, company_name: str = None, keyword: str = None) -> Optional[dict]:
    """
    Trouve un radar par son identifiant (company_name pour competitor_last_post, keyword pour keyword_posts)
    Utilise une recherche exacte puis une recherche partielle si nécessaire
    
    Args:
        client_id: ID du client
        company_name: Nom de l'entreprise (pour radar_type='competitor_last_post')
        keyword: Mot-clé (pour radar_type='keyword_posts')
    
    Returns:
        Dict du radar ou None
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if company_name:
            # Chercher d'abord par correspondance exacte
            cursor.execute("""
                SELECT * FROM radars 
                WHERE client_id = ? 
                AND radar_type = 'competitor_last_post' 
                AND target_identifier = ?
                LIMIT 1
            """, (client_id, company_name))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # Si pas trouvé, chercher par correspondance partielle (insensible à la casse)
            cursor.execute("""
                SELECT * FROM radars 
                WHERE client_id = ? 
                AND radar_type = 'competitor_last_post' 
                AND LOWER(target_identifier) LIKE LOWER(?)
                LIMIT 1
            """, (client_id, f'%{company_name}%'))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # Chercher aussi dans l'autre sens (si company_name contient target_identifier)
            cursor.execute("""
                SELECT * FROM radars 
                WHERE client_id = ? 
                AND radar_type = 'competitor_last_post' 
                AND LOWER(?) LIKE LOWER('%' || target_identifier || '%')
                LIMIT 1
            """, (client_id, company_name))
            row = cursor.fetchone()
            if row:
                return dict(row)
        
        if keyword:
            # Chercher d'abord par correspondance exacte
            cursor.execute("""
                SELECT * FROM radars 
                WHERE client_id = ? 
                AND radar_type = 'keyword_posts' 
                AND keyword = ?
                LIMIT 1
            """, (client_id, keyword))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            # Si pas trouvé, chercher par correspondance partielle (insensible à la casse)
            cursor.execute("""
                SELECT * FROM radars 
                WHERE client_id = ? 
                AND radar_type = 'keyword_posts' 
                AND LOWER(keyword) LIKE LOWER(?)
                LIMIT 1
            """, (client_id, f'%{keyword}%'))
            row = cursor.fetchone()
            if row:
                return dict(row)
        
        return None


def add_radar_target(radar_id: int, target_type: str, target_value: str, target_order: int = 0):
    """Ajoute une cible à un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO radar_targets (radar_id, target_type, target_value, target_order)
            VALUES (?, ?, ?, ?)
        """, (radar_id, target_type, target_value, target_order))
        return cursor.lastrowid


def delete_radar_targets(radar_id: int):
    """Supprime toutes les cibles d'un radar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM radar_targets WHERE radar_id = ?", (radar_id,))
        return cursor.rowcount >= 0


def get_scheduled_radars(client_id: int = None):
    """Récupère tous les radars avec scheduling activé"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if client_id:
            cursor.execute("""
                SELECT * FROM radars 
                WHERE enabled = 1 AND schedule_type != 'manual' AND schedule_interval > 0
                AND client_id = ?
                ORDER BY last_scheduled_run ASC NULLS FIRST
            """, (client_id,))
        else:
            cursor.execute("""
                SELECT * FROM radars 
                WHERE enabled = 1 AND schedule_type != 'manual' AND schedule_interval > 0
                ORDER BY last_scheduled_run ASC NULLS FIRST
            """)
        return [dict(row) for row in cursor.fetchall()]


# ============== MIGRATION ==============

def migrate_from_csv():
    """Migre les données existantes des CSV vers SQLite"""
    import pandas as pd
    from pathlib import Path

    data_dir = Path(__file__).parent.parent / "data"

    # Vérifier si la migration a déjà été faite
    clients = get_all_clients()
    if clients:
        return False  # Déjà migré

    # Créer le client Uclic
    profile_path = Path(__file__).parent.parent / "company_profile.json"
    if profile_path.exists():
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_json = json.load(f)

        client_id = add_client(
            name=profile_json.get('company_name', 'Uclic'),
            description=profile_json.get('company_description', ''),
            website=profile_json.get('website', '')
        )

        # Migrer le profil
        target = profile_json.get('target_persona', {})
        outreach = profile_json.get('outreach_strategy', {})
        template = outreach.get('message_template', {})

        save_client_profile(client_id, {
            'products_services': profile_json.get('products_services', []),
            'job_titles': target.get('job_titles', []),
            'company_types': target.get('company_types', []),
            'industries': target.get('industries', []),
            'company_size': target.get('company_size', ''),
            'geographic_location': target.get('geographic_location', ''),
            'pain_points': target.get('pain_points', []),
            'characteristics': target.get('characteristics', []),
            'what_offers': outreach.get('what_offers', ''),
            'value_proposition': outreach.get('value_proposition', ''),
            'ideal_signals': outreach.get('ideal_signals', []),
            'message_tone': template.get('tone', ''),
            'message_structure': template.get('structure', ''),
            'message_key_points': template.get('key_points', []),
            'message_cta': template.get('call_to_action', ''),
            'message_example': template.get('example', '')
        })

        # Migrer les concurrents depuis company_profile.json
        competitors_data = profile_json.get('competitor_companies', {})
        why_contact = competitors_data.get('why_contact_on_their_posts', '')
        for company in competitors_data.get('scraped_companies', []):
            add_competitor(client_id, company, why_contact=why_contact)
    else:
        client_id = add_client(name='Uclic')

    # Migrer companies_to_follow.csv
    companies_csv = Path(__file__).parent.parent / "companies_to_follow.csv"
    if companies_csv.exists():
        df = pd.read_csv(companies_csv)
        for _, row in df.iterrows():
            # Vérifier si ce concurrent existe déjà
            existing = get_competitors(client_id)
            if not any(c['company_name'] == row.get('company_name', '') for c in existing):
                add_competitor(
                    client_id=client_id,
                    company_name=row.get('company_name', ''),
                    company_url=row.get('company_url', ''),
                    company_id=str(row.get('company_id', '')),
                    company_query=row.get('company_query', '')
                )

    # Migrer les réactions CSV
    csv_files = list(data_dir.glob("all_reactions_*.csv"))
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            for _, row in df.iterrows():
                save_reaction(client_id, row.to_dict())
        except Exception as e:
            print(f"Erreur migration {csv_file}: {e}")

    # Migrer edited_messages.json
    edited_path = data_dir / "edited_messages.json"
    if edited_path.exists():
        with open(edited_path, 'r', encoding='utf-8') as f:
            edited = json.load(f)
        for reactor_urn, message in edited.items():
            save_edited_message(client_id, reactor_urn, message)

    return True


# Initialiser la DB au chargement du module
init_db()
