"""Comparaison détaillée de deux départements sur l'offre de santé."""

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from gtts import gTTS
from gtts.tts import gTTSError

from utils.data_loader import aggregate_department_data, format_number
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
Tu es un assistant d'analyse territoriale en santé. Compare {first} et {second}
à partir des données Insee BPE 2025 fournies ci-dessous.
{first}: {first_summary}
{second}: {second_summary}
Répartition par catégorie: {categories}

Donne un verdict en français, factuel et accessible, en quatre phrases maximum.
Indique quel territoire semble le mieux doté en volume et en densité, cite une
limite importante de la BPE, et ne présente jamais ce résultat comme un avis
médical. Ne fabrique aucune donnée.
"""
    if st.button("Lancer la comparaison intelligente", key="run_ai_comparison"):
        with st.spinner("L'IA analyse les deux territoires…"):
            try:
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="openai/gpt-oss-20b",
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


def render_decision() -> None:
    """Affiche la page complète de comparaison des départements."""
    st.set_page_config(
        page_title="Comparer les territoires",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Comparer")
    st.markdown(
        """
        <div style="text-align:center; padding:1.5rem 0 0.5rem 0;">
            <h1 style="font-size:2.2rem; margin:0;">Comparaison des territoires</h1>
            <p style="color:#64748b; font-size:1.05rem;">
                Comparez deux départements selon leur offre médicale et sanitaire
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data = aggregate_department_data()
    departments = sorted(data["departement"].dropna().unique())
    if len(departments) < 2:
        st.error("Deux départements sont nécessaires pour lancer une comparaison.")
        return
    first, second = render_department_selector(departments)
    if first == second:
        st.warning("Veuillez choisir deux départements différents.")
        return

    intelligent, overview, categories, densities, limits = st.tabs(
        [
            "🔍 Comparaison intelligente",
            "📊 Vue d'ensemble",
            "🩺 Catégories de soins",
            "📈 Densités",
            "⚠️ Limites",
        ]
    )
    with intelligent:
        render_ai_comparison(data, first, second)
    with overview:
        render_summary(data, first, second)
    with categories:
        st.header("Comparaison des catégories de soins")
        render_category_comparison(data, first, second)
    with densities:
        st.header("Une comparaison équitable par population")
        render_density_comparison(data, first, second)
    with limits:
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
    render_footer()


if __name__ == "__main__":
    render_decision()
