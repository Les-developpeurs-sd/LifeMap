"""Chargement, préparation et agrégation des données de santé."""

import json
from pathlib import Path
from typing import Final

import pandas as pd
import streamlit as st


DATA_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "data"
BPE_PATH: Final[Path] = DATA_DIR / "BPE25.parquet"
DEPARTMENTS_PATH: Final[Path] = DATA_DIR / "departements-avec-outre-mer.geojson"

# La nomenclature BPE regroupe les équipements de santé dans le domaine D.
HEALTH_CODES: Final[dict[str, tuple[str, ...]]] = {
    "Médecins": tuple(f"D{code}" for code in range(251, 277)),
    "Dentistes": ("D277",),
    "Kinésithérapeutes": ("D279",),
    "Infirmiers": ("D281",),
    "Autres professionnels": ("D245", "D246", "D247", "D248", "D249", "D250", "D278", "D280", "D282", "D283"),
    "Hôpitaux et cliniques": tuple(f"D{code}" for code in range(101, 108)),
    "Centres et maisons de santé": ("D108", "D110", "D113"),
    "Pharmacies": ("D307",),
    "Laboratoires et urgences": ("D109", "D111", "D302", "D303", "D304"),
}
CODE_TO_CATEGORY: Final[dict[str, str]] = {
    code: category for category, codes in HEALTH_CODES.items() for code in codes
}


def _normalise_department_code(value: object) -> str:
    """Normalise un code départemental sans perdre les zéros initiaux.

    Args:
        value: Code lu depuis le parquet ou le GeoJSON.

    Returns:
        Code textuel compatible avec les clés cartographiques.
    """
    code = str(value).strip()
    if code.isdigit() and len(code) < 2:
        return code.zfill(2)
    return code


@st.cache_data(show_spinner=False)
def load_department_reference() -> pd.DataFrame:
    """Charge le référentiel des départements et leurs contours.

    Returns:
        DataFrame contenant les codes et noms des départements.
    """
    with DEPARTMENTS_PATH.open(encoding="utf-8") as file:
        geojson = json.load(file)
    rows = [
        {
            "code_departement": _normalise_department_code(feature["properties"]["code"]),
            "departement": feature["properties"]["nom"],
        }
        for feature in geojson["features"]
    ]
    return pd.DataFrame(rows).drop_duplicates("code_departement")


@st.cache_data(show_spinner=False)
def load_department_geojson() -> dict:
    """Charge les contours départementaux pour une carte choroplèthe.

    Returns:
        Objet GeoJSON compatible avec Plotly.
    """
    with DEPARTMENTS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def load_population_reference() -> pd.DataFrame:
    """Charge la population Insee optionnelle fournie par l'utilisateur.

    Returns:
        Table population, ou table vide si le fichier optionnel est absent.
    """
    path = DATA_DIR / "population_departements.csv"
    if not path.exists():
        return pd.DataFrame(columns=["code_departement", "population"])
    population = pd.read_csv(path, dtype={"code_departement": str})
    required = {"code_departement", "population"}
    if not required.issubset(population.columns):
        raise ValueError(f"{path} doit contenir les colonnes {sorted(required)}")
    population["code_departement"] = population["code_departement"].map(_normalise_department_code)
    population["population"] = pd.to_numeric(population["population"], errors="coerce")
    return population.dropna(subset=["population"])


@st.cache_data(show_spinner="Lecture de la BPE 2025…")
def load_health_data() -> pd.DataFrame:
    """Charge la BPE et conserve uniquement les équipements de santé utiles.

    Returns:
        DataFrame filtré avec un équipement de santé par ligne.
    """
    if not BPE_PATH.exists():
        raise FileNotFoundError(f"Fichier absent : {BPE_PATH}")
    columns = ["TYPEQU", "DEP", "REG", "LIBCOM", "NOMRS", "LATITUDE", "LONGITUDE"]
    data = pd.read_parquet(BPE_PATH, columns=columns)
    data["code_departement"] = data["DEP"].map(_normalise_department_code)
    data["categorie"] = data["TYPEQU"].map(CODE_TO_CATEGORY)
    return data[data["categorie"].notna()].copy()


@st.cache_data(show_spinner=False)
def aggregate_department_data() -> pd.DataFrame:
    """Agrège les équipements de santé par département et catégorie.

    Returns:
        Table longue avec une ligne par département et catégorie.
    """
    health = load_health_data()
    reference = load_department_reference()
    counts = (
        health.groupby(["code_departement", "REG", "categorie"], as_index=False)
        .size()
        .rename(columns={"size": "equipements"})
    )
    departments = (
        counts.groupby(["code_departement", "REG"], as_index=False)["equipements"]
        .sum()
        .rename(columns={"equipements": "total_equipements"})
    )
    result = counts.merge(departments, on=["code_departement", "REG"], how="left")
    result = result.merge(reference, on="code_departement", how="left", validate="many_to_one")
    return add_density(result, load_population_reference())


def add_density(data: pd.DataFrame, population: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ajoute une densité pour 100 000 habitants lorsque la population existe.

    Args:
        data: Agrégats départementaux.
        population: Table optionnelle avec ``code_departement`` et ``population``.

    Returns:
        Copie de la table enrichie d'une colonne ``densite_100k``.
    """
    result = data.copy()
    if population is not None and not population.empty:
        result = result.merge(population, on="code_departement", how="left", validate="many_to_one")
        result["densite_100k"] = result["equipements"].div(result["population"]).mul(100_000)
    else:
        result["population"] = pd.NA
        result["densite_100k"] = pd.NA
    return result


def format_number(value: object, decimals: int = 0) -> str:
    """Formate un nombre selon les conventions françaises.

    Args:
        value: Valeur à formater.
        decimals: Nombre de décimales à afficher.

    Returns:
        Chaîne formatée ou ``N/D`` si la valeur est indisponible.
    """
    if pd.isna(value):
        return "N/D"
    formatted = f"{float(value):,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")
