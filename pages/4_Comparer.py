"""Page dédiée à la comparaison de deux départements."""

import streamlit as st

from utils.data_loader import aggregate_department_data
from utils.decider_components import render_comparison
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_comparison_page() -> None:
    st.set_page_config(
        page_title="Comparer deux départements",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Comparer")
    st.title("🔄 Comparer deux départements")
    st.write(
        "Comparez l'offre de soins, les densités par catégorie et le bilan global "
        "de deux départements."
    )
    render_comparison(aggregate_department_data())
    render_footer()


if __name__ == "__main__":
    render_comparison_page()
