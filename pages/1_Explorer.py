"""Exploration filtrée de l'offre de soins."""

import streamlit as st
import plotly.express as px

from utils.data_loader import (
    aggregate_department_data,
    format_number,
    load_department_geojson,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def apply_filters(data):
    """Filtre les agrégats selon les choix validés par l'utilisateur.

    Args:
        data: Agrégats de l'offre de soins.

    Returns:
        Sous-ensemble filtré.
    """
    region_options = {"Toutes les régions": None}
    for row in data[["REG", "region"]].drop_duplicates().sort_values("region").itertuples():
        if row.region:
            region_options[f"{row.region} ({row.REG})"] = row.REG
    categories = ["Toutes"] + sorted(data["categorie"].unique())
    with st.form("filters"):
        region_label = st.selectbox("Région administrative", list(region_options))
        category = st.selectbox("Type d'offre", categories)
        minimum = st.slider("Nombre minimum d'équipements", 0, 5000, 0, step=10)
        submitted = st.form_submit_button("Appliquer les filtres")
    if submitted:
        st.session_state["last_filters"] = {
            "region": region_options[region_label],
            "category": category,
            "minimum": minimum,
        }
    selected = st.session_state.get(
        "last_filters", {"region": None, "category": "Toutes", "minimum": 0}
    )
    filtered = data.copy()
    if selected["region"] is not None:
        filtered = filtered[filtered["REG"] == selected["region"]]
    if selected["category"] != "Toutes":
        filtered = filtered[filtered["categorie"] == selected["category"]]
    return filtered[filtered["equipements"] >= selected["minimum"]]


def render_explorer() -> None:
    """Affiche les filtres, le classement et les graphiques d'exploration."""
    st.set_page_config(page_title="Explorer l'offre", page_icon="🔎", layout="wide")
    inject_navbar_css()
    render_navbar("Explorer")
    st.title("🔎 Explorer l'offre de soins")
    st.write("Validez plusieurs critères en une seule fois grâce au formulaire.")
    data = aggregate_department_data()
    filtered = apply_filters(data)
    if filtered.empty:
        st.warning("Aucun résultat avec ces filtres.")
        return
    ranking = (
        filtered.groupby(["code_departement", "departement"], as_index=False)["equipements"]
        .sum()
        .sort_values("equipements", ascending=False)
    )
    st.metric("Départements affichés", format_number(len(ranking)))
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            ranking.head(20).sort_values("equipements"),
            x="equipements",
            y="departement",
            orientation="h",
            labels={"equipements": "Équipements", "departement": ""},
            template="plotly_white",
            color="equipements",
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        category_data = (
            filtered.groupby("categorie", as_index=False)["equipements"]
            .sum()
            .sort_values("equipements", ascending=False)
        )
        fig = px.pie(
            category_data,
            values="equipements",
            names="categorie",
            title="Répartition par type d'offre",
            hole=0.45,
        )
        st.plotly_chart(fig, width="stretch")
    map_data = (
        filtered.groupby(["code_departement", "departement"], as_index=False)["equipements"]
        .sum()
    )
    st.subheader("Carte départementale")
    fig_map = px.choropleth_map(
        map_data,
        geojson=load_department_geojson(),
        locations="code_departement",
        featureidkey="properties.code",
        color="equipements",
        hover_name="departement",
        color_continuous_scale="Teal",
        center={"lat": 46.6, "lon": 2.4},
        zoom=4.8,
        map_style="carto-positron",
        labels={"equipements": "Équipements"},
    )
    fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_map, width="stretch")
    st.dataframe(ranking, hide_index=True, width="stretch")
    render_footer()


if __name__ == "__main__":
    render_explorer()
