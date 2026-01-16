"""
Page Scraper - Controle et monitoring du scraper
"""
import streamlit as st
import subprocess
import threading
import queue
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.session import render_client_selector
from utils.database import get_client, get_competitors
from utils.styles import render_page_header, render_empty_state

st.set_page_config(page_title="Scraper | LeadFlow", page_icon="🎯", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Scraper",
    f"Lancer et monitorer le scraper LinkedIn - {client['name'] if client else ''}"
)

# Etat du scraper dans session_state
if 'scraper_running' not in st.session_state:
    st.session_state.scraper_running = False
if 'scraper_logs' not in st.session_state:
    st.session_state.scraper_logs = []

# Fonction pour lire les logs
def read_logs(log_queue, log_file):
    """Lit les logs depuis le fichier et les met dans la queue"""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            # Aller a la fin du fichier
            f.seek(0, 2)
            while st.session_state.scraper_running:
                line = f.readline()
                if line:
                    log_queue.put(line.strip())
                else:
                    time.sleep(0.5)
    except Exception as e:
        log_queue.put(f"Erreur de lecture des logs: {e}")

# Interface de lancement
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">Lancer le Scraper</div>
        </div>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    # Charger les concurrents depuis SQLite
    competitors = get_competitors(client_id)

    if competitors:
        company_options = [c['company_name'] for c in competitors]
        selected_companies = st.multiselect("Concurrents a traiter", company_options, default=company_options)
    else:
        st.warning("Aucun concurrent configure. Allez dans Configuration > Concurrents pour en ajouter.")
        selected_companies = []

with col2:
    enable_ai = st.checkbox("Activer l'analyse IA", value=True)

# Boutons de controle
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Lancer le Scraper", disabled=st.session_state.scraper_running or not selected_companies):
        if not selected_companies:
            st.error("Selectionnez au moins un concurrent")
        else:
            st.session_state.scraper_running = True
            st.session_state.scraper_logs = []
            st.success("Scraper lance!")
            st.info("Le scraper s'execute en arriere-plan. Consultez les logs ci-dessous.")
            st.rerun()

with col2:
    if st.button("Arreter", disabled=not st.session_state.scraper_running):
        st.session_state.scraper_running = False
        st.warning("Arret demande")
        st.rerun()

with col3:
    if st.button("Actualiser"):
        st.cache_data.clear()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Logs
st.markdown("""
    <div class="data-card">
        <div class="data-card-header">
            <div class="data-card-title">Logs en Temps Reel</div>
        </div>
    </div>
""", unsafe_allow_html=True)

log_file = Path("linkedin_scraper_company.log")

if log_file.exists():
    # Afficher les dernieres lignes du log
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            last_lines = lines[-100:] if len(lines) > 100 else lines
            log_text = ''.join(last_lines)
            st.code(log_text, language=None)
    except Exception as e:
        st.error(f"Erreur lors de la lecture des logs: {e}")
else:
    st.info("Aucun fichier de log trouve. Lancez le scraper pour voir les logs.")

# Instructions
st.markdown("---")
st.info(f"""
**Instructions:**
- Pour lancer le scraper manuellement : `python linkedin_scraper_company.py --client-id {client_id}`
- Les logs sont mis a jour en temps reel
- Utilisez le bouton "Actualiser" pour mettre a jour les donnees apres l'execution
""")
