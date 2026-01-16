"""
Module de gestion de la session Streamlit (client actif) - Version moderne
"""
import streamlit as st
from utils.database import get_all_clients, add_client, init_db, migrate_from_csv
from utils.styles import inject_modern_css, render_logo


def init_session():
    """Initialise la session et retourne le client actif"""
    # S'assurer que la DB est initialisee et migree
    init_db()
    migrate_from_csv()

    # Recuperer les clients
    clients = get_all_clients()

    # Si aucun client, creer un client par defaut
    if not clients:
        add_client("Mon Entreprise", "Description de l'entreprise", "")
        clients = get_all_clients()

    # Initialiser le client actif dans la session
    if 'active_client_id' not in st.session_state:
        st.session_state.active_client_id = clients[0]['id']

    # Verifier que le client actif existe toujours
    client_ids = [c['id'] for c in clients]
    if st.session_state.active_client_id not in client_ids:
        st.session_state.active_client_id = clients[0]['id']

    return clients


def render_client_selector():
    """Affiche le selecteur de client moderne dans la sidebar et retourne le client_id actif"""
    clients = init_session()

    # Injecter les styles CSS modernes
    inject_modern_css()

    with st.sidebar:
        # Logo
        render_logo()

        # Navigation personnalisee
        st.page_link("app.py", label="🏠 Accueil", use_container_width=True)
        st.page_link("pages/1_📊_Dashboard.py", label="📊 Dashboard", use_container_width=True)
        st.page_link("pages/2_👥_Prospects.py", label="👥 Prospects", use_container_width=True)
        st.page_link("pages/3_💬_Messages.py", label="💬 Messages", use_container_width=True)
        st.page_link("pages/7_🎯_Radars.py", label="🎯 Radars", use_container_width=True)
        st.page_link("pages/8_👤_Persona.py", label="👤 Persona", use_container_width=True)
        st.page_link("pages/5_📈_Statistiques.py", label="📈 Statistiques", use_container_width=True)
        st.page_link("pages/6_⚙️_Configuration.py", label="⚙️ Configuration", use_container_width=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # Workspace selector
        st.markdown("""
            <div class="workspace-selector">
                <div class="workspace-label">Workspace</div>
            </div>
        """, unsafe_allow_html=True)

        # Creer un dictionnaire pour le selectbox
        client_options = {c['name']: c['id'] for c in clients}
        client_names = list(client_options.keys())

        # Trouver l'index du client actif
        current_client = next(
            (c for c in clients if c['id'] == st.session_state.active_client_id),
            clients[0]
        )
        current_index = client_names.index(current_client['name'])

        # Selecteur
        selected_name = st.selectbox(
            "Client",
            client_names,
            index=current_index,
            key="client_selector",
            label_visibility="collapsed"
        )

        # Mettre a jour le client actif
        st.session_state.active_client_id = client_options[selected_name]

        # Statut
        st.markdown("""
            <div style="display: flex; align-items: center; padding: 0.5rem 0; color: #64748b; font-size: 0.75rem;">
                <span class="status-dot online"></span>
                <span>Connecte</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # Footer
        st.markdown("""
            <div style="position: absolute; bottom: 1rem; left: 1rem; right: 1rem;">
                <div class="divider"></div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0;">
                    <span class="version-badge">v2.0</span>
                    <span style="color: #475569; font-size: 0.7rem;">LeadFlow</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    return st.session_state.active_client_id


def get_active_client_id():
    """Retourne l'ID du client actif"""
    if 'active_client_id' not in st.session_state:
        init_session()
    return st.session_state.active_client_id
