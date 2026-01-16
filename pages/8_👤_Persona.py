"""
Page Persona - Gestion du profil entreprise et persona cible
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from utils.auth import require_auth
from utils.session import render_client_selector
from utils.database import (
    get_client, get_client_profile, save_client_profile, update_client,
    get_competitors, add_competitor, delete_competitor,
    get_target_persons, add_target_person, delete_target_person,
    get_persons_from_radars, sync_persons_from_radars,
    get_radars, get_radar_message_template, save_radar_message_template,
    get_client_profile_as_dict
)
from utils.ai_analyzer import openai_client, OPENAI_ENABLED, OPENAI_MODEL
from utils.styles import render_page_header

st.set_page_config(page_title="Persona | LeadFlow", page_icon="👤", layout="wide")

# Vérifier l'authentification
require_auth()

# Selecteur de client
client_id = render_client_selector()
client = get_client(client_id)

# Header
render_page_header(
    "Persona",
    f"Profil entreprise et persona cible - {client['name'] if client else ''}"
)

profile = get_client_profile(client_id) or {}

# Fonctions helper
def list_to_text(lst):
    return "\n".join(lst) if lst else ""

def text_to_list(txt):
    return [line.strip() for line in txt.split("\n") if line.strip()]

# Onglets
tab1, tab2, tab3, tab4 = st.tabs(["📋 Infos & Services", "🎯 Persona Cible", "💬 Stratégie Outreach", "🏢 Concurrents"])

# ============== ONGLET 1: Infos & Services ==============
with tab1:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">Informations Générales</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Informations de l'entreprise")

    # Mettre a jour les infos du client
    company_name = st.text_input("Nom de l'entreprise",
                                 value=client['name'] if client else '',
                                 key="company_name_persona")

    company_description = st.text_area("Description de l'entreprise",
                                       value=client.get('description', '') if client else '',
                                       height=100,
                                       key="company_description_persona")

    website = st.text_input("Site web",
                            value=client.get('website', '') if client else '',
                            key="website_persona")

    st.markdown("### Produits & Services")
    st.caption("Un élément par ligne")
    products_services_text = st.text_area("Produits et services",
                                           value=list_to_text(profile.get('products_services', [])),
                                           height=150,
                                           key="products_services_persona")

# ============== ONGLET 2: Persona Cible ==============
with tab2:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">Persona Cible</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Titres de poste cibles")
        st.caption("Un titre par ligne")
        job_titles_text = st.text_area("Titres",
                                       value=list_to_text(profile.get('job_titles', [])),
                                       height=150,
                                       key="job_titles_persona")

        st.markdown("### Types d'entreprises")
        st.caption("Un type par ligne")
        company_types_text = st.text_area("Types",
                                          value=list_to_text(profile.get('company_types', [])),
                                          height=100,
                                          key="company_types_persona")

        st.markdown("### Taille d'entreprise")
        company_size = st.text_input("Taille (ex: 10-500 employés)",
                                     value=profile.get('company_size', ''),
                                     key="company_size_persona")

    with col2:
        st.markdown("### Secteurs d'activité")
        st.caption("Un secteur par ligne")
        industries_text = st.text_area("Secteurs",
                                       value=list_to_text(profile.get('industries', [])),
                                       height=150,
                                       key="industries_persona")

        st.markdown("### Localisation géographique")
        geographic_location = st.text_input("Localisation",
                                            value=profile.get('geographic_location', ''),
                                            key="geographic_location_persona")

        st.markdown("### Pain Points")
        st.caption("Un pain point par ligne")
        pain_points_text = st.text_area("Pain points",
                                        value=list_to_text(profile.get('pain_points', [])),
                                        height=100,
                                        key="pain_points_persona")

    st.markdown("### Caractéristiques")
    st.caption("Une caractéristique par ligne")
    characteristics_text = st.text_area("Caractéristiques",
                                        value=list_to_text(profile.get('characteristics', [])),
                                        height=100,
                                        key="characteristics_persona")

# ============== ONGLET 3: Stratégie Outreach ==============
with tab3:
    st.markdown("""
        <div class="data-card">
            <div class="data-card-header">
                <div class="data-card-title">Stratégie Outreach</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Offre")
    what_offers = st.text_area("Ce que vous offrez",
                               value=profile.get('what_offers', ''),
                               height=80,
                               key="what_offers_persona")

    st.markdown("### Proposition de valeur")
    value_proposition = st.text_area("Proposition de valeur",
                                     value=profile.get('value_proposition', ''),
                                     height=100,
                                     key="value_proposition_persona")

    st.markdown("### Signaux idéaux")
    st.caption("Un signal par ligne")
    ideal_signals_text = st.text_area("Signaux",
                                      value=list_to_text(profile.get('ideal_signals', [])),
                                      height=120,
                                      key="ideal_signals_persona")

    st.markdown("---")
    st.markdown("### Template de Message")

    col1, col2 = st.columns(2)

    with col1:
        tone = st.text_input("Ton",
                             value=profile.get('message_tone', ''),
                             key="tone_persona")

        structure = st.text_input("Structure",
                                  value=profile.get('message_structure', ''),
                                  key="structure_persona")

        call_to_action = st.text_input("Call to Action",
                                       value=profile.get('message_cta', ''),
                                       key="call_to_action_persona")

    with col2:
        st.markdown("**Points clés**")
        st.caption("Un point par ligne")
        key_points_text = st.text_area("Points clés",
                                       value=list_to_text(profile.get('message_key_points', [])),
                                       height=100,
                                       key="key_points_persona",
                                       label_visibility="collapsed")

    st.markdown("### Exemple de message")
    example = st.text_area("Exemple",
                           value=profile.get('message_example', ''),
                           height=100,
                           key="example_persona")
    
    st.markdown("---")
    st.markdown("### 💬 Messages par Radar")
    st.caption("Messages types configurés pour chaque radar. Ces messages sont utilisés comme base pour générer les messages personnalisés des prospects de chaque radar.")
    
    # Récupérer tous les radars
    radars = get_radars(client_id)
    
    if radars:
        # Bouton pour générer automatiquement les messages types manquants
        radars_without_message = [r for r in radars if not get_radar_message_template(r.get('id'))]
        
        if radars_without_message:
            col_gen1, col_gen2 = st.columns([3, 1])
            with col_gen2:
                if st.button("✨ Générer les messages manquants (IA)", type="primary", use_container_width=True):
                    company_profile = get_client_profile_as_dict(client_id)
                    if not company_profile:
                        st.error("❌ Profil entreprise non trouvé. Configurez d'abord le persona.")
                    elif not OPENAI_ENABLED or not openai_client:
                        st.error("❌ OpenAI non configuré. Configurez OpenAI dans la page Configuration.")
                    else:
                        with st.spinner(f"Génération de {len(radars_without_message)} message(s) type en cours..."):
                            success_count = 0
                            error_count = 0
                            
                            for radar in radars_without_message:
                                try:
                                    # Préparer les informations du radar
                                    radar_type = radar.get('radar_type', '')
                                    radar_name = radar.get('name', 'Sans nom')
                                    target_identifier = radar.get('target_identifier', '')
                                    keyword = radar.get('keyword', '')
                                    
                                    # Construire le contexte selon le type de radar
                                    if radar_type == 'competitor_last_post':
                                        context = f"Radar sur les derniers posts du concurrent '{target_identifier}'. Les prospects réagissent aux posts de cette entreprise."
                                    elif radar_type == 'person_last_post':
                                        context = f"Radar sur les derniers posts de la personne '{target_identifier}'. Les prospects réagissent aux posts de cette personne."
                                    elif radar_type == 'keyword_posts':
                                        context = f"Radar sur les posts contenant le mot-clé '{keyword}'. Les prospects réagissent à des posts sur ce sujet."
                                    else:
                                        context = f"Radar '{radar_name}' de type '{radar_type}'."
                                    
                                    # Générer le message type avec IA
                                    prompt = f"""Tu es un expert en outbound B2B. Génère un message type (template) LinkedIn pour ce radar.

Contexte du radar:
{context}

Notre entreprise:
- Nom: {company_profile.get('company_name', '')}
- Description: {company_profile.get('company_description', '')}
- Ce qu'on offre: {company_profile.get('outreach_strategy', {}).get('what_offers', '')}
- Proposition de valeur: {company_profile.get('outreach_strategy', {}).get('value_proposition', '')}

Persona cible:
- Titres de poste: {', '.join(company_profile.get('target_persona', {}).get('job_titles', []))}
- Secteurs: {', '.join(company_profile.get('target_persona', {}).get('industries', []))}
- Pain points: {', '.join(company_profile.get('target_persona', {}).get('pain_points', []))}

Template de message général:
- Ton: {profile.get('message_tone', 'professionnel, amical')}
- Structure: {profile.get('message_structure', '')}
- Points clés: {', '.join(profile.get('message_key_points', []))}

Génère un message type (template) court (maximum 100 mots) en français qui:
1. Fait référence à la réaction du prospect sur le post du radar
2. Connecte avec notre solution en se basant sur le persona
3. Pose une question ouverte pertinente
4. Est naturel, personnel et engageant

Utilise des variables comme [entreprise], [sujet], [notre entreprise], [prospect] pour la personnalisation future.

Réponds UNIQUEMENT avec le message type, sans markdown, sans "Message:", sans guillemets."""
                                    
                                    response = openai_client.chat.completions.create(
                                        model=OPENAI_MODEL,
                                        messages=[
                                            {"role": "system", "content": "Tu es un expert en rédaction de messages outbound B2B. Réponds UNIQUEMENT avec le message final, sans formatage supplémentaire."},
                                            {"role": "user", "content": prompt}
                                        ],
                                        temperature=0.7,
                                        max_tokens=200
                                    )
                                    
                                    generated_template = response.choices[0].message.content.strip()
                                    
                                    # Nettoyer le message
                                    if generated_template.startswith('"') and generated_template.endswith('"'):
                                        generated_template = generated_template[1:-1]
                                    if generated_template.startswith("Message:"):
                                        generated_template = generated_template[8:].strip()
                                    
                                    if generated_template:
                                        save_radar_message_template(radar.get('id'), generated_template)
                                        success_count += 1
                                    else:
                                        error_count += 1
                                        
                                except Exception as e:
                                    error_count += 1
                                    st.error(f"Erreur pour le radar '{radar.get('name')}': {e}")
                            
                            if success_count > 0:
                                st.success(f"✅ {success_count} message(s) type généré(s) avec succès!")
                            if error_count > 0:
                                st.warning(f"⚠️ {error_count} erreur(s) lors de la génération")
                            
                            st.cache_data.clear()
                            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Afficher les radars avec leurs messages
        for radar in radars:
            radar_message_template = get_radar_message_template(radar.get('id'))
            
            # Déterminer le type de radar pour l'affichage
            radar_type_label = {
                'competitor_last_post': '📊 Concurrent',
                'person_last_post': '👤 Personne',
                'keyword_posts': '🔍 Mot-clé'
            }.get(radar.get('radar_type', ''), '🎯')
            
            # Déterminer la cible pour l'affichage
            target_display = radar.get('target_identifier', 'N/A')
            if radar.get('radar_type') == 'keyword_posts' and radar.get('keyword'):
                target_display = radar.get('keyword')
            
            with st.expander(f"{radar_type_label} {radar.get('name', 'Sans nom')} - {target_display}", expanded=False):
                if radar_message_template:
                    edited_template = st.text_area(
                        "Message type",
                        value=radar_message_template,
                        height=120,
                        key=f"radar_msg_edit_{radar.get('id')}",
                        help="Ce message type est utilisé pour générer les messages personnalisés des prospects de ce radar. Vous pouvez le modifier ici."
                    )
                    
                    col_save_msg, col_info_msg = st.columns([1, 3])
                    with col_save_msg:
                        if st.button("💾 Sauvegarder", key=f"save_radar_msg_{radar.get('id')}", use_container_width=True):
                            if edited_template != radar_message_template:
                                save_radar_message_template(radar.get('id'), edited_template)
                                st.success("✅ Message type sauvegardé!")
                                st.rerun()
                            else:
                                st.info("Aucune modification")
                    with col_info_msg:
                        st.caption(f"💡 Ce message type est utilisé pour tous les prospects du radar '{radar.get('name')}'.")
                else:
                    st.info("💡 Aucun message type configuré pour ce radar. Cliquez sur 'Générer les messages manquants' ci-dessus pour en créer un automatiquement.")
    else:
        st.info("📝 Aucun radar configuré. Créez des radars dans la page Radars pour avoir des messages types spécifiques.")

# ============== ONGLET 4: Concurrents ==============
with tab4:
    # Sous-onglets pour Concurrents et Personnes
    sub_tab1, sub_tab2 = st.tabs(["🏢 Concurrents", "👤 Personnes à Scraper"])
    
    # ============== SOUS-ONGLET 1: Concurrents ==============
    with sub_tab1:
        st.markdown("""
            <div class="data-card">
                <div class="data-card-header">
                    <div class="data-card-title">Concurrents à Scraper</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        competitors = get_competitors(client_id)

        # Liste des concurrents
        if competitors:
            st.markdown("### Liste des concurrents")
            for comp in competitors:
                with st.expander(f"{comp['company_name']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**URL:** {comp.get('company_url', 'N/A')}")
                        st.write(f"**ID:** {comp.get('company_id', 'N/A')}")
                        st.write(f"**Query:** {comp.get('company_query', 'N/A')}")
                        if comp.get('why_contact'):
                            st.write(f"**Raison:** {comp.get('why_contact')}")
                    with col2:
                        if st.button("🗑️ Supprimer", key=f"del_comp_persona_{comp['id']}"):
                            delete_competitor(comp['id'])
                            st.rerun()
        else:
            st.info("Aucun concurrent configuré. Ajoutez-en ci-dessous.")

        st.markdown("---")

        # Ajouter un concurrent
        st.markdown("### Ajouter un concurrent")
        with st.form("add_competitor_form_persona"):
            col1, col2 = st.columns(2)

            with col1:
                new_comp_name = st.text_input("Nom de l'entreprise", placeholder="ex: Growthroom")
                new_comp_url = st.text_input("URL LinkedIn", placeholder="https://www.linkedin.com/company/...")

            with col2:
                new_comp_id = st.text_input("ID LinkedIn", placeholder="Optionnel")
                new_comp_query = st.text_input("Query", placeholder="Optionnel")

            new_comp_why = st.text_area("Pourquoi contacter sur leurs posts?", height=100, placeholder="Expliquez pourquoi vous souhaitez contacter les personnes engagées sur leurs posts...")

            if st.form_submit_button("➕ Ajouter le concurrent", use_container_width=True):
                if new_comp_name:
                    add_competitor(
                        client_id=client_id,
                        company_name=new_comp_name,
                        company_url=new_comp_url,
                        company_id=new_comp_id,
                        company_query=new_comp_query,
                        why_contact=new_comp_why
                    )
                    st.success(f"✅ Concurrent '{new_comp_name}' ajouté!")
                    st.rerun()
                else:
                    st.error("Le nom du concurrent est requis")
    
    # ============== SOUS-ONGLET 2: Personnes à Scraper ==============
    with sub_tab2:
        st.markdown("""
            <div class="data-card">
                <div class="data-card-header">
                    <div class="data-card-title">Personnes à Scraper</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        target_persons = get_target_persons(client_id)
        persons_from_radars = get_persons_from_radars(client_id)
        
        # Vérifier s'il y a des personnes dans les radars qui ne sont pas dans target_persons
        existing_urls = {p['profile_url'] for p in target_persons}
        persons_to_sync = [p for p in persons_from_radars if p['profile_url'] not in existing_urls]
        
        # Afficher un message si des personnes sont disponibles dans les radars
        if persons_to_sync:
            st.info(f"📊 {len(persons_to_sync)} personne(s) trouvée(s) dans vos radars mais pas encore synchronisée(s). Cliquez sur le bouton ci-dessous pour les ajouter automatiquement.")
            if st.button("🔄 Synchroniser depuis les Radars", key="sync_persons_from_radars", use_container_width=True):
                synced_count = sync_persons_from_radars(client_id)
                if synced_count > 0:
                    st.success(f"✅ {synced_count} personne(s) synchronisée(s) avec succès!")
                    st.rerun()
                else:
                    st.info("Aucune nouvelle personne à synchroniser.")
        
        # Liste des personnes
        if target_persons:
            st.markdown("### Liste des personnes")
            for person in target_persons:
                person_display_name = person.get('person_name') or person.get('profile_url', 'Personne sans nom')
                with st.expander(f"👤 {person_display_name}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**URL:** {person.get('profile_url', 'N/A')}")
                        if person.get('person_name'):
                            st.write(f"**Nom:** {person.get('person_name')}")
                        if person.get('why_contact'):
                            st.write(f"**Raison:** {person.get('why_contact')}")
                    with col2:
                        if st.button("🗑️ Supprimer", key=f"del_person_persona_{person['id']}"):
                            delete_target_person(person['id'])
                            st.rerun()
        else:
            if persons_from_radars:
                st.info(f"💡 Vous avez {len(persons_from_radars)} personne(s) dans vos radars. Utilisez le bouton de synchronisation ci-dessus pour les ajouter ici.")
            else:
                st.info("Aucune personne configurée. Ajoutez-en ci-dessous ou créez un radar de type 'Dernier post personne'.")

        st.markdown("---")

        # Ajouter une personne
        st.markdown("### Ajouter une personne")
        with st.form("add_person_form_persona"):
            new_person_name = st.text_input("Nom de la personne (optionnel)", placeholder="ex: John Doe")
            new_person_url = st.text_input(
                "URL LinkedIn du profil", 
                placeholder="https://www.linkedin.com/in/john-doe/",
                help="URL complète du profil LinkedIn"
            )
            new_person_why = st.text_area(
                "Pourquoi scraper cette personne?", 
                height=100, 
                placeholder="Expliquez pourquoi vous souhaitez scraper les engagements de cette personne..."
            )

            if st.form_submit_button("➕ Ajouter la personne", use_container_width=True):
                if new_person_url:
                    # Extraire le nom d'utilisateur de l'URL si possible
                    if not new_person_name and '/in/' in new_person_url:
                        username = new_person_url.split('/in/')[-1].split('/')[0].split('?')[0]
                        new_person_name = username.replace('-', ' ').title()
                    
                    add_target_person(
                        client_id=client_id,
                        profile_url=new_person_url,
                        person_name=new_person_name,
                        why_contact=new_person_why
                    )
                    display_name = new_person_name or new_person_url
                    st.success(f"✅ Personne '{display_name}' ajoutée!")
                    st.rerun()
                else:
                    st.error("L'URL du profil LinkedIn est requise")

# Bouton de sauvegarde du profil (affiché pour tous les onglets)
st.markdown("---")
col_save, _ = st.columns([1, 3])
with col_save:
    if st.button("💾 Sauvegarder le Profil", type="primary", use_container_width=True, key="save_profile_persona"):
        # Mettre a jour le client
        update_client(client_id, company_name, company_description, website)

        # Mettre a jour le profil
        profile_data = {
            'products_services': text_to_list(products_services_text),
            'job_titles': text_to_list(job_titles_text),
            'company_types': text_to_list(company_types_text),
            'industries': text_to_list(industries_text),
            'company_size': company_size,
            'geographic_location': geographic_location,
            'pain_points': text_to_list(pain_points_text),
            'characteristics': text_to_list(characteristics_text),
            'what_offers': what_offers,
            'value_proposition': value_proposition,
            'ideal_signals': text_to_list(ideal_signals_text),
            'message_tone': tone,
            'message_structure': structure,
            'message_key_points': text_to_list(key_points_text),
            'message_cta': call_to_action,
            'message_example': example
        }

        if save_client_profile(client_id, profile_data):
            st.success("✅ Profil sauvegardé avec succès!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Erreur lors de la sauvegarde")
