"""Aide à la décision pour comparer deux départements."""

import streamlit as st
import plotly.express as px

from utils.data_loader import aggregate_department_data, format_number
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_department_card(data, department):
    """Affiche les indicateurs détaillés d'un département.

    Args:
        data: Agrégats de l'offre de soins.
        department: Nom du département à afficher.
    """
    selected = data[data["departement"] == department]
    total = selected["equipements"].sum()
    st.metric("Équipements recensés", format_number(total))
    chart = selected.sort_values("equipements", ascending=True)
    fig = px.bar(
        chart,
        x="equipements",
        y="categorie",
        orientation="h",
        labels={"equipements": "Nombre", "categorie": ""},
        title=f"Profil de {department}",
        template="plotly_white",
        color="equipements",
        color_continuous_scale="Teal",
    )
    st.plotly_chart(fig, width="stretch")


def render_decision() -> None:
    """Permet de comparer deux départements sur leur profil de santé."""
    st.set_page_config(page_title="Choisir un département", page_icon="📍", layout="wide")
    inject_navbar_css()
    render_navbar("Comparer")
    st.title("📍 Comparer deux lieux de vie")
    st.write(
        "La comparaison porte sur les lieux d'exercice et équipements recensés par la BPE. "
        "Elle éclaire l'accessibilité potentielle, sans constituer un avis médical."
    )
    data = aggregate_department_data()
    departments = sorted(data["departement"].dropna().unique())
    if "selected_departments" not in st.session_state:
        st.session_state["selected_departments"] = departments[:2]
    with st.form("department_comparison"):
        first_column, second_column = st.columns(2)
        with first_column:
            st.subheader("📍 Territoire 1")
            first = st.selectbox(
                "Choisissez un département",
                departments,
                index=departments.index(st.session_state["selected_departments"][0]),
            )
        with second_column:
            st.subheader("📍 Territoire 2")
            second = st.selectbox(
                "Choisissez un département",
                departments,
                index=departments.index(st.session_state["selected_departments"][1]),
            )
        submitted = st.form_submit_button("Comparer")
    if submitted:
        st.session_state["selected_departments"] = [first, second]
    first, second = st.session_state["selected_departments"]
    if first == second:
        st.warning("Choisissez deux départements différents.")
        return
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(first)
        render_department_card(data, first)
    with col2:
        st.subheader(second)
        render_department_card(data, second)
    comparison = (
        data[data["departement"].isin([first, second])]
        .pivot_table(index="categorie", columns="departement", values="equipements", fill_value=0)
        .reset_index()
    )
    st.subheader("Comparaison catégorie par catégorie")
    st.dataframe(comparison, hide_index=True, width="stretch")
    st.warning(
        "Limites : la BPE compte des lieux d'exercice, pas nécessairement des personnes uniques. "
        "Les médecins salariés des hôpitaux ne sont pas inclus et le volume brut dépend de la population."
    )
    render_footer()


if __name__ == "__main__":
    render_decision()
