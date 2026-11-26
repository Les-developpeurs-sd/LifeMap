"""Page dédiée à l'aide au choix d'un département où déménager.

Ce module gère la page "Où déménager ?" qui aide les utilisateurs à :
- Définir leur profil (famille avec enfants, senior, actif, etc.)
- Sélectionner les professions de santé dont ils ont besoin
- Filtrer les départements selon leurs critères
- Obtenir un classement des départements les mieux dotés
- Visualiser les résultats sur une carte

Cette page est particulièrement utile pour les personnes qui envisagent de déménager
et veulent éviter les zones sous-équipées en soins de santé.
"""

import streamlit as st

from utils.decider_components import build_specialty_table, render_move_tab
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_move_page() -> None:
    """Affiche la page complète dédiée à l'aide au choix de département.
    
    Cette fonction configure la page et affiche :
    - La configuration de page (titre, icône, layout)
    - La barre de navigation avec "Où déménager ?" comme page active
    - Le titre principal et une description
    - L'onglet "Où déménager ?" avec le formulaire et les résultats
    - Le pied de page
    
    Returns:
        None: Affiche directement le contenu dans Streamlit.
    """
    # Configure la page avec un titre, une icône et un layout large
    st.set_page_config(
        page_title="Où déménager ?",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Injecte le CSS personnalisé pour la barre de navigation
    inject_navbar_css()
    
    # Affiche la barre de navigation avec "Où déménager ?" comme page active
    render_navbar("Où déménager ?")
    
    # Affiche le titre principal de la page
    st.title("🧭 Où déménager pour éviter les déserts médicaux ?")

    # Construire la table des spécialités avec les densités et indices calculés
    table, _ = build_specialty_table()
    
    # Affiche l'onglet principal avec le formulaire de critères et les résultats
    render_move_tab(table)
    
    # Affiche le pied de page avec les sources des données
    render_footer()


# Point d'entrée du script si exécuté directement
if __name__ == "__main__":
    render_move_page()
