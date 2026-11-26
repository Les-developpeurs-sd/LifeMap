"""Chargement, préparation et agrégation des données de santé.

Ce module est responsable de tout le traitement des données de l'application.
Il gère :
- Le chargement des fichiers de données (BPE, départements, régions, population)
- La normalisation des codes départementaux
- L'agrégation des équipements par département et catégorie
- Le calcul des densités et indicateurs
- La mise en cache des données pour optimiser les performances

Sources de données :
- BPE 2025 (Base Permanente des Équipements) : données brutes des équipements
- donnees_departements.csv : référentiel des départements avec régions et population
- departements-avec-outre-mer.geojson : contours géographiques des départements
- regions-avec-outre-mer.geojson : contours géographiques des régions
- population_departements.csv (optionnel) : population alternative

Les données sont classées par domaines (TYPEQU) selon la nomenclature Insee,
avec un focus sur les équipements de santé (domaine D).
"""

import json
from pathlib import Path
from typing import Final

import pandas as pd
import streamlit as st


# Chemin vers le dossier des données (relatif à ce fichier)
DATA_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "data"

# Chemins vers les fichiers de données principaux
BPE_PATH: Final[Path] = DATA_DIR / "BPE25.parquet"  # Données BPE au format Parquet
DEPARTMENT_DATA_PATH: Final[Path] = DATA_DIR / "donnees_departements.csv"  # Référentiel départements
DEPARTMENTS_PATH: Final[Path] = DATA_DIR / "departements-avec-outre-mer.geojson"  # GeoJSON départements
REGIONS_PATH: Final[Path] = DATA_DIR / "regions-avec-outre-mer.geojson"  # GeoJSON régions


# Nomenclature des équipements de santé (domaine D de la BPE)
# Regroupe les codes TYPEQU par catégorie de professionnels de santé
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

# Dictionnaire inverse pour mapper un code TYPEQU à sa catégorie
CODE_TO_CATEGORY: Final[dict[str, str]] = {
    code: category for category, codes in HEALTH_CODES.items() for code in codes
}


def _normalise_department_code(value: object) -> str:
    """Normalise un code départemental pour garantir un format à 2 caractères.
    
    Cette fonction s'assure que les codes départementaux ont toujours 2 caractères,
    en ajoutant un zéro devant si nécessaire. Cela permet une correspondance
    correcte entre les différentes sources de données.
    
    Args:
        value: Code départemental sous forme de chaîne ou nombre.
               Peut contenir des espaces ou être vide.
    
    Returns:
        str: Code départemental normalisé à 2 caractères.
             Exemples : "1" -> "01", "75" -> "75", "A" -> "A"
    """
    # Convertit en chaîne et supprime les espaces
    code = str(value).strip()
    
    # Si c'est un nombre avec moins de 2 chiffres, ajoute un zéro devant
    if code.isdigit() and len(code) < 2:
        return code.zfill(2)
    
    # Sinon, retourne le code tel quel (pour les codes spéciaux comme "971", "2A", etc.)
    return code


@st.cache_data(show_spinner=False)
def load_department_reference() -> pd.DataFrame:
    """Charge le référentiel des départements et leurs contours géographiques.
    
    Cette fonction lit le fichier GeoJSON des départements et extrait :
    - Le code du département
    - Le nom du département
    
    Les codes sont normalisés pour une correspondance correcte avec d'autres données.
    
    Returns:
        pd.DataFrame: DataFrame avec les colonnes 'code_departement' et 'departement'.
                    Un département par ligne, sans doublons.
    
    Raises:
        FileNotFoundError: Si le fichier GeoJSON n'existe pas.
        json.JSONDecodeError: Si le fichier GeoJSON est mal formé.
    """
    # Ouvre et lit le fichier GeoJSON
    with DEPARTMENTS_PATH.open(encoding="utf-8") as file:
        geojson = json.load(file)
    
    # Extraire les propriétés de chaque département
    rows = [
        {
            "code_departement": _normalise_department_code(feature["properties"]["code"]),
            "departement": feature["properties"]["nom"],
        }
        for feature in geojson["features"]
    ]
    
    # Créer un DataFrame et supprimer les doublons
    return pd.DataFrame(rows).drop_duplicates("code_departement")


@st.cache_data(show_spinner=False)
def load_department_data() -> pd.DataFrame:
    """Charge le fichier CSV contenant les données administratives des départements.
    
    Ce fichier contient les informations administratives de base :
    - Code région (REG)
    - Code département (DEP)
    - Nom du département
    - Nom de la région
    - Population municipale (PMUN)
    
    Returns:
        pd.DataFrame: DataFrame avec les colonnes REG, DEP, departement, region, population.
                    Les codes REG et DEP sont normalisés.
    
    Raises:
        FileNotFoundError: Si le fichier CSV n'existe pas.
        ValueError: Si le fichier ne contient pas les colonnes requises.
    """
    if not DEPARTMENT_DATA_PATH.exists():
        raise FileNotFoundError(f"Fichier absent : {DEPARTMENT_DATA_PATH}")
    
    # Lit le CSV avec un séparateur point-virgule
    data = pd.read_csv(
        DEPARTMENT_DATA_PATH,
        sep=";",
        dtype={"REG": str, "DEP": str},
    ).rename(columns={"Département": "departement", "Région": "region"})
    
    # Vérifie que les colonnes requises sont présentes
    required = {"REG", "DEP", "departement"}
    if not required.issubset(data.columns):
        raise ValueError(
            f"{DEPARTMENT_DATA_PATH} doit contenir les colonnes {sorted(required)}"
        )
    
    # Normalise les codes REG et DEP
    data["REG"] = data["REG"].map(_normalise_department_code)
    data["DEP"] = data["DEP"].map(_normalise_department_code)
    
    # Convertit la population en numérique (avec gestion des erreurs)
    if "PMUN" in data.columns:
        data["PMUN"] = pd.to_numeric(data["PMUN"], errors="coerce")
    
    # Supprime les doublons et retourne
    return data.drop_duplicates(["REG", "DEP"])


@st.cache_data(show_spinner=False)
def load_department_geojson() -> dict:
    """Charge les contours géographiques des départements au format GeoJSON.
    
    Ce GeoJSON est utilisé pour créer les cartes choroplèthes avec Plotly.
    Il contient les polygones de chaque département français (métropole + outre-mer).
    
    Returns:
        dict: Objet GeoJSON compatible avec Plotly Express.
              Contient les propriétés 'code' et 'nom' pour chaque département.
    
    Raises:
        FileNotFoundError: Si le fichier GeoJSON n'existe pas.
        json.JSONDecodeError: Si le fichier GeoJSON est mal formé.
    """
    with DEPARTMENTS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


@st.cache_data(show_spinner=False)
def load_region_reference() -> pd.DataFrame:
    """Charge le référentiel des régions administratives.
    
    Cette fonction lit le fichier GeoJSON des régions et extrait :
    - Le code de la région
    - Le nom de la région
    
    Returns:
        pd.DataFrame: DataFrame avec les colonnes 'code_region' et 'region'.
                    Une région par ligne, sans doublons.
    """
    with REGIONS_PATH.open(encoding="utf-8") as file:
        geojson = json.load(file)
    
    # Extraire les propriétés de chaque région
    rows = [
        {
            "code_region": _normalise_department_code(feature["properties"]["code"]),
            "region": feature["properties"]["nom"],
        }
        for feature in geojson["features"]
    ]
    
    # Créer un DataFrame et supprimer les doublons
    return pd.DataFrame(rows).drop_duplicates("code_region")


@st.cache_data(show_spinner=False)
def load_population_reference() -> pd.DataFrame:
    """Charge le fichier optionnel de population par département.
    
    Ce fichier peut être fourni par l'utilisateur pour remplacer ou compléter
    les données de population du fichier principal. Il permet d'avoir des
    données de population plus récentes ou plus précises.
    
    Returns:
        pd.DataFrame: DataFrame avec les colonnes 'code_departement' et 'population'.
                    Vide si le fichier n'existe pas.
    
    Raises:
        ValueError: Si le fichier existe mais ne contient pas les colonnes requises.
    """
    path = DATA_DIR / "population_departements.csv"
    
    # Si le fichier n'existe pas, retourne un DataFrame vide
    if not path.exists():
        return pd.DataFrame(columns=["code_departement", "population"])
    
    # Lit le CSV
    population = pd.read_csv(path, dtype={"code_departement": str})
    
    # Vérifie que les colonnes requises sont présentes
    required = {"code_departement", "population"}
    if not required.issubset(population.columns):
        raise ValueError(f"{path} doit contenir les colonnes {sorted(required)}")
    
    # Normalise les codes départementaux
    population["code_departement"] = population["code_departement"].map(_normalise_department_code)
    
    # Convertit la population en numérique et supprime les valeurs manquantes
    population["population"] = pd.to_numeric(population["population"], errors="coerce")
    return population.dropna(subset=["population"])


@st.cache_data(show_spinner="Lecture de la BPE 2025…")
def load_health_data() -> pd.DataFrame:
    """Charge la Base Permanente des Équipements (BPE) 2025 et filtre les équipements de santé.
    
    Cette fonction lit le fichier Parquet de la BPE et :
    1. Sélectionne uniquement les colonnes utiles
    2. Filtre pour ne garder que les équipements de santé (domaine D)
    3. Mappe les codes TYPEQU vers des catégories lisibles
    4. Normalise les codes départementaux
    
    Returns:
        pd.DataFrame: DataFrame avec les colonnes TYPEQU, DEP, REG, LIBCOM, NOMRS, 
                    LATITUDE, LONGITUDE, code_departement, categorie.
                    Un équipement par ligne.
    
    Raises:
        FileNotFoundError: Si le fichier Parquet n'existe pas.
    """
    if not BPE_PATH.exists():
        raise FileNotFoundError(f"Fichier absent : {BPE_PATH}")
    
    # Sélectionne uniquement les colonnes nécessaires pour optimiser la lecture
    columns = ["TYPEQU", "DEP", "REG", "LIBCOM", "NOMRS", "LATITUDE", "LONGITUDE"]
    data = pd.read_parquet(BPE_PATH, columns=columns)
    
    # Normalise le code département
    data["code_departement"] = data["DEP"].map(_normalise_department_code)
    
    # Mappe le code TYPEQU vers une catégorie lisible
    data["categorie"] = data["TYPEQU"].map(CODE_TO_CATEGORY)
    
    # Filtre pour ne garder que les équipements avec une catégorie définie
    return data[data["categorie"].notna()].copy()


@st.cache_data(show_spinner=False)
def aggregate_department_data() -> pd.DataFrame:
    """Agrège les équipements de santé par département et catégorie.
    
    Cette fonction est centrale dans le traitement des données. Elle :
    1. Charge les données de santé (via load_health_data)
    2. Compte les équipements par département, région et catégorie
    3. Ajoute les informations de population
    4. Calcule la densité pour 100 000 habitants
    5. Fusionne avec les données administratives
    
    Returns:
        pd.DataFrame: Table longue avec les colonnes :
                    - code_departement, REG, categorie, equipements
                    - departement, region, population
                    - total_equipements (total par département)
                    - densite_100k (équipements pour 100 000 habitants)
    """
    # Charge les données de santé
    health = load_health_data()
    
    # Compte les équipements par département, région et catégorie
    counts = (
        health.groupby(["code_departement", "REG", "categorie"], as_index=False)
        .size()
        .rename(columns={"size": "equipements"})
    )
    
    # Calcule le total d'équipements par département
    departments = (
        counts.groupby(["code_departement", "REG"], as_index=False)["equipements"]
        .sum()
        .rename(columns={"equipements": "total_equipements"})
    )
    
    # Fusionne avec les totaux
    result = counts.merge(departments, on=["code_departement", "REG"], how="left")
    
    # Normalise les codes REG
    result["REG"] = result["REG"].map(_normalise_department_code)
    
    # Charge les données administratives des départements
    department_data = load_department_data().rename(columns={"DEP": "code_departement"})
    
    # Fusionne avec les données administratives
    result = result.merge(
        department_data[["REG", "code_departement", "departement", "region", "PMUN"]],
        on=["REG", "code_departement"],
        how="inner",
        validate="many_to_one",  # Chaque département peut avoir plusieurs catégories
    )
    
    # Renomme la colonne de population
    result = result.rename(columns={"PMUN": "population"})
    
    # Ajoute la densité pour 100 000 habitants
    return add_density(result, load_population_reference())


def add_density(data: pd.DataFrame, population: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ajoute une colonne de densité pour 100 000 habitants.
    
    Cette fonction calcule la densité d'équipements par département en utilisant
    soit la population fournie en paramètre, soit la population déjà présente
    dans les données.
    
    Args:
        data: DataFrame contenant les équipements par département.
              Doit avoir une colonne 'equipements' et optionnellement 'population'.
        population: DataFrame optionnel avec les colonnes 'code_departement' et 'population'.
                   Si fourni, remplace/remplit la population des données.
    
    Returns:
        pd.DataFrame: Copie des données avec une colonne 'densite_100k' ajoutée.
                     La densité est calculée comme : (equipements / population) * 100_000
    """
    result = data.copy()
    
    # Si une table de population alternative est fournie
    if population is not None and not population.empty:
        # Renomme pour éviter les conflits
        population_data = population.rename(columns={"population": "population_reference"})
        
        # Fusionne avec la table de population
        result = result.merge(
            population_data,
            on="code_departement",
            how="left",
            validate="many_to_one",
        )
        
        # Utilise la population de référence si la colonne population existe déjà
        if "population" in result.columns:
            result["population"] = result["population"].fillna(result["population_reference"])
            result = result.drop(columns="population_reference")
        else:
            result = result.rename(columns={"population_reference": "population"})
    
    # Si la colonne population n'existe toujours pas, l'ajoute avec des valeurs manquantes
    elif "population" not in result.columns:
        result["population"] = pd.NA
    
    # Calcule la densité pour 100 000 habitants
    if "population" in result.columns:
        result["densite_100k"] = result["equipements"].div(result["population"]).mul(100_000)
    else:
        result["densite_100k"] = pd.NA
    
    return result


def format_number(value: object, decimals: int = 0) -> str:
    """Formate un nombre selon les conventions françaises.
    
    Cette fonction formate les nombres avec :
    - Des espaces comme séparateurs de milliers
    - Une virgule comme séparateur décimal
    - "N/D" pour les valeurs manquantes
    
    Args:
        value: Valeur à formater (nombre, chaîne, ou NA).
        decimals: Nombre de décimales à afficher (par défaut 0).
    
    Returns:
        str: Chaîne formatée selon les conventions françaises.
             Exemples : 1234 -> "1 234", 1234.56 -> "1 234,56", NA -> "N/D"
    """
    if pd.isna(value):
        return "N/D"
    
    # Formate avec des virgules comme séparateurs de milliers et des points comme séparateurs décimaux
    formatted = f"{float(value):,.{decimals}f}"
    
    # Remplace les virgules par des espaces et les points par des virgules
    return formatted.replace(",", " ").replace(".", ",")
