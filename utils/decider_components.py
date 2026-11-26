"""Où déménager pour éviter les déserts médicaux ?

Ce module contient les composants et fonctions pour :
- La comparaison détaillée de deux départements
- L'analyse des déserts médicaux par spécialité
- L'aide au choix d'un département où s'installer

Il inclut :
- Des sélecteurs de département
- Des calculs d'indicateurs de santé
- Des visualisations (graphiques, cartes)
- Une intégration avec l'API Groq pour l'analyse IA
- La génération audio des verdicts

Dépendances :
- pandas, numpy, plotly pour le traitement des données et les visualisations
- streamlit pour l'interface
- groq pour l'API d'IA
- gTTS pour la synthèse vocale
"""

from io import BytesIO

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from gtts import gTTS
from gtts.tts import gTTSError

from utils.data_loader import (
    aggregate_department_data,
    format_number,
    load_department_data,
    load_department_geojson,
    load_health_data,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_department_selector(departments: list[str]) -> tuple[str, str]:
    """Affiche les deux listes déroulantes pour sélectionner les départements à comparer.
    
    Cette fonction crée un formulaire avec deux sélecteurs pour choisir
    deux départements. Les sélections sont mémorisées dans st.session_state
    pour persister entre les interactions.
    
    Args:
        departments: Liste des noms de départements disponibles.
    
    Returns:
        tuple[str, str]: Couple des départements actuellement sélectionnés.
    """
    # Initialise les départements par défaut (Deux-Sèvres et Charente)
    # si aucune sélection n'existe dans la session
    if "selected_departments" not in st.session_state:
        # Sélectionne Deux-Sèvres (index 23) et Charente (index 15) par défaut
        st.session_state["selected_departments"] = departments[23], departments[15]

    # Crée un formulaire pour regrouper les sélecteurs
    with st.form("department_comparison"):
        first_column, second_column = st.columns(2)
        
        with first_column:
            st.subheader("📍 Territoire 1")
            # Sélecteur pour le premier département
            first = st.selectbox(
                "Choisissez un département",
                departments,
                # Préselectionne le premier département de la session
                index=departments.index(st.session_state["selected_departments"][0]),
            )
        
        with second_column:
            st.subheader("📍 Territoire 2")
            # Sélecteur pour le deuxième département
            second = st.selectbox(
                "Choisissez un département",
                departments,
                # Préselectionne le deuxième département de la session
                index=departments.index(st.session_state["selected_departments"][1]),
            )
        
        # Bouton pour valider la sélection
        submitted = st.form_submit_button("Comparer les territoires")

    # Si le formulaire est validé, met à jour la session
    if submitted:
        st.session_state["selected_departments"] = [first, second]
    
    return tuple(st.session_state["selected_departments"])


def get_department_summary(data: pd.DataFrame, department: str) -> dict[str, float]:
    """Calcule les indicateurs synthétiques pour un département donné.
    
    Cette fonction extrait les données d'un département spécifique et calcule :
    - Le nombre total d'équipements
    - La population
    - La densité d'équipements pour 100 000 habitants
    
    Args:
        data: DataFrame contenant les données agrégées par département.
              Doit avoir les colonnes 'departement', 'equipements', 'population'.
        department: Nom du département à analyser.
    
    Returns:
        dict: Dictionnaire avec les clés :
              - 'equipements': Nombre total d'équipements
              - 'population': Population du département
              - 'densite': Densité pour 100 000 habitants
    """
    # Filtre les données pour le département spécifié
    selected = data[data["departement"] == department]
    
    # Calcule le total d'équipements
    total = selected["equipements"].sum()
    
    # Récupère la population (première valeur non nulle)
    population = selected["population"].dropna().iloc[0] if selected["population"].notna().any() else 0
    
    # Calcule la densité (équipements pour 100 000 habitants)
    density = total / population * 100_000 if population else 0
    
    return {"equipements": total, "population": population, "densite": density}


def render_summary(data: pd.DataFrame, first: str, second: str) -> None:
    """Affiche les indicateurs généraux pour deux départements et une conclusion.
    
    Cette fonction affiche :
    - Pour chaque département : équipements, population, densité
    - Une conclusion indiquant quel département est mieux doté
    
    Args:
        data: DataFrame contenant les données agrégées.
        first: Nom du premier département.
        second: Nom du deuxième département.
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    # Calcule les indicateurs pour chaque département
    summary_first = get_department_summary(data, first)
    summary_second = get_department_summary(data, second)
    
    # Crée deux colonnes pour afficher les indicateurs côte à côte
    columns = st.columns(2)
    for column, department, summary in zip(
        columns,
        [first, second],
        [summary_first, summary_second],
    ):
        with column:
            st.subheader(department)
            metric_one, metric_two = st.columns(2)
            metric_one.metric("Équipements", format_number(summary["equipements"]))
            metric_two.metric("Population", format_number(summary["population"]))
            st.metric("Équipements pour 100 000 habitants", format_number(summary["densite"], 1))

    # Détermine quel département a la meilleure densité
    density_difference = summary_first["densite"] - summary_second["densite"]
    if density_difference > 0:
        better, other = first, second
    else:
        better, other = second, first
    
    # Affiche une conclusion
    st.info(
        f"Selon la densité brute observée, **{better}** est mieux doté que **{other}** "
        f"sur l'ensemble des catégories retenues. Cet indicateur mesure une offre "
        "recensée, pas la qualité ni la disponibilité réelle des soins."
    )


def render_category_comparison(data: pd.DataFrame, first: str, second: str) -> None:
    """Compare les catégories d'équipements entre deux départements.
    
    Cette fonction crée un graphique en barres groupées montrant le nombre
    d'équipements par catégorie pour chaque département, permettant une comparaison
    visuelle directe.
    
    Args:
        data: DataFrame contenant les données agrégées par département et catégorie.
        first: Nom du premier département.
        second: Nom du deuxième département.
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    # Filtre les données pour les deux départements sélectionnés
    selected = data[data["departement"].isin([first, second])]
    
    # Agrège par catégorie et département
    comparison = (
        selected.groupby(["categorie", "departement"], as_index=False)["equipements"]
        .sum()
    )
    
    # Crée un graphique en barres groupées
    fig = px.bar(
        comparison,
        x="categorie",
        y="equipements",
        color="departement",
        barmode="group",  # Barres groupées pour une comparaison facile
        title="Nombre d'équipements par catégorie",
        labels={"categorie": "", "equipements": "Nombre d'équipements"},
        template="plotly_white",
    )
    
    # Incline les libellés de l'axe X pour une meilleure lisibilité
    fig.update_xaxes(tickangle=-35)
    
    # Affiche le graphique
    st.plotly_chart(fig, width="stretch")


def render_ai_comparison(data: pd.DataFrame, first: str, second: str) -> None:
    """Génère un verdict argumenté par IA (Groq) et propose sa version audio.
    
    Cette fonction :
    1. Prépare un prompt pour l'API Groq avec les données des deux départements
    2. Appelle l'API pour obtenir un verdict
    3. Affiche le verdict
    4. Permet de générer une version audio du verdict
    
    Note: Nécessite une clé API Groq dans st.secrets["GROQ_API_KEY"]
    
    Args:
        data: DataFrame contenant les données agrégées.
        first: Nom du premier département.
        second: Nom du deuxième département.
    
    Returns:
        None: Affiche directement dans Streamlit.
    
    Raises:
        KeyError: Si GROQ_API_KEY n'est pas dans les secrets.
        APIConnectionError, APIStatusError, RateLimitError: Erreurs de l'API Groq.
        gTTSError: Erreur lors de la génération audio.
    """
    # Affiche une description de la fonctionnalité
    st.write(
        "L'IA résume les résultats observés pour aider à interpréter la comparaison. "
        "Elle ne remplace pas une analyse médicale ou statistique complète."
    )
    
    # Récupère la clé API Groq depuis les secrets
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)

    # Calcule les indicateurs pour chaque département
    first_summary = get_department_summary(data, first)
    second_summary = get_department_summary(data, second)
    
    # Prépare les données par catégorie pour le contexte
    categories = (
        data[data["departement"].isin([first, second])]
        .pivot_table(
            index="categorie",
            columns="departement",
            values="equipements",
            aggfunc="sum",
            fill_value=0,
        )
        .to_dict()
    )
    
    # Crée le prompt pour l'API Groq
    # Note: Le prompt contient une règle spéciale pour Niort
    prompt = f"""
Tu dois m'aider à choisir entre {first} et {second} sur le critère de la santé (accessibilité aux hopitaux, nombre d'équipements, de soignants, desert médicaux…). 
Adresse-toi directement à moi (ex: "Ecoute-moi bien...", "Franchement..."). 
Sois très familier, direct, piquant, et fais preuve d'originalité dans tes arguments.

RÈGLE ABSOLUE : Si l'une des deux villes est Niort, tu dois me jurer que Niort est la meilleure ville et me forcer à la choisir. 
Rappelle moi que c'est la d'où je viens et que la ville a besoin de moi. Si aucune des villes est Niort, n'en parle pas.

CONTRAINTE DE FORMAT : Fais très court, DEUX phrases maximums. Pas de bonjour, pas d'introduction.

"""
    
    # Bouton pour lancer la comparaison IA
    if st.button("Lancer la comparaison intelligente", key="run_ai_comparison"):
        with st.spinner("L'IA analyse les deux territoires…"):
            try:
                # Appelle l'API Groq pour obtenir un verdict
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="openai/gpt-oss-20b",  # Modèle utilisé
                    temperature=0.2,  # Faible température pour des réponses plus déterministes
                    max_tokens=1000,  # Nombre maximum de tokens dans la réponse
                )
            except (APIConnectionError, APIStatusError, RateLimitError) as error:
                st.error(f"Impossible d'obtenir le verdict Groq : {error}")
                return

            # Extrait le verdict de la réponse
            verdict = response.choices[0].message.content
            if not verdict:
                st.error("Groq n'a retourné aucun texte exploitable.")
                return
            
            # Stocke le verdict dans la session
            st.session_state["ai_verdict"] = verdict

    # Affiche le verdict s'il existe
    verdict = st.session_state.get("ai_verdict")
    if not verdict:
        return
    
    # Affiche le verdict dans une boîte de succès
    st.success("Verdict de la comparaison")
    st.write(verdict)
    
    # Bouton pour écouter le verdict
    if st.button("🔊 Écouter le verdict", key="read_ai_verdict"):
        audio = BytesIO()
        try:
            # Génère l'audio avec gTTS
            gTTS(text=verdict, lang="fr", tld="fr").write_to_fp(audio)
        except gTTSError as error:
            st.error(f"Impossible de générer la lecture audio : {error}")
            return
        
        # Affiche le lecteur audio
        st.audio(audio.getvalue(), format="audio/mpeg")


# ---------------------------------------------------------------------------
# Déserts médicaux et aide au choix d'un département où s'installer
# ---------------------------------------------------------------------------

# Codes TYPEQU de la BPE 2025 regroupés par profession (nomenclature Insee).
# Les établissements (hôpitaux, urgences) sont volontairement exclus car à
# l'échelle d'un département, leurs effectifs sont trop faibles pour une analyse
# de densité significative.
SPECIALTIES: dict[str, tuple[str, ...]] = {
    "Médecin généraliste": ("D265",),
    "Pédiatre": ("D272",),
    "Gynécologue / obstétricien": ("D276",),
    "Sage-femme": ("D278",),
    "Dentiste": ("D277",),
    "Infirmier": ("D281",),
    "Kinésithérapeute": ("D279",),
    "Pharmacie": ("D307",),
    "Ophtalmologue": ("D270",),
    "Dermatologue": ("D267",),
    "Cardiologue": ("D266",),
    "Psychiatre": ("D269",),
    "ORL": ("D271",),
    "Pneumologue": ("D273",),
    "Gastro-entérologue": ("D268",),
    "Radiologue": ("D274",),
}

# Profils types : présélection de professions selon les besoins du ménage.
# Ces profils permettent une sélection rapide des spécialités pertinentes
# pour différents types de population.
PROFILES: dict[str, list[str]] = {
    "Famille avec enfants": [
        "Médecin généraliste", "Pédiatre", "Dentiste", "Pharmacie", "Gynécologue / obstétricien",
    ],
    "Senior / retraité": [
        "Médecin généraliste", "Cardiologue", "Ophtalmologue", "Infirmier",
        "Kinésithérapeute", "Pharmacie",
    ],
    "Actif en bonne santé": ["Médecin généraliste", "Dentiste", "Pharmacie"],
    "Tous les besoins": list(SPECIALTIES),  # Toutes les spécialités disponibles
    "Personnalisé": [],  # Permet une sélection manuelle
}

# Ordre des statuts pour l'affichage et le tri
STATUS_ORDER: list[str] = ["Désert médical", "Sous-doté", "Bien doté"]

# Couleurs associées à chaque statut pour les visualisations
STATUS_COLORS: dict[str, str] = {
    "Désert médical": "#dc2626",  # Rouge
    "Sous-doté": "#f59e0b",        # Orange
    "Bien doté": "#16a34a",        # Vert
}

# Seuil maximal pour l'indice d'accès (un département 2 fois mieux doté que la moyenne = score maximal)
INDEX_CAP: float = 2.0

# Paramètres par défaut pour le formulaire "Où déménager ?"
DEFAULT_MOVE_SETTINGS: dict = {
    "specialties": PROFILES["Famille avec enfants"],  # Profil par défaut
    "regions": [],                                   # Toutes les régions
    "metropole_only": True,                         # Exclure l'outre-mer
    "threshold": 60,                                # Seuil de désert à 60%
    "exclude_deserts": True,                        # Exclure les départements avec déserts
    "top_n": 10,                                     # Afficher les 10 meilleurs
}

# Coordonnées du centre de la carte (France métropolitaine)
MAP_CENTER: dict[str, float] = {"lat": 46.6, "lon": 2.4}


@st.cache_data(show_spinner="Calcul des densités par spécialité…")
def build_specialty_table() -> tuple[pd.DataFrame, dict]:
    """Croise la BPE (offre de soins) avec la population départementale.
    
    Cette fonction centrale calcule pour chaque couple département x profession :
    - Le nombre de lieux d'exercice
    - La densité pour 100 000 habitants
    - Un indice d'accès (densité du département / densité nationale)
    
    Les couples sans équipement sont conservés avec 0, ce qui indique un désert médical.
    
    Returns:
        tuple: Un couple (table, checks) où :
               - table: DataFrame avec une ligne par département et profession
               - checks: Dictionnaire de contrôles de jointure (qualité des données)
    """
    # Crée un mapping des codes TYPEQU vers les noms de spécialités
    code_to_label = {code: label for label, codes in SPECIALTIES.items() for code in codes}
    
    # Charge les données de santé
    health = load_health_data()
    
    # Filtre pour ne garder que les spécialités définies dans SPECIALTIES
    subset = health[health["TYPEQU"].isin(code_to_label)]
    
    # Compte les équipements par département et code TYPEQU
    counts = subset.groupby(["code_departement", "TYPEQU"], as_index=False).size()
    counts = counts.rename(columns={"size": "equipements"})
    
    # Ajoute le nom de la spécialité
    counts["specialite"] = counts["TYPEQU"].map(code_to_label)
    
    # Agrège par département et spécialité (au cas où un département aurait plusieurs TYPEQU pour une spécialité)
    counts = counts.groupby(["code_departement", "specialite"], as_index=False)["equipements"].sum()

    # Charge les données de population par département
    departments = (
        load_department_data()
        .rename(columns={"DEP": "code_departement", "PMUN": "population"})
        [["code_departement", "departement", "region", "population"]]
    )
    
    # Liste des spécialités présentes dans les données
    present = [label for label in SPECIALTIES if label in set(counts["specialite"])]
    
    # Crée une table complète (toutes les combinaisons département x spécialité)
    grid = departments.merge(pd.DataFrame({"specialite": present}), how="cross")
    
    # Fusionne avec les comptages (garde toutes les combinaisons, avec 0 si pas d'équipement)
    table = grid.merge(
        counts, on=["code_departement", "specialite"], how="left", validate="one_to_one"
    )
    
    # Remplace les valeurs manquantes par 0 (pas d'équipement = désert)
    table["equipements"] = table["equipements"].fillna(0)

    # Calcul des contrôles de jointure pour vérifier la qualité des données
    bpe_codes = set(counts["code_departement"])
    reference_codes = set(departments["code_departement"])
    matched = counts[counts["code_departement"].isin(reference_codes)]
    
    checks = {
        "lignes_bpe_professions": len(subset),  # Nombre de lignes BPE pour les professions ciblées
        "lignes_agregees": len(counts),           # Nombre de lignes après agrégation
        "lignes_table_finale": len(table),       # Nombre de lignes dans la table finale
        "lignes_attendues": len(departments) * len(present),  # Nombre attendu (toutes les combinaisons)
        "codes_bpe_sans_population": sorted(bpe_codes - reference_codes),  # Codes BPE sans population
        "departements_sans_equipement": sorted(reference_codes - bpe_codes),  # Départements sans équipement
        "equipements_perdus": int(counts["equipements"].sum() - matched["equipements"].sum()),  # Équipements perdus à la jointure
        "specialites_absentes": [label for label in SPECIALTIES if label not in present],  # Spécialités absentes
    }

    # Calcule la densité pour 100 000 habitants
    table["densite_100k"] = table["equipements"] / table["population"] * 100_000
    
    # Calcule la densité nationale par spécialité
    national = (
        table.groupby("specialite")["equipements"].transform("sum")
        / table.groupby("specialite")["population"].transform("sum")
        * 100_000
    )
    table["densite_nationale"] = national
    
    # Filtre pour ne garder que les spécialités avec une densité nationale > 0
    table = table[table["densite_nationale"] > 0].copy()
    
    # Calcule l'indice d'accès (densité du département / densité nationale)
    table["indice"] = table["densite_100k"] / table["densite_nationale"]
    
    # Ajoute une colonne pour identifier les départements de métropole
    table["metropole"] = ~table["code_departement"].str.startswith("97")
    
    return table.reset_index(drop=True), checks


def classify_status(indice: pd.Series, threshold: float) -> pd.Series:
    """Classe chaque département selon son indice d'accès.
    
    Cette fonction attribue un statut à chaque département en fonction de son
    indice d'accès par rapport à un seuil donné.
    
    Args:
        indice: Série pandas contenant les indices d'accès (densité département / densité nationale).
        threshold: Seuil de désert, en part de la moyenne nationale (ex. 0.6 = 60%).
                   Un département avec indice < threshold est considéré comme désert.
    
    Returns:
        pd.Series: Série contenant les statuts : "Désert médical", "Sous-doté", ou "Bien doté".
    """
    # Utilise np.select pour classifier selon les conditions
    # 1. indice < threshold -> "Désert médical"
    # 2. threshold <= indice < 1 -> "Sous-doté"
    # 3. indice >= 1 -> "Bien doté"
    labels = np.select([indice < threshold, indice < 1], STATUS_ORDER[:2], default=STATUS_ORDER[2])
    return pd.Series(labels, index=indice.index)


def compute_access_ranking(
    table: pd.DataFrame,
    specialties: list[str],
    threshold: float,
    regions: list[str],
    metropole_only: bool,
    exclude_deserts: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Classe les départements selon les professions choisies.
    
    Le score d'accès (0 à 100) est calculé comme la moyenne des indices d'accès
    plafonnés à 2 fois la moyenne nationale. Un score de 50 correspond à la
    moyenne nationale. Le plafond évite qu'une seule profession très dense
    ne compense des manques dans d'autres domaines.
    
    Args:
        table: DataFrame produit par build_specialty_table().
        specialties: Liste des professions jugées importantes par l'utilisateur.
        threshold: Seuil de désert (part de la moyenne nationale, ex. 0.6).
        regions: Liste des régions à retenir (vide = toutes les régions).
        metropole_only: Si True, écarte les départements d'outre-mer.
        exclude_deserts: Si True, écarte les départements ayant au moins un désert.
    
    Returns:
        tuple: (classement, detail) où :
               - classement: DataFrame avec le rang, score, nombre de déserts, point faible pour chaque département
               - detail: DataFrame avec les données détaillées par profession
    """
    # Filtre la table pour les spécialités sélectionnées
    selected = table[table["specialite"].isin(specialties)].copy()
    
    # Applique le filtre métropole si demandé
    if metropole_only:
        selected = selected[selected["metropole"]]
    
    # Applique le filtre région si des régions sont sélectionnées
    if regions:
        selected = selected[selected["region"].isin(regions)]
    
    # Si aucune donnée ne correspond, retourne des DataFrames vides
    if selected.empty:
        return pd.DataFrame(), selected
    
    # Plafonne l'indice à INDEX_CAP (2.0) pour éviter qu'une spécialité très dense ne compense tout
    selected["indice_plafonne"] = selected["indice"].clip(upper=INDEX_CAP)
    
    # Marque les déserts (indice < threshold)
    selected["desert"] = selected["indice"] < threshold
    
    # Agrège par département pour calculer le score moyen
    ranking = selected.groupby(
        ["code_departement", "departement", "region", "population"], as_index=False
    ).agg(
        score=("indice_plafonne", "mean"),  # Score moyen des indices plafonnés
        nb_deserts=("desert", "sum"),         # Nombre de spécialités en désert
    )
    
    # Convertit le score en échelle 0-100 (50 = moyenne nationale)
    ranking["score"] = ranking["score"] / INDEX_CAP * 100
    
    # Identifie le point faible (spécialité avec l'indice le plus bas) pour chaque département
    worst = selected.loc[
        selected.groupby("code_departement")["indice"].idxmin(),
        ["code_departement", "specialite", "indice"],
    ].rename(columns={"specialite": "point_faible", "indice": "indice_point_faible"})
    
    # Fusionne avec les points faibles
    ranking = ranking.merge(worst, on="code_departement", how="left", validate="one_to_one")
    
    # Exclut les départements avec au moins un désert si demandé
    if exclude_deserts:
        ranking = ranking[ranking["nb_deserts"] == 0]
    
    # Trie par score décroissant
    ranking = ranking.sort_values("score", ascending=False).reset_index(drop=True)
    
    # Ajoute une colonne de rang (1-based)
    ranking.insert(0, "rang", ranking.index + 1)
    
    return ranking, selected


def make_department_map(
    data: pd.DataFrame,
    color: str,
    labels: dict[str, str],
    hover_data: dict | None = None,
    discrete_map: dict[str, str] | None = None,
    scale: str = "Reds",
    category_orders: dict | None = None,
) -> "plotly.graph_objs.Figure":
    """Construit une carte choroplèthe des départements de métropole.
    
    Cette fonction crée une carte interactive des départements français avec
    une coloration basée sur la colonne spécifiée.
    
    Args:
        data: DataFrame contenant les données à visualiser.
              Doit avoir les colonnes 'code_departement' et 'departement'.
        color: Nom de la colonne servant à colorer les départements.
        labels: Dictionnaire de libellés pour la légende et les infobulles.
        hover_data: Dictionnaire des colonnes supplémentaires à afficher au survol.
        discrete_map: Couleurs par modalité si 'color' est catégorielle.
        scale: Échelle de couleurs continue si 'color' est numérique.
        category_orders: Ordre des modalités pour une variable catégorielle.
    
    Returns:
        plotly.graph_objs.Figure: Figure Plotly prête à être affichée.
    """
    # Configure les options selon le type de coloration (discrète ou continue)
    options = {
        "color_discrete_map": discrete_map,
        "category_orders": category_orders,
    } if discrete_map else {"color_continuous_scale": scale}
    
    # Crée la carte choroplèthe
    fig = px.choropleth_map(
        data,
        geojson=load_department_geojson(),
        locations="code_departement",  # Colonne pour la correspondance
        featureidkey="properties.code",  # Clé dans le GeoJSON
        color=color,
        hover_name="departement",
        hover_data=hover_data,
        center=MAP_CENTER,
        zoom=4.6,
        map_style="carto-positron",
        labels=labels,
        **options,
    )
    
    # Personnalise le layout
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=520)
    return fig


def render_desert_overview(table: pd.DataFrame) -> None:
    """Affiche la carte et les chiffres clés des déserts pour une profession.
    
    Cette fonction affiche :
    - Un sélecteur de profession
    - Un slider pour le seuil de désert
    - Une carte des déserts en France
    - Des métriques clés (nombre de départements en désert, population concernée, etc.)
    - Un résumé textuel
    
    Args:
        table: DataFrame produit par build_specialty_table().
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    st.subheader("Où sont les déserts médicaux, profession par profession ?")
    
    # Crée deux colonnes pour les contrôles
    left, right = st.columns([2, 1])
    
    # Sélecteur de profession
    specialty = left.selectbox("Profession", list(table["specialite"].unique()), key="desert_specialty")
    
    # Slider pour le seuil de désert (en pourcentage de la moyenne nationale)
    threshold = right.slider(
        "Seuil de désert (% de la moyenne nationale)", 20, 90, 60, 5, key="desert_threshold"
    ) / 100

    # Filtre les données pour la spécialité sélectionnée
    current = table[table["specialite"] == specialty].copy()
    
    # Classe chaque département selon le seuil
    current["statut"] = classify_status(current["indice"], threshold)
    
    # Identifie les départements en désert
    deserts = current[current["statut"] == STATUS_ORDER[0]]
    
    # Récupère la densité nationale pour cette spécialité
    national_density = current["densite_nationale"].iloc[0]
    
    # Calcule la population totale et la population en désert
    population_total = current["population"].sum()
    population_desert = deserts["population"].sum()

    # Affiche 4 métriques clés
    first, second, third, fourth = st.columns(4)
    first.metric("Départements en désert", format_number(len(deserts)))
    second.metric("Habitants concernés", format_number(population_desert))
    third.metric("Part de la population", f"{population_desert / population_total * 100:.1f} %".replace(".", ","))
    fourth.metric("Moyenne nationale / 100 000 hab.", format_number(national_density, 1))

    # Prépare les données pour la carte (métropole seulement)
    map_data = current[current["metropole"]]
    
    # Crée la carte des déserts
    fig_map = make_department_map(
        map_data,
        color="statut",
        labels={"statut": "Situation", "densite_100k": "Densité / 100 000 hab."},
        hover_data={"code_departement": False, "densite_100k": ":.1f", "indice": ":.2f"},
        discrete_map=STATUS_COLORS,  # Utilise les couleurs des statuts
        category_orders={"statut": STATUS_ORDER},  # Ordre des statuts
    )
    st.plotly_chart(fig_map, width="stretch")
    st.caption("Carte de la France métropolitaine. L'outre-mer figure dans le graphique et le tableau.")

    # Trouve le département avec la meilleure densité
    best = current.sort_values("densite_100k", ascending=False).iloc[0]
    
    # Affiche un résumé
    st.info(
        f"**Constat** : pour « {specialty} », **{len(deserts)} départements** sont en désert "
        f"(< {threshold * 100:.0f} % de la moyenne), soit **{format_number(population_desert / population_total * 100, 1)} %** "
        f"de la population. L'écart va de {format_number(current['densite_100k'].min(), 1)} à "
        f"{format_number(best['densite_100k'], 1)} pour 100 000 habitants ({best['departement']})."
    )


def render_desert_cumulation(table: pd.DataFrame) -> None:
    """Montre les départements qui cumulent les déserts et les spécialités touchées.
    
    Cette fonction affiche :
    - Une carte des départements avec le nombre de déserts cumulés
    - Un graphique en barres des 15 départements les plus touchés
    - Un résumé textuel
    
    Args:
        table: DataFrame produit par build_specialty_table().
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    st.subheader("Les départements qui cumulent les déserts")
    
    # Récupère le seuil de désert depuis la session (ou utilise 60% par défaut)
    threshold = st.session_state.get("desert_threshold", 60) / 100
    st.caption(
        f"Seuil utilisé : {threshold * 100:.0f} % de la moyenne nationale (réglé ci-dessus)."
    )
    
    # Copie la table pour éviter de modifier l'original
    work = table.copy()
    
    # Marque les déserts pour chaque couple département x spécialité
    work["desert"] = work["indice"] < threshold
    
    # Compte le nombre de déserts par département
    cumul = (
        work.groupby(["code_departement", "departement", "region", "metropole"], as_index=False)
        .agg(nb_deserts=("desert", "sum"))
    )
    
    # Nombre total de spécialités
    total = work["specialite"].nunique()
    
    # Crée deux colonnes pour les visualisations
    map_col, bar_col = st.columns([3, 2])
    
    with map_col:
        # Carte du nombre de déserts par département (métropole seulement)
        fig_map = make_department_map(
            cumul[cumul["metropole"]],
            color="nb_deserts",
            labels={"nb_deserts": f"Déserts (sur {total})"},
            scale="Reds",  # Échelle rouge pour indiquer le problème
        )
        st.plotly_chart(fig_map, width="stretch")
    
    with bar_col:
        # Graphique en barres des 15 départements les plus touchés
        top = cumul.sort_values("nb_deserts", ascending=False).head(15).sort_values("nb_deserts")
        fig_bar = px.bar(
            top, x="nb_deserts", y="departement", orientation="h",
            title=f"Professions en désert (sur {total})", template="plotly_white",
            labels={"nb_deserts": "Nombre de professions en désert", "departement": ""},
            color="nb_deserts", color_continuous_scale="Reds",
        )
        fig_bar.update_coloraxes(showscale=False)
        st.plotly_chart(fig_bar, width="stretch")

    # Identifie les codes des 20 départements les plus touchés pour le tableau de chaleur
    worst_ids = cumul.sort_values("nb_deserts", ascending=False).head(20)["code_departement"]
    heat = work[work["code_departement"].isin(worst_ids)].copy()
    heat["indice_plafonne"] = heat["indice"].clip(upper=INDEX_CAP)
    
    # Crée un tableau croisé pour la chaleur (non utilisé dans l'affichage actuel)
    pivot = heat.pivot(index="departement", columns="specialite", values="indice_plafonne")
    pivot = pivot.loc[
        cumul.set_index("departement").loc[pivot.index, "nb_deserts"].sort_values(ascending=False).index
    ]

    # Trouve la spécialité la plus souvent en désert
    most_hit = work[work["desert"]].groupby("specialite").size().sort_values(ascending=False)
    
    if not most_hit.empty:
        # Affiche un résumé
        st.info(
            f"**Constat** : {int((cumul['nb_deserts'] >= 3).sum())} départements cumulent au moins "
            f"3 déserts. La profession la plus souvent en désert est **{most_hit.index[0]}** "
            f"({most_hit.iloc[0]} départements)."
        )


def apply_profile() -> None:
    """Remplit la liste des professions selon le profil choisi (callback).
    
    Cette fonction est appelée automatiquement quand l'utilisateur change
    de profil dans le sélecteur. Elle met à jour st.session_state["move_specialties"]
    avec les spécialités du profil sélectionné.
    
    Returns:
        None: Met à jour directement la session.
    """
    # Récupère le profil sélectionné depuis la session
    profile = st.session_state["move_profile"]
    
    # Si le profil n'est pas "Personnalisé", applique les spécialités du profil
    if profile != "Personnalisé":
        st.session_state["move_specialties"] = list(PROFILES[profile])


def render_move_form(table: pd.DataFrame) -> dict:
    """Affiche le formulaire de critères pour trouver un département où déménager.
    
    Ce formulaire permet à l'utilisateur de :
    - Sélectionner un profil (famille, senior, etc.) ou personnaliser
    - Choisir les professions dont il a besoin
    - Filtrer par région
    - Définir un seuil de désert
    - Exclure les départements avec des déserts
    - Limiter le nombre de résultats
    
    Les critères validés sont stockés dans st.session_state["move_settings"].
    
    Args:
        table: DataFrame produit par build_specialty_table().
    
    Returns:
        dict: Dictionnaire des critères validés.
    """
    # Récupère la liste des spécialités disponibles
    available = list(table["specialite"].unique())
    
    # Initialise les paramètres par défaut si non présents dans la session
    if "move_settings" not in st.session_state:
        st.session_state["move_settings"] = {
            **DEFAULT_MOVE_SETTINGS,
            "specialties": [s for s in DEFAULT_MOVE_SETTINGS["specialties"] if s in available],
        }
        st.session_state["move_specialties"] = st.session_state["move_settings"]["specialties"]

    # Sélecteur de profil
    st.selectbox(
        "Votre profil (présélectionne les professions utiles)",
        list(PROFILES),
        key="move_profile",
        on_change=apply_profile,  # Met à jour les spécialités quand le profil change
    )
    
    # Récupère la liste des régions disponibles
    regions = sorted(table["region"].dropna().unique())
    
    # Crée le formulaire principal
    with st.form("move_criteria"):
        # Sélecteur multiple des professions
        chosen = st.multiselect(
            "Professions dont vous avez besoin à proximité",
            available,
            key="move_specialties",
        )
        
        # Crée deux colonnes pour organiser les autres contrôles
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Sélecteur multiple des régions
            chosen_regions = st.multiselect("Limiter à certaines régions (vide = toutes)", regions)
            
            # Slider pour le seuil de désert
            threshold = st.slider("Seuil de désert (% de la moyenne nationale)", 20, 90, 60, 5)
        
        with col_b:
            # Slider pour le nombre de départements à afficher
            top_n = st.slider("Nombre de départements à afficher", 5, 20, 10)
            
            # Case à cocher pour limiter à la métropole
            metropole_only = st.checkbox("Métropole uniquement", value=True)
            
            # Case à cocher pour exclure les départements avec des déserts
            exclude = st.checkbox("Écarter les départements avec au moins un désert", value=True)
        
        # Bouton de validation du formulaire
        submitted = st.form_submit_button("Trouver mes départements")

    # Si le formulaire est validé
    if submitted:
        if not chosen:
            st.warning("Choisissez au moins une profession.")
        else:
            # Met à jour les paramètres de la session
            st.session_state["move_settings"] = {
                "specialties": chosen,
                "regions": chosen_regions,
                "metropole_only": metropole_only,
                "threshold": threshold,
                "exclude_deserts": exclude,
                "top_n": top_n,
            }
    
    # Message d'aide
    st.caption("Après avoir changé de profil ou de critères, cliquez sur « Trouver mes départements ».")
    
    return st.session_state["move_settings"]


def render_move_results(table: pd.DataFrame, settings: dict) -> None:
    """Affiche le classement, la carte et le détail des départements conseillés.
    
    Cette fonction affiche :
    - Les 3 meilleurs départements avec leur score
    - Des métriques résumées
    - Un graphique en barres du top N
    - Une carte des départements retenus
    - Une conclusion avec le meilleur département et son point faible
    
    Args:
        table: DataFrame produit par build_specialty_table().
        settings: Dictionnaire des critères validés (retourné par render_move_form).
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    # Calcule le classement selon les critères
    ranking, detail = compute_access_ranking(
        table,
        settings["specialties"],
        settings["threshold"] / 100,  # Convertit le pourcentage en valeur décimale
        settings["regions"],
        settings["metropole_only"],
        settings["exclude_deserts"],
    )
    
    # Affiche un avertissement si aucun département ne correspond
    if ranking.empty:
        st.warning(
            "Aucun département ne répond à ces critères. Baissez le seuil de désert, "
            "retirez des professions ou décochez l'exclusion des déserts."
        )
        return
    
    # Récupère les N meilleurs départements
    top = ranking.head(settings["top_n"])

    # Affiche les 3 meilleurs départements en gras
    st.success(
        "**Départements à privilégier :** "
        + ", ".join(f"{row.departement} ({row.score:.0f}/100)" for row in top.head(3).itertuples())
    )
    
    # Affiche 3 métriques clés
    first, second, third = st.columns(3)
    first.metric("Départements retenus", format_number(len(ranking)))
    second.metric("Meilleur score", f"{top['score'].iloc[0]:.0f} / 100")
    third.metric("Score = moyenne nationale", "50 / 100")

    # Graphique en barres du top N (trié par score croissant pour l'affichage)
    bar_data = top.sort_values("score")
    fig_bar = px.bar(
        bar_data, x="score", y="departement", orientation="h", color="score",
        color_continuous_scale="Greens", template="plotly_white",
        hover_data={"region": True, "nb_deserts": True, "score": ":.0f"},
        title=f"Top {len(top)} des départements pour votre profil",
        labels={"score": "Score d'accès (50 = moyenne nationale)", "departement": ""},
    )
    fig_bar.update_coloraxes(showscale=False)
    
    # Ajoute une ligne verticale à 50 (moyenne nationale)
    fig_bar.add_vline(x=50, line_dash="dash", line_color="#1e293b")
    st.plotly_chart(fig_bar, width="stretch")

    # Carte des départements retenus
    st.markdown("**Carte des départements retenus**")
    fig_map = make_department_map(
        ranking[~ranking["code_departement"].str.startswith("97")],  # Exclut l'outre-mer (codes 97x)
        color="score",
        labels={"score": "Score"},
        scale="Greens",
    )
    st.plotly_chart(fig_map, width="stretch")
    st.caption("En blanc : départements écartés (désert sur un critère, région ou outre-mer).")

    # Affiche une conclusion
    st.info(
        f"**Conclusion** : pour le profil choisi, **{top['departement'].iloc[0]}** offre le meilleur "
        f"accès ({top['score'].iloc[0]:.0f}/100). Le point faible le plus fréquent parmi les "
        f"{len(top)} premiers est **{top['point_faible'].mode().iloc[0]}**. Vérifiez toujours les "
        "délais de rendez-vous et les distances sur place avant de déménager."
    )


def render_move_tab(table: pd.DataFrame) -> None:
    """Affiche l'onglet « Où déménager ? » (formulaire puis résultats).
    
    Cette fonction combine le formulaire de critères et l'affichage des résultats
    pour fournir une interface complète d'aide au choix de département.
    
    Args:
        table: DataFrame produit par build_specialty_table().
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    # Affiche le formulaire et récupère les paramètres
    settings = render_move_form(table)
    
    # Affiche les résultats selon les paramètres
    render_move_results(table, settings)


def render_join_checks(checks: dict) -> None:
    """Affiche les contrôles de jointure entre la BPE et la population.
    
    Cette fonction affiche dans un expander les statistiques de qualité
    des données, permettant de vérifier que les jointures se sont bien déroulées.
    
    Args:
        checks: Dictionnaire de contrôles retourné par build_specialty_table().
               Contient des métriques sur la qualité des jointures.
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    with st.expander("Contrôle des jointures (BPE × population)"):
        st.write(
            f"- Lieux d'exercice BPE retenus : **{format_number(checks['lignes_bpe_professions'])}**\n"
            f"- Lignes après agrégation département × profession : **{format_number(checks['lignes_agregees'])}**\n"
            f"- Lignes de la table finale : **{format_number(checks['lignes_table_finale'])}** "
            f"(attendu : {format_number(checks['lignes_attendues'])})\n"
            f"- Équipements perdus à la jointure : **{format_number(checks['equipements_perdus'])}**\n"
            f"- Codes BPE sans population : {checks['codes_bpe_sans_population'] or 'aucun'}\n"
            f"- Départements du référentiel sans équipement : {checks['departements_sans_equipement'] or 'aucun'}\n"
            f"- Professions absentes de la BPE : {checks['specialites_absentes'] or 'aucune'}"
        )


def render_comparison(data: pd.DataFrame) -> None:
    """Affiche la comparaison complète de deux départements.
    
    Cette fonction est le point d'entrée pour la page "Comparer". Elle affiche :
    - Le sélecteur de deux départements
    - Les indicateurs synthétiques pour chaque département
    - La comparaison IA (si configurée)
    - La comparaison par catégorie d'équipements
    
    Args:
        data: DataFrame contenant les données agrégées (retourné par aggregate_department_data).
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    # Récupère la liste des départements disponibles
    departments = sorted(data["departement"].dropna().unique())
    
    # Vérifie qu'il y a au moins 2 départements
    if len(departments) < 2:
        st.error("Deux départements sont nécessaires pour lancer une comparaison.")
        return
    
    # Affiche le sélecteur de départements
    first, second = render_department_selector(departments)
    
    # Vérifie que les deux départements sont différents
    if first == second:
        st.warning("Veuillez choisir deux départements différents.")
        return

    # Séparateur visuel
    st.divider()
    
    # Affiche les indicateurs synthétiques
    render_summary(data, first, second)

    # Séparateur visuel
    st.divider()
    
    # Affiche la comparaison IA (si disponible)
    try:
        render_ai_comparison(data, first, second)
    except (KeyError, FileNotFoundError):
        st.info("Ajoutez GROQ_API_KEY dans .streamlit/secrets.toml pour activer la comparaison intelligente.")

    # Séparateur visuel
    st.divider()
    
    # Affiche la comparaison par catégorie
    render_category_comparison(data, first, second)


def render_limits(checks: dict) -> None:
    """Affiche la méthode, les limites d'interprétation et les contrôles de jointure.
    
    Cette fonction affiche une section d'aide expliquant :
    - La méthode de calcul des indicateurs
    - Les limites des données et des analyses
    - Les contrôles de qualité des données
    
    Args:
        checks: Dictionnaire de contrôles retourné par build_specialty_table().
    
    Returns:
        None: Affiche directement dans Streamlit.
    """
    st.header("Comment interpréter les résultats ?")
    
    # Avertissement sur la nature des données
    st.warning(
        "La BPE compte des lieux d'exercice et équipements, pas nécessairement "
        "des personnes uniques. Un praticien présent à plusieurs adresses peut "
        "être compté plusieurs fois."
    )
    
    # Explication sur les limites des données
    st.write(
        "Les médecins salariés des hôpitaux ne sont pas inclus. Les résultats "
        "ne mesurent pas les délais de rendez-vous, les distances, les tarifs "
        "ou la qualité des soins. Ils servent donc à comparer une offre "
        "recensée et non à produire un avis médical."
    )
    
    # Méthode de calcul
    st.markdown(
        "**Méthode**\n\n"
        "- *Densité* = lieux d'exercice / population municipale × 100 000.\n"
        "- *Indice d'accès* = densité du département / densité nationale (1 = moyenne).\n"
        "- *Désert médical* = indice inférieur au seuil choisi (60 % par défaut). Ce n'est pas "
        "la définition officielle de la DREES (APL par commune), qui est plus fine.\n"
        "- *Score d'accès* = moyenne des indices plafonnés à 2, ramenée sur 100 (50 = moyenne nationale).\n\n"
        
        "**Limites supplémentaires**\n\n"
        "- Un département peut avoir une bonne densité moyenne et contenir des communes isolées.\n"
        "- Pour les professions rares (pédiatres, pneumologues), un seul départ à la retraite "
        "change fortement la densité des petits départements.\n"
        "- La population n'est pas pondérée par l'âge : un département âgé a des besoins plus élevés.\n"
        "- Les hôpitaux et urgences sont exclus (effectifs trop faibles par département) ; "
        "les sources APL (DREES) ou SAE compléteraient l'analyse."
    )
    
    # Affiche les contrôles de jointure
    render_join_checks(checks)
