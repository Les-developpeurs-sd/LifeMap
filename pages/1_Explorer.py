"""Exploration filtrée de l'offre de soins."""

import streamlit as st
import plotly.express as px

from utils.data_loader import (
    aggregate_department_data,
    format_number,
    load_department_geojson,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def get_filter_params(data):
    """Récupère les paramètres de filtrage validés dans le formulaire."""
    region_options = {"Toutes les régions": None}
    for row in data[["REG", "region"]].drop_duplicates().sort_values("region").itertuples():
        if row.region:
            region_options[f"{row.region} ({row.REG})"] = row.REG

    categories = ["Toutes"] + sorted(data["categorie"].unique())

    with st.form("filters"):
        region_label = st.selectbox("Région administrative", list(region_options))
        category = st.selectbox("Type d'offre", categories)
        minimum, maximum = st.slider(
            "Nombre d'équipements par département (min - max)",
            min_value=0,
            max_value=25000,
            value=(0, 25000),
            step=10,
        )
        submitted = st.form_submit_button("Appliquer les filtres")

    if submitted:
        st.session_state["last_filters"] = {
            "region": region_options[region_label],
            "category": category,
            "minimum": minimum,
            "maximum": maximum,
        }

    return st.session_state.get(
        "last_filters",
        {"region": None, "category": "Toutes", "minimum": 0, "maximum": 25000},
    )


def apply_row_filters(data, selected):
    """Filtre les lignes selon la région et la catégorie."""
    filtered = data.copy()
    if selected["region"] is not None:
        filtered = filtered[filtered["REG"] == selected["region"]]
    if selected["category"] != "Toutes":
        filtered = filtered[filtered["categorie"] == selected["category"]]
    return filtered


def render_explorer() -> None:
    """Affiche les filtres, le classement et les graphiques d'exploration."""
    st.set_page_config(page_title="Explorer l'offre", page_icon="🔎", layout="wide")
    inject_navbar_css()
    render_navbar("Explorer")
    st.title("🔎 Explorer l'offre de soins")
    st.write("Validez plusieurs critères en une seule fois grâce au formulaire.")

    data = aggregate_department_data()
    selected = get_filter_params(data)
    filtered_rows = apply_row_filters(data, selected)

    # 1. Agrégation par département puis filtrage sur le total min - max
    dept_totals = (
        filtered_rows.groupby(["code_departement", "departement"], as_index=False)["equipements"]
        .sum()
    )
    valid_depts = dept_totals[
        (dept_totals["equipements"] >= selected["minimum"])
        & (dept_totals["equipements"] <= selected["maximum"])
    ]

    if valid_depts.empty:
        st.warning("Aucun résultat avec ces filtres.")
        return

    # On restreint aussi les lignes aux départements retenus pour garder le camembert cohérent
    filtered = filtered_rows[
        filtered_rows["code_departement"].isin(valid_depts["code_departement"])
    ]

    ranking = valid_depts.sort_values("equipements", ascending=False)
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

    st.subheader("Carte départementale")
    fig_map = px.choropleth_map(
        ranking,
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
