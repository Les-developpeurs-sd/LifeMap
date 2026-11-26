"""Exploration filtrée de l'offre de soins.

Ce module gère l'affichage et le filtrage des données d'équipements de santé
par département en France. Il permet aux utilisateurs de filtrer par région,
catégorie d'équipement, et nombre d'équipements, puis visualise les résultats
à travers des graphiques interactifs (barres, camembert, carte choroplèthe).
"""

import streamlit as st
import plotly.express as px

from utils.data_loader import (
    aggregate_department_data,
    format_number,
    load_department_geojson,
)


def get_filter_params(data):
    """Récupère et gère les paramètres de filtrage sélectionnés par l'utilisateur.
    
    Cette fonction affiche un formulaire Streamlit avec des contrôles pour :
    - Sélectionner une région administrative (ou "Toutes les régions")
    - Sélectionner un type d'offre de soins (ou "Toutes")
    - Définir une plage de nombre d'équipements (min - max)
    
    Les paramètres validés sont stockés dans st.session_state['last_filters']
    pour persister entre les interactions.
    
    Args:
        data (pd.DataFrame): DataFrame contenant les données d'équipements avec les colonnes
                             'REG', 'region', et 'categorie'.
    
    Returns:
        dict: Dictionnaire contenant les filtres appliqués avec les clés :
              - 'region': Code de la région sélectionnée (None pour toutes)
              - 'category': Catégorie sélectionnée ("Toutes" pour toutes)
              - 'minimum': Valeur minimale du slider d'équipements
              - 'maximum': Valeur maximale du slider d'équipements
    """
    # Crée un dictionnaire d'options de région avec "Toutes les régions" comme première option
    region_options = {"Toutes les régions": None}
    
    # Récupère les régions uniques depuis les données et les ajoute au dictionnaire
    # drop_duplicates() supprime les doublons, sort_values() trie par nom de région
    for row in data[["REG", "region"]].drop_duplicates().sort_values("region").itertuples():
        if row.region:
            # Formate l'option comme "NomRégion (CODE)" avec le code REG comme valeur
            region_options[f"{row.region} ({row.REG})"] = row.REG

    # Crée la liste des catégories avec "Toutes" en première position
    categories = ["Toutes"] + sorted(data["categorie"].unique())

    # Crée un formulaire Streamlit pour regrouper les contrôles
    with st.form("filters"):
        # Sélecteur de région - utilise les clés du dictionnaire region_options
        region_label = st.selectbox("Région administrative", list(region_options))
        
        # Sélecteur de catégorie
        category = st.selectbox("Type d'offre", categories)
        
        # Slider pour définir la plage de nombre d'équipements
        minimum, maximum = st.slider(
            "Nombre d'équipements par département (min - max)",
            min_value=0,
            max_value=25000,
            value=(0, 25000),
            step=10,  # Incrément de 10
        )
        
        # Bouton de validation du formulaire
        submitted = st.form_submit_button("Appliquer les filtres")

    # Si le formulaire est validé, stocke les paramètres dans la session
    if submitted:
        st.session_state["last_filters"] = {
            "region": region_options[region_label],  # Récupère le code REG ou None
            "category": category,
            "minimum": minimum,
            "maximum": maximum,
        }

    # Retourne les derniers filtres validés, ou les valeurs par défaut si aucun filtre n'a été appliqué
    return st.session_state.get(
        "last_filters",
        {"region": None, "category": "Toutes", "minimum": 0, "maximum": 25000},
    )


def apply_row_filters(data, selected):
    """Applique les filtres de région et de catégorie aux données.
    
    Cette fonction filtre le DataFrame en fonction des critères sélectionnés.
    Elle crée une copie des données pour éviter de modifier l'original.
    
    Args:
        data (pd.DataFrame): DataFrame contenant les données à filtrer.
        selected (dict): Dictionnaire des filtres à appliquer, contenant :
                         - 'region': Code REG de la région (None pour aucune)
                         - 'category': Nom de la catégorie ("Toutes" pour aucune)
    
    Returns:
        pd.DataFrame: DataFrame filtré selon les critères spécifiés.
    """
    # Crée une copie des données pour éviter de modifier l'original
    filtered = data.copy()
    
    # Filtre par région si une région est sélectionnée
    if selected["region"] is not None:
        # Conserve uniquement les lignes où la colonne REG correspond au code sélectionné
        filtered = filtered[filtered["REG"] == selected["region"]]
    
    # Filtre par catégorie si une catégorie spécifique est sélectionnée (pas "Toutes")
    if selected["category"] != "Toutes":
        # Conserve uniquement les lignes où la colonne categorie correspond à la catégorie sélectionnée
        filtered = filtered[filtered["categorie"] == selected["category"]]
    
    return filtered


def render_explorer_content() -> None:
    """Affiche l'interface complète de l'explorateur d'offre de soins.
    
    Cette fonction est la principale de ce module. Elle :
    1. Charge et filtre les données selon les paramètres utilisateur
    2. Agrège les données par département
    3. Applique le filtrage sur le nombre d'équipements (min/max)
    4. Affiche les métriques résumées
    5. Génère et affiche les 3 graphiques :
       - Graphique en barres horizontales des 20 premiers départements
       - Camembert de la répartition par type d'offre
       - Carte choroplèthe de France avec les équipements par département
    
    Returns:
        None: Affiche directement le contenu dans Streamlit.
    """
    # Titre de la section
    st.title("🔎 Explorer l'offre de soins")
    st.write("Validez plusieurs critères en une seule fois grâce au formulaire.")

    # Charge les données agrégées par département et catégorie
    data = aggregate_department_data()
    
    # Récupère les paramètres de filtrage (région, catégorie, min/max)
    selected = get_filter_params(data)
    
    # Applique les filtres de région et catégorie aux données
    filtered_rows = apply_row_filters(data, selected)

    # 1. Agrégation par département : calcule le total d'équipements par département
    dept_totals = (
        filtered_rows.groupby(["code_departement", "departement"], as_index=False)["equipements"]
        .sum()  # Somme des équipements pour chaque département
    )
    
    # 2. Filtre les départements selon la plage min/max d'équipements
    valid_depts = dept_totals[
        (dept_totals["equipements"] >= selected["minimum"])
        & (dept_totals["equipements"] <= selected["maximum"])
    ]

    # Affiche un avertissement si aucun département ne correspond aux critères
    if valid_depts.empty:
        st.warning("Aucun résultat avec ces filtres.")
        return

    # Filtre les lignes originales pour ne garder que les départements valides
    # Cela permet de garder le camembert cohérent avec les autres visualisations
    filtered = filtered_rows[
        filtered_rows["code_departement"].isin(valid_depts["code_departement"])
    ]

    # Trie les départements par nombre d'équipements (décroissant)
    ranking = valid_depts.sort_values("equipements", ascending=False)
    
    # Affiche 3 métriques clés en haut de la section
    first, second, third = st.columns(3)
    first.metric("Équipements de santé analysés", format_number(int(filtered["equipements"].sum())))
    second.metric("Départements observés", format_number(len(valid_depts)))
    third.metric("Catégories comparées", format_number(filtered["categorie"].nunique()))

    # Crée deux colonnes pour les graphiques en barres et camembert
    left, right = st.columns(2)
    
    # Graphique en barres horizontales - Top 20 départements
    with left:
        fig = px.bar(
            ranking.head(20).sort_values("equipements"),  # Prend les 20 premiers et les trie par ordre croissant pour l'affichage
            x="equipements",
            y="departement",
            orientation="h",  # Barres horizontales
            labels={"equipements": "Équipements", "departement": ""},  # Libellés des axes
            template="plotly_white",
            color="equipements",  # Colore les barres selon le nombre d'équipements
            color_continuous_scale="Teal",  # Palette de couleurs Teal
        )
        st.plotly_chart(fig, width="stretch")
    
    # Graphique camembert - Répartition par type d'offre
    with right:
        # Agrège les données par catégorie pour le camembert
        category_data = (
            filtered.groupby("categorie", as_index=False)["equipements"]
            .sum()  # Total d'équipements par catégorie
            .sort_values("equipements", ascending=False)  # Trie par ordre décroissant
        )
        
        fig = px.pie(
            category_data,
            values="equipements",
            names="categorie",
            title="Répartition par type d'offre",
            hole=0.45,  # Crée un trou au centre (donut chart)
            color_discrete_sequence=px.colors.sequential.Teal,  # Palette Teal pour les segments
        )
        # Personnalisation du layout pour correspondre au thème LifeMap
        fig.update_layout(
            template="plotly_white",
            font=dict(family="Inter, sans-serif", color="#1e293b"),  # Police Inter, couleur texte principale
            title_font_color="#1e293b",  # Couleur du titre
            title_font_size=16,  # Taille du titre
        )
        # Personnalisation des traces (segments du camembert)
        fig.update_traces(
            textfont=dict(family="Inter, sans-serif", color="#ffffff", size=11),  # Texte blanc dans les segments
            marker=dict(line=dict(color="#ffffff", width=2)),  # Bordure blanche entre les segments
        )
        st.plotly_chart(fig, width="stretch")

    # Carte choroplèthe - Répartition géographique des équipements
    st.subheader("Carte départementale")
    fig_map = px.choropleth_map(
        ranking,  # Utilise le classement des départements
        geojson=load_department_geojson(),  # GeoJSON des contours des départements
        locations="code_departement",  # Colonne pour la correspondance avec le GeoJSON
        featureidkey="properties.code",  # Clé dans le GeoJSON pour la correspondance
        color="equipements",  # Colore selon le nombre d'équipements
        hover_name="departement",  # Affiche le nom du département au survol
        color_continuous_scale="Teal",  # Palette Teal pour la carte
        center={"lat": 46.6, "lon": 2.4},  # Centre sur la France métropolitaine
        zoom=4.8,  # Niveau de zoom
        map_style="carto-positron",  # Style de carte clair
        labels={"equipements": "Équipements"},  # Libellé de la légende
    )
    # Supprime les marges pour un affichage optimal
    fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_map, width="stretch")


# Point d'entrée du module si exécuté directement
if __name__ == "__main__":
    render_explorer()
