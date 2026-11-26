"""Page dédiée aux déserts médicaux.

Ce module gère la page "Déserts médicaux" qui permet aux utilisateurs de :
- Visualiser les déserts médicaux par spécialité (médecin généraliste, pédiatre, etc.)
- Analyser où se trouvent les déserts médicaux en France
- Identifier les départements qui cumulent plusieurs déserts
- Comprendre les facteurs qui créent des déserts médicaux

La page utilise les données de la BPE (Base Permanente des Équipements) 2025.
"""

import streamlit as st

from utils.decider_components import (
    build_specialty_table,
    render_desert_cumulation,
    render_desert_overview,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_deserts_page() -> None:
    """Affiche la page complète dédiée à l'analyse des déserts médicaux.
    
    Cette fonction configure la page et affiche :
    - La configuration de page (titre, icône, layout)
    - La barre de navigation avec "Déserts médicaux" comme page active
    - Le titre principal de la page
    - L'aperçu des déserts par profession (carte + métriques)
    - L'analyse des départements qui cumulent les déserts
    - Le pied de page
    
    Returns:
        None: Affiche directement le contenu dans Streamlit.
    """
    # Configure la page avec un titre, une icône et un layout large
    st.set_page_config(
        page_title="Déserts médicaux",
        page_icon="🏜️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Injecte le CSS personnalisé pour la barre de navigation
    inject_navbar_css()
    
    # Affiche la barre de navigation avec "Déserts médicaux" comme page active
    render_navbar("Déserts médicaux")
    
    # Affiche le titre principal de la page
    st.title("🏜️ Déserts médicaux")

    # Construire la table des spécialités avec les densités calculées
    # build_specialty_table() retourne un tuple (table, checks) mais on n'utilise que la table ici
    table, _ = build_specialty_table()
    
    # Affiche l'aperçu des déserts par profession (carte interactive + métriques)
    render_desert_overview(table)
    
    # Affiche une ligne de séparation visuelle
    st.divider()
    
    # Affiche l'analyse des départements qui cumulent plusieurs déserts
    render_desert_cumulation(table)
    
    # Affiche le pied de page avec les sources des données
    render_footer()


# Point d'entrée du script si exécuté directement
if __name__ == "__main__":
    render_deserts_page()
