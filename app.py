"""Accueil de l'application LifeMap : Santé Où Habiter."""

import streamlit as st
import plotly.express as px

from utils.data_loader import (
    aggregate_department_data,
    format_number,
    load_department_reference,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar


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


    data = aggregate_department_data()
    departments = load_department_reference()
    total = int(data["equipements"].sum())
    categories = data["categorie"].nunique()
    department_count = data["code_departement"].nunique()
    first, second, third = st.columns(3)
    first.metric("Équipements de santé analysés", format_number(total))
    second.metric("Départements observés", format_number(department_count))
    third.metric("Catégories comparées", format_number(categories))

    st.divider()
    st.header("Une première réponse")
    department_totals = (
        data.groupby(["code_departement", "departement"], as_index=False)["equipements"]
        .sum()
        .sort_values("equipements", ascending=False)
    )
    top = department_totals.iloc[0]
    low = department_totals.iloc[-1]
    st.info(
        f"En volume brut, **{top['departement']}** concentre le plus d'équipements "
        f"({format_number(top['equipements'])}). À l'inverse, **{low['departement']}** "
        f"en compte {format_number(low['equipements'])}. Ce classement doit être "
        "recalculé en densité dès qu'une population de référence est disponible."
    )

    chart_data = department_totals.head(15).sort_values("equipements")
    fig = px.bar(
        chart_data,
        x="equipements",
        y="departement",
        orientation="h",
        title="Les 15 départements avec le plus d'équipements recensés",
        labels={"equipements": "Nombre de lieux ou équipements", "departement": ""},
        template="plotly_white",
        color="equipements",
        color_continuous_scale="Teal",
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Source principale : Insee, Base permanente des équipements 2025. "
        "La carte des départements sert de référentiel géographique."
    )
    render_footer()


if __name__ == "__main__":
    render_home()
