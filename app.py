"""Accueil de l'application LifeMap : Santé Où Habiter.

Ce module est le point d'entrée principal de l'application. Il configure la page
principal (Accueil) et affiche :
- Le titre et la description de l'application
- L'image d'illustration (city_skyline.png)
- Le contenu de l'explorateur d'offre de soins (via render_explorer_content)
- Le pied de page

L'application utilise Streamlit pour l'interface et Plotly pour les visualisations.
"""

import streamlit as st
import plotly.express as px

from utils.data_loader import (
    aggregate_department_data,
    format_number,
    load_department_reference,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar
from utils.explorer_components import render_explorer_content


def render_home() -> None:
    """Affiche la page d'accueil de l'application LifeMap.
    
    Cette fonction configure et affiche la page d'accueil avec :
    - Une configuration de page (titre, icône, layout)
    - L'injection du CSS personnalisé pour la barre de navigation
    - La barre de navigation avec l'onglet "Accueil" actif
    - Un titre principal et une description centrés
    - Une image d'illustration (si disponible)
    - Un séparateur visuel
    - Le contenu de l'explorateur d'offre de soins
    - Le pied de page
    
    Returns:
        None: Affiche directement le contenu dans Streamlit.
    """
    # Configure la page avec un titre, une icône, un layout large et la sidebar masquée par défaut
    st.set_page_config(
        page_title="LifeMap : Santé Où Habiter",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Injecte le CSS personnalisé pour la barre de navigation (couleurs, polices, etc.)
    inject_navbar_css()
    
    # Affiche la barre de navigation avec "Accueil" comme page active
    render_navbar("Accueil")
    
    # Crée deux colonnes pour organiser le titre/description et l'image
    col_text, col_img = st.columns([1, 1])

    with col_text:
        # Affiche le titre et la description centrés avec un padding vertical
        st.markdown("""
        <div style="text-align:center; padding-top:9rem; padding-bottom:0.5rem;">
            <h1 style="font-size:2.2rem; font-weight:700; color:#1e293b; margin:0; letter-spacing:-1px;">
                Votre prochain chez-vous grâce à la santé, éviter les déserts médicaux
            </h1>
            <p style="color:#64748b; font-size:1.05rem; margin-top:0.5rem;">
                Découverte des départements français pour les comparer et analyser les déserts médicaux.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_img:
        # Affiche l'image d'illustration si elle existe, sinon ignore l'erreur
        try:
            st.image("city_skyline.png", use_container_width=True)
        except Exception:
            # Si le fichier image n'existe pas ou ne peut pas être chargé, ne rien afficher
            pass

    # Affiche une ligne de séparation visuelle
    st.divider()

    # Affiche le contenu principal de la page : l'explorateur d'offre de soins
    render_explorer_content()
    
    # Affiche le pied de page avec les sources des données
    render_footer()


# Point d'entrée du script si exécuté directement
if __name__ == "__main__":
    render_home()
