"""Styles et navigation communs à toutes les pages de LifeMap : Santé Où Habiter.

Ce module fournit les composants visuels partagés entre toutes les pages :
- L'injection du CSS personnalisé pour le thème de l'application
- La barre de navigation (navbar) avec le logo et les liens vers les pages
- Le pied de page (footer) avec les sources des données

Le thème utilise la police Inter et une palette de couleurs basée sur :
- Bleu principal : #2563eb
- Bleu secondaire : #1d4ed8
- Texte principal : #1e293b
- Texte secondaire : #64748b
- Gris clair : #e2e8f0, #eff6ff
- Fond : #ffffff
"""

import streamlit as st


def inject_navbar_css() -> None:
    """Injecte le thème visuel partagé de l'application.
    
    Cette fonction ajoute une balise <style> avec toutes les règles CSS personnalisées
    pour l'application. Elle configure :
    - La police par défaut (Inter) pour tout le contenu
    - Le style de la barre de navigation
    - Le style des liens de navigation
    - Le style des métriques Streamlit
    - Le style des onglets
    - Le style des boutons
    - Le style des DataFrames
    - Le style des séparateurs (hr)
    - Le style du pied de page
    - Des règles de responsive design
    
    Returns:
        None: Injecte directement le CSS via st.markdown.
    """
    st.markdown(
        """
        <style>
        /* Import de la police Inter depuis Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* Applique la police Inter à tout le contenu */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }
        
        /* Masque la sidebar Streamlit pour un design clean */
        section[data-testid="stSidebar"],
        button[data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Style du conteneur de la navbar */
        .navbar-container {
            border-bottom: 1px solid #e2e8f0;
            margin: -1rem -1rem 1.5rem -1rem;
            padding: 0.6rem 2rem;
            background: #ffffff;
        }
        
        /* Style du texte de la marque (logo) */
        .navbar-brand-text {
            font-size: 1.35rem;
            font-weight: 700;
            color: #1e293b;
            letter-spacing: -0.5px;
            line-height: 2.4rem;
        }
        /* Le span dans le logo est coloré en bleu principal */
        .navbar-brand-text span { color: #2563eb; }
        
        /* Style des liens de navigation */
        [data-testid="stPageLink"] a {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: #64748b !important;
            padding: 0.45rem 0.9rem !important;
            border-radius: 6px !important;
            text-decoration: none !important;
            transition: all 0.2s ease !important;
            border: none !important;
            background: transparent !important;
        }
        
        /* Style au survol et quand la page est active */
        [data-testid="stPageLink"] a:hover,
        [data-testid="stPageLink"] a[aria-current="page"] {
            color: #2563eb !important;
            background: #eff6ff !important;
            font-weight: 600 !important;
        }
        
        /* Style des titres (h1, h2, h3) */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif !important;
            color: #1e293b !important;
            letter-spacing: -0.5px;
        }
        
        /* Style des métriques Streamlit */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.2rem;
            transition: all 0.2s ease;
        }
        
        /* Effet au survol des métriques */
        [data-testid="stMetric"]:hover {
            border-color: #2563eb;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
            transform: translateY(-2px);
        }
        
        /* Style du label des métriques */
        [data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem !important;
            letter-spacing: 0.5px;
        }
        
        /* Style de la valeur des métriques */
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #1e293b !important;
            font-weight: 700;
        }
        
        /* Style des onglets Streamlit */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: transparent;
            border-bottom: 1px solid #e2e8f0;
        }
        
        /* Style des onglets individuels */
        .stTabs [data-baseweb="tab"] {
            color: #64748b;
            font-weight: 500;
            padding: 0.8rem 1.2rem;
            border-bottom: 2px solid transparent;
        }
        
        /* Style de l'onglet sélectionné */
        .stTabs [aria-selected="true"] {
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
            font-weight: 600;
        }
        
        /* Style des boutons Streamlit */
        .stButton > button, .stFormSubmitButton > button {
            background: #2563eb !important;
            color: #ffffff !important;
            font-weight: 600;
            border: none !important;
            border-radius: 8px;
        }
        
        /* Effet au survol des boutons */
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: #1d4ed8 !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        }
        
        /* Style des DataFrames Streamlit */
        [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
        }
        
        /* Style des séparateurs horizontaux */
        hr { border: none; height: 1px; background: #e2e8f0; }
        
        /* Style du pied de page */
        .site-footer {
            text-align: center;
            padding: 2rem 0;
            color: #94a3b8;
            font-size: 0.85rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 2rem;
        }
        
        /* Responsive design : réduit le padding sur mobile */
        @media (max-width: 768px) {
            .navbar-container { padding: 0.6rem 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_navbar(active_page: str = "Accueil") -> None:
    """Affiche la barre de navigation adaptée aux pages actuelles.
    
    Cette fonction crée une barre de navigation avec :
    - Le logo "LifeMap : Santé Où Habiter" à gauche
    - Les liens vers les 4 pages principales à droite
    - Un style cohérent avec le thème de l'application
    
    Args:
        active_page (str): Nom de la page actuellement affichée. 
                           Utilisé pour déterminer quel lien doit être mis en évidence.
                           Valeurs possibles : "Accueil", "Déserts médicaux", 
                           "Où déménager ?", "Comparer".
    
    Returns:
        None: Affiche directement la navbar dans Streamlit.
    """
    # Crée 5 colonnes : 1 pour le logo (2.4x plus large), 4 pour les liens (1x chacun)
    columns = st.columns([2.4, 1, 1, 1, 1])
    
    with columns[0]:
        # Affiche le logo avec le span coloré en bleu
        st.markdown(
            '<div class="navbar-brand-text">🩺 <span>LifeMap</span> : Santé Où Habiter</div>',
            unsafe_allow_html=True,
        )
    
    # Liste des pages avec leurs libellés et chemins
    pages = [
        ("Accueil", "app.py"),
        ("Déserts médicaux", "pages/2_Decider.py"),
        ("Où déménager ?", "pages/3_Demenager.py"),
        ("Comparer", "pages/4_Comparer.py"),
    ]
    
    # Affiche chaque lien dans sa colonne dédiée
    for column, (label, path) in zip(columns[1:], pages):
        with column:
            # Utilise st.page_link pour la navigation entre pages
            st.page_link(path, label=label)
    
    # Ajoute une marge négative pour aligner correctement la navbar
    st.markdown(
        '<div class="navbar-container" style="margin-top:-0.5rem; padding:0;"></div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Affiche le pied de page avec la source principale des données.
    
    Cette fonction affiche un pied de page simple avec les informations
    sur les sources des données utilisées dans l'application.
    
    Returns:
        None: Affiche directement le footer dans Streamlit.
    """
    st.markdown(
        """
        <div class="site-footer">
            Source : Insee, Base permanente des équipements 2025 ·
            Référentiel géographique des départements
        </div>
        """,
        unsafe_allow_html=True,
    )
