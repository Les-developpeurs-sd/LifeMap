"""Chargement, préparation et agrégation des données de santé."""

import json
from pathlib import Path
from typing import Final

import pandas as pd
import streamlit as st


DATA_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "data"
BPE_PATH: Final[Path] = DATA_DIR / "BPE25.parquet"
DEPARTMENT_DATA_PATH: Final[Path] = DATA_DIR / "donnees_departements.csv"
DEPARTMENTS_PATH: Final[Path] = DATA_DIR / "departements-avec-outre-mer.geojson"
REGIONS_PATH: Final[Path] = DATA_DIR / "regions-avec-outre-mer.geojson"

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
def load_department_data() -> pd.DataFrame:
    """Charge le CSV départemental utilisé pour enrichir les données BPE.

    Returns:
        DataFrame contenant les codes ``REG`` et ``DEP``, le nom du département
        issu de la colonne ``Département`` et la population municipale.
    """
    if not DEPARTMENT_DATA_PATH.exists():
        raise FileNotFoundError(f"Fichier absent : {DEPARTMENT_DATA_PATH}")
    data = pd.read_csv(
        DEPARTMENT_DATA_PATH,
        sep=";",
        dtype={"REG": str, "DEP": str},
    ).rename(columns={"Département": "departement", "Région": "region"})
    required = {"REG", "DEP", "departement"}
    if not required.issubset(data.columns):
        raise ValueError(
            f"{DEPARTMENT_DATA_PATH} doit contenir les colonnes {sorted(required)}"
        )
    data["REG"] = data["REG"].map(_normalise_department_code)
    data["DEP"] = data["DEP"].map(_normalise_department_code)
    if "PMUN" in data.columns:
        data["PMUN"] = pd.to_numeric(data["PMUN"], errors="coerce")
    return data.drop_duplicates(["REG", "DEP"])


@st.cache_data(show_spinner=False)
def load_department_geojson() -> dict:
    """Charge les contours départementaux pour une carte choroplèthe.

    Returns:
        Objet GeoJSON compatible avec Plotly.
    """
    with DEPARTMENTS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def load_region_reference() -> pd.DataFrame:
    """Charge les codes et noms des régions administratives.

    Returns:
        DataFrame contenant un code et un nom par région.
    """
    with REGIONS_PATH.open(encoding="utf-8") as file:
        geojson = json.load(file)
    rows = [
        {
            "code_region": _normalise_department_code(feature["properties"]["code"]),
            "region": feature["properties"]["nom"],
        }
        for feature in geojson["features"]
    ]
    return pd.DataFrame(rows).drop_duplicates("code_region")


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
    result["REG"] = result["REG"].map(_normalise_department_code)
    department_data = load_department_data().rename(columns={"DEP": "code_departement"})
    result = result.merge(
        department_data[["REG", "code_departement", "departement", "region", "PMUN"]],
        on=["REG", "code_departement"],
        how="inner",
        validate="many_to_one",
    )
    result = result.rename(columns={"PMUN": "population"})
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
        population_data = population.rename(columns={"population": "population_reference"})
        result = result.merge(
            population_data,
            on="code_departement",
            how="left",
            validate="many_to_one",
        )
        if "population" in result.columns:
            result["population"] = result["population"].fillna(result["population_reference"])
            result = result.drop(columns="population_reference")
        else:
            result = result.rename(columns={"population_reference": "population"})
    elif "population" not in result.columns:
        result["population"] = pd.NA
    if "population" in result.columns:
        result["densite_100k"] = result["equipements"].div(result["population"]).mul(100_000)
    else:
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
