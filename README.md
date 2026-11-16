# LifeMap : Santé Où Habiter

Application Streamlit répondant à la question :

> **Où faut-il habiter par rapport au médical et à la santé ?**

Elle compare l'offre de soins des départements français à partir des équipements
recensés par l'Insee. L'objectif est de repérer les territoires les mieux dotés
et de comprendre pourquoi un classement brut ne suffit pas à conclure : un
département très peuplé compte mécaniquement davantage de lieux de soins.

## Fonctionnalités

- synthèse nationale et classement des départements ;
- exploration par région, catégorie de professionnel ou d'établissement ;
- comparaison de deux départements ;
- graphiques interactifs et tableau exportable depuis Streamlit ;
- formulaire de filtres (`st.form`) ;
- mémorisation des filtres et de la dernière comparaison (`st.session_state`) ;
- cache de lecture et d'agrégation de la BPE (`st.cache_data`).

## Données

Les fichiers à placer dans `data/` sont :

- `BPE25.parquet` : Insee, Base permanente des équipements 2025, un lieu
  d'exercice ou équipement par ligne ;
- `donnees_departements.csv` : référentiel départemental avec les codes
  `REG`/`DEP`, le nom `Département` et la population municipale ;
- `departements-avec-outre-mer.geojson` : référentiel des contours et des noms
  de départements ;
- `regions-avec-outre-mer.geojson` : référentiel régional disponible pour les
  extensions cartographiques.

La jointure principale croise `REG` et `DEP` de la BPE avec les mêmes colonnes
du fichier `donnees_departements.csv`. `REG` permet de rattacher la région et
`DEP` identifie le département sans dupliquer les lignes (un même `REG`
correspond à plusieurs départements). Le nom affiché est celui de la colonne
`Département` du CSV. Les codes `01` à `09`, `2A`, `2B` et `971` à `976` sont
normalisés en texte.

La version fournie analyse les volumes recensés. Pour publier une densité pour
100 000 habitants, ajouter une source officielle Insee des populations 2023
dans `data/population_departements.csv`, avec les colonnes
`code_departement,population`. La fonction `add_density` est prête à réaliser
ce croisement sans perdre les zéros initiaux.

### Limites d'interprétation

La BPE compte des lieux d'exercice, pas nécessairement des personnes uniques.
Un professionnel présent à deux adresses peut être compté deux fois et les
médecins salariés des hôpitaux ne sont pas représentés. Un volume élevé ne
signifie donc pas automatiquement un meilleur accès aux soins.

## Installation et lancement

```bash
python -m venv .venv
source .venv/bin/activate              # Windows : .venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Le parquet est volumineux : le premier chargement peut prendre quelques
secondes. Les appels suivants bénéficient du cache Streamlit.

## Organisation

- `app.py` : accueil, indicateurs et première conclusion ;
- `pages/1_Explorer.py` : filtres et exploration de l'offre ;
- `pages/2_Decider.py` : comparaison de deux départements ;
- `utils/data_loader.py` : chemins relatifs, lecture, normalisation et
  agrégation des données ;
- `data/` : sources locales.

## Participants

À compléter avec les noms du groupe avant le dépôt.
