"""Où déménager pour éviter les déserts médicaux ? Déserts par spécialité, classement
des départements selon le profil, et comparaison détaillée de deux départements."""

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
import sys
from pathlib import Path
from groq import Groq
from gtts import gTTS


def render_department_selector(departments: list[str]) -> tuple[str, str]:
    """Affiche les deux listes déroulantes de comparaison.

    Args:
        departments: Noms des départements disponibles.

    Returns:
        Couple des départements mémorisés dans la session.
    """
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
        submitted = st.form_submit_button("Comparer les territoires")

    if submitted:
        st.session_state["selected_departments"] = [first, second]
    return tuple(st.session_state["selected_departments"])


def get_department_summary(data: pd.DataFrame, department: str) -> dict[str, float]:
    """Calcule les indicateurs synthétiques d'un département.

    Args:
        data: Agrégats départementaux enrichis par le CSV.
        department: Nom du département.

    Returns:
        Dictionnaire contenant volume, population et densité.
    """
    selected = data[data["departement"] == department]
    total = selected["equipements"].sum()
    population = selected["population"].dropna().iloc[0] if selected["population"].notna().any() else 0
    density = total / population * 100_000 if population else 0
    return {"equipements": total, "population": population, "densite": density}


def render_summary(data: pd.DataFrame, first: str, second: str) -> None:
    """Affiche les indicateurs généraux et une conclusion prudente.

    Args:
        data: Agrégats départementaux.
        first: Premier département.
        second: Second département.
    """
    summary_first = get_department_summary(data, first)
    summary_second = get_department_summary(data, second)
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

    density_difference = summary_first["densite"] - summary_second["densite"]
    if density_difference > 0:
        better, other = first, second
    else:
        better, other = second, first
    st.info(
        f"Selon la densité brute observée, **{better}** est mieux doté que **{other}** "
        f"sur l'ensemble des catégories retenues. Cet indicateur mesure une offre "
        "recensée, pas la qualité ni la disponibilité réelle des soins."
    )


def render_category_comparison(data: pd.DataFrame, first: str, second: str) -> None:
    """Compare les catégories d'équipements des deux départements.

    Args:
        data: Agrégats départementaux.
        first: Premier département.
        second: Second département.
    """
    selected = data[data["departement"].isin([first, second])]
    comparison = (
        selected.groupby(["categorie", "departement"], as_index=False)["equipements"]
        .sum()
    )
    fig = px.bar(
        comparison,
        x="categorie",
        y="equipements",
        color="departement",
        barmode="group",
        title="Nombre d'équipements par catégorie",
        labels={"categorie": "", "equipements": "Nombre d'équipements"},
        template="plotly_white",
    )
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        comparison.pivot(index="categorie", columns="departement", values="equipements")
        .fillna(0)
        .reset_index(),
        hide_index=True,
        width="stretch",
    )


def render_density_comparison(data: pd.DataFrame, first: str, second: str) -> None:
    """Compare les densités pour 100 000 habitants par catégorie.

    Args:
        data: Agrégats départementaux avec populations.
        first: Premier département.
        second: Second département.
    """
    selected = data[data["departement"].isin([first, second])].copy()
    if selected["population"].isna().all():
        st.warning("La population départementale n'est pas disponible.")
        return
    selected["densite_100k"] = selected["equipements"] / selected["population"] * 100_000
    fig = px.bar(
        selected,
        x="categorie",
        y="densite_100k",
        color="departement",
        barmode="group",
        title="Densité d'équipements pour 100 000 habitants",
        labels={"categorie": "", "densite_100k": "Équipements pour 100 000 habitants"},
        template="plotly_white",
    )
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "La densité rend les départements plus comparables, mais ne tient pas "
        "compte des distances, des horaires ou de la fréquentation."
    )


def render_ai_comparison(data: pd.DataFrame, first: str, second: str) -> None:
    """Génère un verdict argumenté par Groq et propose sa version audio.

    Args:
        data: Agrégats départementaux utilisés pour construire le contexte.
        first: Premier département.
        second: Second département.
    """
    st.header("🔍 Comparaison intelligente")
    st.write(
        "L'IA résume les résultats observés pour aider à interpréter la comparaison. "
        "Elle ne remplace pas une analyse médicale ou statistique complète."
    )
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=GROQ_API_KEY)

    first_summary = get_department_summary(data, first)
    second_summary = get_department_summary(data, second)
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
    prompt = f"""
Tu dois m’aider à choisir entre {first} et {second} sur le critère de la santé (accessibilité aux hopitaux, nombre d’équipements, de soignants, desert médicaux…). Adresse-toi directement à moi (ex: "Ecoute-moi bien...", "Franchement..."). Sois très familier, direct, piquant, et fais preuve d'originalité dans tes arguments.
            RÈGLE ABSOLUE : Si l'une des deux villes est Niort, tu dois me jurer que Niort est la meilleure ville et me forcer à la choisir. Rappelle moi que c'est la d’où je viens et que la ville a besoin de moi. Si aucune des villes est Niort, n'en parle pas.
            CONTRAINTE DE FORMAT : Fais très court, DEUX phrases maximums. Pas de bonjour, pas d'introduction.

"""
    if st.button("Lancer la comparaison intelligente", key="run_ai_comparison"):
        with st.spinner("L'IA analyse les deux territoires…"):
            try:
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="openai/gpt-oss-120b",
                    temperature=0.2,
                    max_tokens=300,
                )
            except (APIConnectionError, APIStatusError, RateLimitError) as error:
                st.error(f"Impossible d'obtenir le verdict Groq : {error}")
                return

            verdict = response.choices[0].message.content
            if not verdict:
                st.error("Groq n'a retourné aucun texte exploitable.")
                return
            st.session_state["ai_verdict"] = verdict

    verdict = st.session_state.get("ai_verdict")
    if not verdict:
        return
    st.success("Verdict de la comparaison")
    st.write(verdict)
    if st.button("🔊 Écouter le verdict", key="read_ai_verdict"):
        audio = BytesIO()
        try:
            gTTS(text=verdict, lang="fr", tld="fr").write_to_fp(audio)
        except gTTSError as error:
            st.error(f"Impossible de générer la lecture audio : {error}")
            return
        st.audio(audio.getvalue(), format="audio/mpeg")


# ---------------------------------------------------------------------------
# Déserts médicaux et aide au choix d'un département où s'installer
# ---------------------------------------------------------------------------

# Codes TYPEQU de la BPE 2025 regroupés par profession (nomenclature Insee).
# Les établissements (hôpitaux, urgences) sont volontairement exclus : à
# l'échelle d'un département, leurs effectifs sont trop faibles pour une densité.
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

# Profils types : présélection de professions selon le besoin du ménage.
PROFILES: dict[str, list[str]] = {
    "Famille avec enfants": [
        "Médecin généraliste", "Pédiatre", "Dentiste", "Pharmacie", "Gynécologue / obstétricien",
    ],
    "Senior / retraité": [
        "Médecin généraliste", "Cardiologue", "Ophtalmologue", "Infirmier",
        "Kinésithérapeute", "Pharmacie",
    ],
    "Actif en bonne santé": ["Médecin généraliste", "Dentiste", "Pharmacie"],
    "Tous les besoins": list(SPECIALTIES),
    "Personnalisé": [],
}

STATUS_ORDER: list[str] = ["Désert médical", "Sous-doté", "Bien doté"]
STATUS_COLORS: dict[str, str] = {
    "Désert médical": "#dc2626",
    "Sous-doté": "#f59e0b",
    "Bien doté": "#16a34a",
}
INDEX_CAP: float = 2.0  # un département 2 fois mieux doté que la moyenne = score maximal
DEFAULT_MOVE_SETTINGS: dict = {
    "specialties": PROFILES["Famille avec enfants"],
    "regions": [],
    "metropole_only": True,
    "threshold": 60,
    "exclude_deserts": True,
    "top_n": 10,
}
MAP_CENTER: dict[str, float] = {"lat": 46.6, "lon": 2.4}


@st.cache_data(show_spinner="Calcul des densités par spécialité…")
def build_specialty_table() -> tuple[pd.DataFrame, dict]:
    """Croise la BPE (offre de soins) avec la population départementale.

    Pour chaque couple département x profession, calcule le nombre de lieux
    d'exercice, la densité pour 100 000 habitants et un indice d'accès égal à
    la densité du département divisée par la densité nationale (1 = moyenne
    nationale). Les couples sans équipement sont conservés avec 0 : c'est
    justement le signe d'un désert médical.

    Returns:
        Un couple (table, controles) : la table longue (une ligne par
        département et profession) et un dictionnaire de contrôles de jointure
        (lignes avant/après, clés sans correspondance).
    """
    code_to_label = {code: label for label, codes in SPECIALTIES.items() for code in codes}
    health = load_health_data()
    subset = health[health["TYPEQU"].isin(code_to_label)]
    counts = subset.groupby(["code_departement", "TYPEQU"], as_index=False).size()
    counts = counts.rename(columns={"size": "equipements"})
    counts["specialite"] = counts["TYPEQU"].map(code_to_label)
    counts = counts.groupby(["code_departement", "specialite"], as_index=False)["equipements"].sum()

    departments = (
        load_department_data()
        .rename(columns={"DEP": "code_departement", "PMUN": "population"})
        [["code_departement", "departement", "region", "population"]]
    )
    present = [label for label in SPECIALTIES if label in set(counts["specialite"])]
    grid = departments.merge(pd.DataFrame({"specialite": present}), how="cross")
    table = grid.merge(
        counts, on=["code_departement", "specialite"], how="left", validate="one_to_one"
    )
    table["equipements"] = table["equipements"].fillna(0)

    bpe_codes = set(counts["code_departement"])
    reference_codes = set(departments["code_departement"])
    matched = counts[counts["code_departement"].isin(reference_codes)]
    checks = {
        "lignes_bpe_professions": len(subset),
        "lignes_agregees": len(counts),
        "lignes_table_finale": len(table),
        "lignes_attendues": len(departments) * len(present),
        "codes_bpe_sans_population": sorted(bpe_codes - reference_codes),
        "departements_sans_equipement": sorted(reference_codes - bpe_codes),
        "equipements_perdus": int(counts["equipements"].sum() - matched["equipements"].sum()),
        "specialites_absentes": [label for label in SPECIALTIES if label not in present],
    }

    table["densite_100k"] = table["equipements"] / table["population"] * 100_000
    national = (
        table.groupby("specialite")["equipements"].transform("sum")
        / table.groupby("specialite")["population"].transform("sum")
        * 100_000
    )
    table["densite_nationale"] = national
    table = table[table["densite_nationale"] > 0].copy()
    table["indice"] = table["densite_100k"] / table["densite_nationale"]
    table["metropole"] = ~table["code_departement"].str.startswith("97")
    return table.reset_index(drop=True), checks


def classify_status(indice: pd.Series, threshold: float) -> pd.Series:
    """Classe chaque département selon son indice d'accès.

    Args:
        indice: Densité du département / densité nationale (1 = moyenne).
        threshold: Seuil de désert, en part de la moyenne nationale (ex. 0,6).

    Returns:
        Série de libellés : « Désert médical », « Sous-doté » ou « Bien doté ».
    """
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
    """Classe les départements selon les professions choisies par la personne.

    Le score d'accès (0 à 100) est la moyenne des indices d'accès plafonnés à
    2 fois la moyenne nationale : 50 correspond à la moyenne nationale. Un
    plafond évite qu'une seule profession très dense compense des manques.

    Args:
        table: Table produite par ``build_specialty_table``.
        specialties: Professions jugées importantes.
        threshold: Seuil de désert (part de la moyenne nationale).
        regions: Régions retenues (liste vide = toutes).
        metropole_only: Écarte les départements d'outre-mer si vrai.
        exclude_deserts: Écarte les départements ayant au moins un désert.

    Returns:
        Un couple (classement, détail) : classement par département (rang,
        score, nombre de déserts, point faible) et détail par profession.
    """
    selected = table[table["specialite"].isin(specialties)].copy()
    if metropole_only:
        selected = selected[selected["metropole"]]
    if regions:
        selected = selected[selected["region"].isin(regions)]
    if selected.empty:
        return pd.DataFrame(), selected
    selected["indice_plafonne"] = selected["indice"].clip(upper=INDEX_CAP)
    selected["desert"] = selected["indice"] < threshold
    ranking = selected.groupby(
        ["code_departement", "departement", "region", "population"], as_index=False
    ).agg(
        score=("indice_plafonne", "mean"),
        nb_deserts=("desert", "sum"),
    )
    ranking["score"] = ranking["score"] / INDEX_CAP * 100
    worst = selected.loc[
        selected.groupby("code_departement")["indice"].idxmin(),
        ["code_departement", "specialite", "indice"],
    ].rename(columns={"specialite": "point_faible", "indice": "indice_point_faible"})
    ranking = ranking.merge(worst, on="code_departement", how="left", validate="one_to_one")
    if exclude_deserts:
        ranking = ranking[ranking["nb_deserts"] == 0]
    ranking = ranking.sort_values("score", ascending=False).reset_index(drop=True)
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
):
    """Construit une carte choroplèthe des départements de métropole.

    Args:
        data: Table avec ``code_departement`` et ``departement``.
        color: Colonne servant à colorer les départements.
        labels: Libellés affichés dans la légende et l'infobulle.
        hover_data: Colonnes supplémentaires de l'infobulle.
        discrete_map: Couleurs par modalité si ``color`` est catégorielle.
        scale: Échelle continue utilisée sinon.
        category_orders: Ordre des modalités pour une variable catégorielle.

    Returns:
        Figure Plotly prête à être affichée.
    """
    options = {
        "color_discrete_map": discrete_map,
        "category_orders": category_orders,
    } if discrete_map else {"color_continuous_scale": scale}
    fig = px.choropleth_map(
        data,
        geojson=load_department_geojson(),
        locations="code_departement",
        featureidkey="properties.code",
        color=color,
        hover_name="departement",
        hover_data=hover_data,
        center=MAP_CENTER,
        zoom=4.6,
        map_style="carto-positron",
        labels=labels,
        **options,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=520)
    return fig


def render_desert_overview(table: pd.DataFrame) -> None:
    """Affiche la carte et les chiffres clés des déserts pour une profession.

    Args:
        table: Table produite par ``build_specialty_table``.
    """
    st.subheader("Où sont les déserts médicaux, profession par profession ?")
    st.write(
        "Un département est classé **désert médical** pour une profession lorsque sa "
        "densité (lieux d'exercice pour 100 000 habitants) est inférieure à un seuil "
        "exprimé en part de la **moyenne nationale**. Réglez le seuil et la profession."
    )
    left, right = st.columns([2, 1])
    specialty = left.selectbox("Profession", list(table["specialite"].unique()), key="desert_specialty")
    threshold = right.slider(
        "Seuil de désert (% de la moyenne nationale)", 20, 90, 60, 5, key="desert_threshold"
    ) / 100

    current = table[table["specialite"] == specialty].copy()
    current["statut"] = classify_status(current["indice"], threshold)
    deserts = current[current["statut"] == STATUS_ORDER[0]]
    national_density = current["densite_nationale"].iloc[0]
    population_total = current["population"].sum()
    population_desert = deserts["population"].sum()

    first, second, third, fourth = st.columns(4)
    first.metric("Départements en désert", format_number(len(deserts)))
    second.metric("Habitants concernés", format_number(population_desert))
    third.metric("Part de la population", f"{population_desert / population_total * 100:.1f} %".replace(".", ","))
    fourth.metric("Moyenne nationale / 100 000 hab.", format_number(national_density, 1))

    map_data = current[current["metropole"]]
    fig_map = make_department_map(
        map_data,
        color="statut",
        labels={"statut": "Situation", "densite_100k": "Densité / 100 000 hab."},
        hover_data={"code_departement": False, "densite_100k": ":.1f", "indice": ":.2f"},
        discrete_map=STATUS_COLORS,
        category_orders={"statut": STATUS_ORDER},
    )
    st.plotly_chart(fig_map, width="stretch")
    st.caption("Carte de la France métropolitaine. L'outre-mer figure dans le graphique et le tableau.")

    worst = current.sort_values("densite_100k").head(15).sort_values("densite_100k", ascending=False)
    fig_bar = px.bar(
        worst,
        x="densite_100k",
        y="departement",
        orientation="h",
        color="statut",
        color_discrete_map=STATUS_COLORS,
        category_orders={"statut": STATUS_ORDER},
        title=f"Les 15 départements les moins dotés : {specialty}",
        labels={"densite_100k": "Lieux d'exercice pour 100 000 habitants", "departement": "", "statut": ""},
        template="plotly_white",
    )
    fig_bar.add_vline(
        x=national_density, line_dash="dash", line_color="#1e293b",
        annotation_text="Moyenne nationale", annotation_position="top",
    )
    st.plotly_chart(fig_bar, width="stretch")

    best = current.sort_values("densite_100k", ascending=False).iloc[0]
    st.info(
        f"**Constat** : pour « {specialty} », **{len(deserts)} départements** sont en désert "
        f"(< {threshold * 100:.0f} % de la moyenne), soit **{format_number(population_desert / population_total * 100, 1)} %** "
        f"de la population. L'écart va de {format_number(current['densite_100k'].min(), 1)} à "
        f"{format_number(best['densite_100k'], 1)} pour 100 000 habitants ({best['departement']})."
    )


def render_desert_cumulation(table: pd.DataFrame) -> None:
    """Montre les départements qui cumulent les déserts et les spécialités touchées.

    Args:
        table: Table produite par ``build_specialty_table``.
    """
    st.subheader("Les départements qui cumulent les déserts")
    threshold = st.session_state.get("desert_threshold", 60) / 100
    st.caption(
        f"Seuil utilisé : {threshold * 100:.0f} % de la moyenne nationale (réglé ci-dessus)."
    )
    work = table.copy()
    work["desert"] = work["indice"] < threshold
    cumul = (
        work.groupby(["code_departement", "departement", "region", "metropole"], as_index=False)
        .agg(nb_deserts=("desert", "sum"))
    )
    total = work["specialite"].nunique()
    map_col, bar_col = st.columns([3, 2])
    with map_col:
        fig_map = make_department_map(
            cumul[cumul["metropole"]],
            color="nb_deserts",
            labels={"nb_deserts": f"Déserts (sur {total})"},
            scale="Reds",
        )
        st.plotly_chart(fig_map, width="stretch")
    with bar_col:
        top = cumul.sort_values("nb_deserts", ascending=False).head(15).sort_values("nb_deserts")
        fig_bar = px.bar(
            top, x="nb_deserts", y="departement", orientation="h",
            title=f"Professions en désert (sur {total})", template="plotly_white",
            labels={"nb_deserts": "Nombre de professions en désert", "departement": ""},
            color="nb_deserts", color_continuous_scale="Reds",
        )
        fig_bar.update_coloraxes(showscale=False)
        st.plotly_chart(fig_bar, width="stretch")

    worst_ids = cumul.sort_values("nb_deserts", ascending=False).head(20)["code_departement"]
    heat = work[work["code_departement"].isin(worst_ids)].copy()
    heat["indice_plafonne"] = heat["indice"].clip(upper=INDEX_CAP)
    pivot = heat.pivot(index="departement", columns="specialite", values="indice_plafonne")
    pivot = pivot.loc[
        cumul.set_index("departement").loc[pivot.index, "nb_deserts"].sort_values(ascending=False).index
    ]
    fig_heat = px.imshow(
        pivot, color_continuous_scale="RdYlGn", zmin=0, zmax=INDEX_CAP, aspect="auto",
        text_auto=".1f", title="Indice d'accès des 20 départements les plus touchés (1 = moyenne nationale)",
        labels={"color": "Indice"},
    )
    fig_heat.update_xaxes(tickangle=-40, title="")
    fig_heat.update_yaxes(title="")
    fig_heat.update_layout(height=620)
    st.plotly_chart(fig_heat, width="stretch")

    most_hit = work[work["desert"]].groupby("specialite").size().sort_values(ascending=False)
    if not most_hit.empty:
        st.info(
            f"**Constat** : {int((cumul['nb_deserts'] >= 3).sum())} départements cumulent au moins "
            f"3 déserts. La profession la plus souvent en désert est **{most_hit.index[0]}** "
            f"({most_hit.iloc[0]} départements)."
        )


def render_inequality(table: pd.DataFrame) -> None:
    """Compare l'inégalité de répartition entre professions.

    Args:
        table: Table produite par ``build_specialty_table``.
    """
    st.subheader("Quelles professions sont les plus inégalement réparties ?")
    plot_data = table.copy()
    plot_data["indice_affiche"] = plot_data["indice"].clip(upper=3)
    stats = plot_data.groupby("specialite")["densite_100k"].agg(["std", "mean"])
    stats["variation"] = stats["std"] / stats["mean"]
    order = stats.sort_values("variation", ascending=False).index.tolist()
    fig = px.box(
        plot_data, x="specialite", y="indice_affiche", points="outliers",
        category_orders={"specialite": order}, template="plotly_white",
        labels={"specialite": "", "indice_affiche": "Indice d'accès (1 = moyenne nationale)"},
        title="Dispersion de l'indice d'accès entre départements (du plus au moins inégal)",
    )
    fig.add_hline(y=1, line_dash="dash", line_color="#1e293b")
    fig.update_xaxes(tickangle=-40)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Plus la boîte est étendue, plus la profession est inégalement répartie. "
        "Les valeurs sont plafonnées à 3 pour la lisibilité."
    )
    st.info(
        f"**Constat** : la répartition la plus inégale concerne **{order[0]}** et la plus "
        f"homogène **{order[-1]}** (coefficient de variation entre départements)."
    )


def apply_profile() -> None:
    """Remplit la liste des professions selon le profil choisi (callback)."""
    profile = st.session_state["move_profile"]
    if profile != "Personnalisé":
        st.session_state["move_specialties"] = list(PROFILES[profile])


def render_move_form(table: pd.DataFrame) -> dict:
    """Affiche le formulaire de critères et mémorise la dernière validation.

    ``st.form`` regroupe les critères derrière un seul bouton pour éviter de
    recalculer le classement à chaque clic ; ``st.session_state`` conserve les
    critères validés d'une interaction à l'autre.

    Args:
        table: Table produite par ``build_specialty_table``.

    Returns:
        Dictionnaire des critères validés.
    """
    available = list(table["specialite"].unique())
    if "move_settings" not in st.session_state:
        st.session_state["move_settings"] = {
            **DEFAULT_MOVE_SETTINGS,
            "specialties": [s for s in DEFAULT_MOVE_SETTINGS["specialties"] if s in available],
        }
        st.session_state["move_specialties"] = st.session_state["move_settings"]["specialties"]

    st.selectbox(
        "Votre profil (présélectionne les professions utiles)",
        list(PROFILES),
        key="move_profile",
        on_change=apply_profile,
    )
    regions = sorted(table["region"].dropna().unique())
    with st.form("move_criteria"):
        chosen = st.multiselect(
            "Professions dont vous avez besoin à proximité",
            available,
            key="move_specialties",
        )
        col_a, col_b = st.columns(2)
        with col_a:
            chosen_regions = st.multiselect("Limiter à certaines régions (vide = toutes)", regions)
            threshold = st.slider("Seuil de désert (% de la moyenne nationale)", 20, 90, 60, 5)
        with col_b:
            top_n = st.slider("Nombre de départements à afficher", 5, 20, 10)
            metropole_only = st.checkbox("Métropole uniquement", value=True)
            exclude = st.checkbox("Écarter les départements avec au moins un désert", value=True)
        submitted = st.form_submit_button("Trouver mes départements")

    if submitted:
        if not chosen:
            st.warning("Choisissez au moins une profession.")
        else:
            st.session_state["move_settings"] = {
                "specialties": chosen,
                "regions": chosen_regions,
                "metropole_only": metropole_only,
                "threshold": threshold,
                "exclude_deserts": exclude,
                "top_n": top_n,
            }
    st.caption("Après avoir changé de profil ou de critères, cliquez sur « Trouver mes départements ».")
    return st.session_state["move_settings"]


def render_move_results(table: pd.DataFrame, settings: dict) -> None:
    """Affiche le classement, la carte et le détail des départements conseillés.

    Args:
        table: Table produite par ``build_specialty_table``.
        settings: Critères validés dans le formulaire.
    """
    ranking, detail = compute_access_ranking(
        table,
        settings["specialties"],
        settings["threshold"] / 100,
        settings["regions"],
        settings["metropole_only"],
        settings["exclude_deserts"],
    )
    if ranking.empty:
        st.warning(
            "Aucun département ne répond à ces critères. Baissez le seuil de désert, "
            "retirez des professions ou décochez l'exclusion des déserts."
        )
        return
    top = ranking.head(settings["top_n"])

    st.success(
        "**Départements à privilégier :** "
        + ", ".join(f"{row.departement} ({row.score:.0f}/100)" for row in top.head(3).itertuples())
    )
    first, second, third = st.columns(3)
    first.metric("Départements retenus", format_number(len(ranking)))
    second.metric("Meilleur score", f"{top['score'].iloc[0]:.0f} / 100")
    third.metric("Score = moyenne nationale", "50 / 100")

    bar_data = top.sort_values("score")
    fig_bar = px.bar(
        bar_data, x="score", y="departement", orientation="h", color="score",
        color_continuous_scale="Greens", template="plotly_white",
        hover_data={"region": True, "nb_deserts": True, "score": ":.0f"},
        title=f"Top {len(top)} des départements pour votre profil",
        labels={"score": "Score d'accès (50 = moyenne nationale)", "departement": ""},
    )
    fig_bar.update_coloraxes(showscale=False)
    fig_bar.add_vline(x=50, line_dash="dash", line_color="#1e293b")
    st.plotly_chart(fig_bar, width="stretch")

    map_col, heat_col = st.columns(2)
    with map_col:
        st.markdown("**Carte des départements retenus**")
        fig_map = make_department_map(
            ranking[~ranking["code_departement"].str.startswith("97")],
            color="score",
            labels={"score": "Score"},
            scale="Greens",
        )
        st.plotly_chart(fig_map, width="stretch")
        st.caption("En blanc : départements écartés (désert sur un critère, région ou outre-mer).")
    with heat_col:
        st.markdown("**Détail par profession (1 = moyenne nationale)**")
        heat = detail[detail["code_departement"].isin(top["code_departement"])].copy()
        heat["indice_plafonne"] = heat["indice"].clip(upper=INDEX_CAP)
        pivot = heat.pivot(index="departement", columns="specialite", values="indice_plafonne")
        pivot = pivot.loc[top["departement"]]
        fig_heat = px.imshow(
            pivot, color_continuous_scale="RdYlGn", zmin=0, zmax=INDEX_CAP, aspect="auto",
            text_auto=".1f", labels={"color": "Indice"},
        )
        fig_heat.update_xaxes(tickangle=-40, title="")
        fig_heat.update_yaxes(title="")
        fig_heat.update_layout(height=520, margin={"t": 10})
        st.plotly_chart(fig_heat, width="stretch")

    display = top.rename(
        columns={
            "rang": "Rang", "departement": "Département", "region": "Région",
            "population": "Population", "score": "Score", "nb_deserts": "Déserts",
            "point_faible": "Point faible", "indice_point_faible": "Indice du point faible",
        }
    ).drop(columns="code_departement")
    display["Score"] = display["Score"].round(1)
    display["Indice du point faible"] = display["Indice du point faible"].round(2)
    st.dataframe(display, hide_index=True, width="stretch")
    st.download_button(
        "Télécharger le classement (CSV)",
        display.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="departements_conseilles.csv",
        mime="text/csv",
    )
    st.info(
        f"**Conclusion** : pour le profil choisi, **{top['departement'].iloc[0]}** offre le meilleur "
        f"accès ({top['score'].iloc[0]:.0f}/100). Le point faible le plus fréquent parmi les "
        f"{len(top)} premiers est **{top['point_faible'].mode().iloc[0]}**. Vérifiez toujours les "
        "délais de rendez-vous et les distances sur place avant de déménager."
    )


def render_move_tab(table: pd.DataFrame) -> None:
    """Affiche l'onglet « Où déménager ? » (formulaire puis résultats).

    Args:
        table: Table produite par ``build_specialty_table``.
    """
    st.subheader("Trouver les départements les mieux dotés pour mon profil")
    st.write(
        "Indiquez les professions de santé dont vous avez besoin : l'application calcule "
        "un score d'accès par département et écarte ceux où l'une d'elles est en désert."
    )
    settings = render_move_form(table)
    render_move_results(table, settings)


def render_join_checks(checks: dict) -> None:
    """Affiche les contrôles de jointure BPE x population.

    Args:
        checks: Dictionnaire renvoyé par ``build_specialty_table``.
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
    """Affiche la comparaison de deux départements sur une seule page, sans sous-onglets.

    Args:
        data: Agrégats départementaux issus de ``aggregate_department_data``.
    """
    departments = sorted(data["departement"].dropna().unique())
    if len(departments) < 2:
        st.error("Deux départements sont nécessaires pour lancer une comparaison.")
        return
    first, second = render_department_selector(departments)
    if first == second:
        st.warning("Veuillez choisir deux départements différents.")
        return

    st.divider()
    render_summary(data, first, second)

    st.divider()
    try:
        render_ai_comparison(data, first, second)
    except (KeyError, FileNotFoundError):
        st.info("Ajoutez GROQ_API_KEY dans .streamlit/secrets.toml pour activer la comparaison intelligente.")

    st.divider()
    st.header("🩺 Comparaison des catégories de soins")
    render_category_comparison(data, first, second)

    st.divider()
    st.header("📈 Une comparaison équitable par population")
    render_density_comparison(data, first, second)


def render_limits(checks: dict) -> None:
    """Affiche la méthode, les limites d'interprétation et les contrôles de jointure.

    Args:
        checks: Dictionnaire renvoyé par ``build_specialty_table``.
    """
    st.header("Comment interpréter les résultats ?")
    st.warning(
        "La BPE compte des lieux d'exercice et équipements, pas nécessairement "
        "des personnes uniques. Un praticien présent à plusieurs adresses peut "
        "être compté plusieurs fois."
    )
    st.write(
        "Les médecins salariés des hôpitaux ne sont pas inclus. Les résultats "
        "ne mesurent pas les délais de rendez-vous, les distances, les tarifs "
        "ou la qualité des soins. Ils servent donc à comparer une offre "
        "recensée et non à produire un avis médical."
    )
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
    render_join_checks(checks)


def render_decision() -> None:
    """Affiche la page complète : déserts médicaux, aide au choix et comparaison."""
    st.set_page_config(
        page_title="Éviter les déserts médicaux",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Comparer")
    st.markdown(
        """
        <div style="text-align:center; padding:1.5rem 0 0.5rem 0;">
            <h1 style="font-size:2.2rem; margin:0;">Où déménager pour éviter les déserts médicaux ?</h1>
            <p style="color:#64748b; font-size:1.05rem;">
                Repérez les déserts médicaux par profession, puis trouvez les départements
                les mieux dotés pour votre profil
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    table, checks = build_specialty_table()
    deserts, move, compare, limits = st.tabs(
        [
            "🏜️ Déserts médicaux",
            "🧭 Où déménager ?",
            "🔄 Comparer deux départements",
            "⚠️ Limites",
        ]
    )
    with deserts:
        render_desert_overview(table)
        st.divider()
        render_desert_cumulation(table)
        st.divider()
        render_inequality(table)
    with move:
        render_move_tab(table)
    with compare:
        render_comparison(aggregate_department_data())
    with limits:
        render_limits(checks)
    render_footer()


if __name__ == "__main__":
    render_decision()
