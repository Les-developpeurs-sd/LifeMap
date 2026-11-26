"""Accueil de l'application LifeMap : Santé Où Habiter."""

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
    """Affiche la synthèse nationale et la méthode de lecture des résultats."""
    st.set_page_config(
        page_title="LifeMap : Santé Où Habiter",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Accueil")
    col_text, col_img = st.columns([1, 1])

    with col_text:
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
        try:
            st.image("city_skyline.png", use_container_width=True)
        except Exception:
            pass

    st.divider()

    render_explorer_content()
    render_footer()


if __name__ == "__main__":
    render_home()
