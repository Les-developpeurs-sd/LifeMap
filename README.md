# LifeMap : Santé Où Habiter

Application Streamlit répondant à la question :

> **Où faut-il habiter par rapport au médical et à la santé ?**
Elle compare l'offre de soins des départements français à partir des équipements recensés par l'Insee. L'objectif est de repérer les territoires les mieux dotés et de comprendre pourquoi un classement brut ne suffit pas à conclure : un département très peuplé compte mécaniquement davantage de lieux de soins.

---

## **📌 1. Fonctionnalités**

LifeMap offre plusieurs fonctionnalités clés pour analyser et comparer l'offre de santé en France :

### **🔍 Exploration interactive**
Filtrer les départements par **région**, **type d'offre** (catégorie d'équipement) et **nombre d'équipements** (min/max)


### **🏜️ Analyse des déserts médicaux**
Visualiser les **déserts médicaux par spécialité** (médecin généraliste, pédiatre, gynécologue, dentiste, etc.)


### **📊 Comparaison de deux départements**
Sélectionner **deux territoires** pour une comparaison côté à côte

### **🧭 Où déménager ? (Aide au choix)**
- Sélectionner un **profil type** (Famille avec enfants, Senior/retraité, Actif en bonne santé, Tous les besoins) pour savoir où déménager


### **🤖 Comparaison intelligente avec IA**
Génération d'un **verdict personnalisé** comparant deux départements avec **Synthèse vocale** : Écouter le verdict grâce à la génération audio (gTTS)


---

## **📊 2. Données**

LifeMap utilise plusieurs sources de données officielles pour fournir une analyse complète et précise :

### **Sources principales**

| Fichier | Source | Description | Format |
|---------|--------|-------------|--------|
| **BPE25.parquet** | Insee | Base Permanente des Équipements 2025. Contient tous les équipements et lieux d'exercice en France. | Parquet |
| **donnees_departements.csv** | Insee | Référentiel des départements avec codes REG, DEP, noms et population municipale (PMUN). | CSV (séparateur ;) |
| **departements-avec-outre-mer.geojson** | Insee | Contours géographiques (polygones) de tous les départements français (métropole + outre-mer). | GeoJSON |


### **Nomenclature des équipements**

Les équipements sont classés selon la **nomenclature TYPEQU de l'Insee** (domaine D pour la santé) :


### **Traitement des données**

- **Normalisation** : Les codes départementaux sont normalisés à 2 caractères (ex: "1" → "01")
- **Agrégation** : Les équipements sont comptés par département et catégorie
- **Calcul des densités** : Nombre d'équipements pour 100 000 habitants
- **Indice d'accès** : Densité du département / densité nationale (1 = moyenne nationale)
- **Score d'accès** : Moyenne des indices plafonnés à 2, ramenée sur 100 (50 = moyenne nationale)

---

## **⚙️ 3. Installation et lancement**

### **🌐 Version en ligne (Streamlit Community Cloud)**

Le projet est hébergé sur **Streamlit Community Cloud** et accessible à l'adresse suivante :

🔗 [https://lifemapsd.streamlit.app](https://lifemapsd.streamlit.app)

> ✅ **Toutes les fonctionnalités sont disponibles en ligne**, y compris l'IA Groq (clé API déjà configurée sur le cloud).

### **💻 Version locale (sans fonctionnalité IA)**

Pour exécuter l'application en local sur votre machine :

#### **Prérequis**
- Python 3.9+
- pip (gestionnaire de paquets Python)
- Git (optionnel, pour cloner le dépôt)

#### **Étapes d'installation**

1. **Télécharger le ZIP** 

2. **Créer un environnement virtuel** (optionnel) :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Linux/Mac
   .\venv\Scripts\activate   # Sur Windows
   ```

3. **Installer les dépendances** :
   ```bash
    pip install -r requirements.txt
    ```

4. **Lancer l'application** :
   ```bash
    streamlit run app.py
    ```

---

## **🗂️ 4. Organisation du projet**

```
LifeMap/
├── app.py                          # Point d'entrée principal (page d'accueil)
├── README.md                        # Ce fichier
├── requirements.txt                 # Dépendances Python
│
├── .streamlit/                      # Configuration Streamlit
│   └── config.toml                  # Configuration de l'application
│
├── pages/                           # Pages supplémentaires de l'application
│   ├── 2_Decider.py                 # Page "Déserts médicaux"
│   ├── 3_Demenager.py               # Page "Où déménager ?"
│   └── 4_Comparer.py               # Page "Comparer deux départements"
│
├── utils/                           # Modules utilitaires et composants
│   ├── data_loader.py               # Chargement et traitement des données
│   ├── navbar.py                    # Composants de navigation (CSS, navbar, footer)
│   ├── explorer_components.py       # Composants de la page d'exploration
│   └── decider_components.py        # Composants des pages Décider, Déménager et Comparer
│
└── data/                            # Données (non incluses dans le dépôt Git)
    ├── BPE25.parquet                 # Base Permanente des Équipements 2025
    ├── donnees_departements.csv      # Référentiel des départements
    ├── departements-avec-outre-mer.geojson  # Contours des départements
    ├── regions-avec-outre-mer.geojson       # Contours des régions
    └── population_departements.csv  # Données de population optionnelles
```

### **Rôle des principaux fichiers**

| Fichier | Rôle |
|---------|------|
| **app.py** | Configure et affiche la page d'accueil avec l'explorateur d'offre de soins |
| **pages/2_Decider.py** | Gère la page d'analyse des déserts médicaux par spécialité |
| **pages/3_Demenager.py** | Fournit une aide au choix de département avec classements personnalisés |
| **pages/4_Comparer.py** | Permet la comparaison détaillée de deux départements |
| **utils/data_loader.py** | Charge et traite toutes les données (BPE, départements, régions, population) |
| **utils/navbar.py** | Définit le thème visuel et les composants de navigation |
| **utils/explorer_components.py** | Contient les fonctions de filtrage et d'affichage pour l'explorateur |
| **utils/decider_components.py** | Contient toutes les fonctions pour les pages Décider, Déménager et Comparer |

---

## **👥 Auteurs**

- **Nathaël BENOIT**
- **Constant AUDIBERT**
- **Rafaël BRUNET-LARE**
- **Paul BABIN**

