"""Styles et navigation communs à toutes les pages de LifeMap : Santé Où Habiter."""

import streamlit as st


def inject_navbar_css() -> None:
    """Injecte le thème visuel partagé de l'application."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }
        section[data-testid="stSidebar"],
        button[data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        .navbar-container {
            border-bottom: 1px solid #e2e8f0;
            margin: -1rem -1rem 1.5rem -1rem;
            padding: 0.6rem 2rem;
            background: #ffffff;
        }
        .navbar-brand-text {
            font-size: 1.35rem;
            font-weight: 700;
            color: #1e293b;
            letter-spacing: -0.5px;
            line-height: 2.4rem;
        }
        .navbar-brand-text span { color: #2563eb; }
        [data-testid="stPageLink"] a {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: #64748b !important;
            padding: 0.45rem 0.9rem !important;
            border-radius: 6px !important;
            text-decoration: none !important;
            transition: all 0.2s ease !important;
            border: none !important;
            background: transparent !important;
        }
        [data-testid="stPageLink"] a:hover,
        [data-testid="stPageLink"] a[aria-current="page"] {
            color: #2563eb !important;
            background: #eff6ff !important;
            font-weight: 600 !important;
        }
        h1, h2, h3 {
            font-family: 'Inter', sans-serif !important;
            color: #1e293b !important;
            letter-spacing: -0.5px;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.2rem;
            transition: all 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            border-color: #2563eb;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
            transform: translateY(-2px);
        }
        [data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem !important;
            letter-spacing: 0.5px;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #1e293b !important;
            font-weight: 700;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: transparent;
            border-bottom: 1px solid #e2e8f0;
        }
        .stTabs [data-baseweb="tab"] {
            color: #64748b;
            font-weight: 500;
            padding: 0.8rem 1.2rem;
            border-bottom: 2px solid transparent;
        }
        .stTabs [aria-selected="true"] {
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
            font-weight: 600;
        }
        .stButton > button, .stFormSubmitButton > button {
            background: #2563eb !important;
            color: #ffffff !important;
            font-weight: 600;
            border: none !important;
            border-radius: 8px;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: #1d4ed8 !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
        }
        hr { border: none; height: 1px; background: #e2e8f0; }
        .site-footer {
            text-align: center;
            padding: 2rem 0;
            color: #94a3b8;
            font-size: 0.85rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 2rem;
        }
        @media (max-width: 768px) {
            .navbar-container { padding: 0.6rem 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_navbar(active_page: str = "Accueil") -> None:
    """Affiche la barre de navigation adaptée aux pages actuelles.

    Args:
        active_page: Nom de la page actuellement affichée.
    """
    columns = st.columns([2.4, 1, 1, 1, 1])
    with columns[0]:
        st.markdown(
            '<div class="navbar-brand-text">🩺 <span>LifeMap</span> : Santé Où Habiter</div>',
            unsafe_allow_html=True,
        )
    pages = [
        ("Accueil", "app.py"),
        ("Déserts médicaux", "pages/2_Decider.py"),
        ("Où déménager ?", "pages/3_Demenager.py"),
        ("Comparer", "pages/4_Comparer.py"),
    ]
    for column, (label, path) in zip(columns[1:], pages):
        with column:
            st.page_link(path, label=label)
    st.markdown(
        '<div class="navbar-container" style="margin-top:-0.5rem; padding:0;"></div>',
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Affiche le pied de page avec la source principale des données."""
    st.markdown(
        """
        <div class="site-footer">
            Source : Insee, Base permanente des équipements 2025 ·
            Référentiel géographique des départements
        </div>
        """,
        unsafe_allow_html=True,
    )
