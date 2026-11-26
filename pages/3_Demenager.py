"""Page dédiée à l'aide au choix d'un département où déménager."""

import streamlit as st

from utils.decider_components import build_specialty_table, render_move_tab
from utils.navbar import inject_navbar_css, render_footer, render_navbar


def render_move_page() -> None:
    st.set_page_config(
        page_title="Où déménager ?",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_navbar_css()
    render_navbar("Où déménager ?")
    st.title("🧭 Où déménager pour éviter les déserts médicaux ?")

    table, _ = build_specialty_table()
    render_move_tab(table)
    render_footer()


if __name__ == "__main__":
    render_move_page()
