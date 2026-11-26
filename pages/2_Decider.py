"""Page dédiée aux déserts médicaux."""

import streamlit as st

from utils.decider_components import (
    build_specialty_table,
    render_desert_cumulation,
    render_desert_overview,
)
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_deserts_page() -> None:
    st.set_page_config(
        page_title="Déserts médicaux",
        page_icon="🏜️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Déserts médicaux")
    st.title("🏜️ Déserts médicaux")

    table, _ = build_specialty_table()
    render_desert_overview(table)
    st.divider()
    render_desert_cumulation(table)
    render_footer()


if __name__ == "__main__":
    render_deserts_page()
