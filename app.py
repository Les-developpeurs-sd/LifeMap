"""Accueil de l'application Santé Où Habiter."""

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
        page_title="Santé Où Habiter",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Accueil")
    st.title("🩺 Santé Où Habiter")
    st.subheader("Où faut-il habiter par rapport au médical et à la santé ?")
    st.write(
        "Cette application compare l'offre de soins des départements français. "
        "Elle aide à repérer les territoires les mieux dotés, en distinguant "
        "les professionnels, les établissements et les pharmacies."
    )

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
