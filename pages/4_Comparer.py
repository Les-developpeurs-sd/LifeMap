"""Page dédiée à la comparaison de deux départements.

Ce module gère la page "Comparer" qui permet aux utilisateurs de :
- Sélectionner deux départements à comparer
- Visualiser une comparaison détaillée des équipements de santé
- Voir les métriques clés pour chaque département (équipements, population, densité)
- Comparer les catégories d'équipements côte à côte
- Obtenir une analyse IA (si configurée) pour aider à la décision

Cette page est utile pour prendre une décision éclairée entre deux options de déménagement.
"""

import streamlit as st

from utils.data_loader import aggregate_department_data
from utils.decider_components import render_comparison
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_comparison_page() -> None:
    """Affiche la page complète dédiée à la comparaison de deux départements.
    
    Cette fonction configure la page et affiche :
    - La configuration de page (titre, icône, layout)
    - La barre de navigation avec "Comparer" comme page active
    - Le titre principal et une description
    - Le sélecteur de deux départements
    - La comparaison détaillée (métriques, graphiques, analyse IA)
    - Le pied de page
    
    Returns:
        None: Affiche directement le contenu dans Streamlit.
    """
    # Configure la page avec un titre, une icône et un layout large
    st.set_page_config(
        page_title="Comparer deux départements",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Injecte le CSS personnalisé pour la barre de navigation
    inject_navbar_css()
    
    # Affiche la barre de navigation avec "Comparer" comme page active
    render_navbar("Comparer")
    
    # Affiche le titre principal de la page
    st.title("🔄 Comparer deux départements")
    
    # Affiche une description de ce que permet cette page
    st.write(
        "Comparez l'offre de soins, les densités par catégorie et le bilan global "
        "de deux départements."
    )
    
    # Charge les données agrégées et affiche l'interface de comparaison
    render_comparison(aggregate_department_data())
    
    # Affiche le pied de page avec les sources des données
    render_footer()


# Point d'entrée du script si exécuté directement
if __name__ == "__main__":
    render_comparison_page()
