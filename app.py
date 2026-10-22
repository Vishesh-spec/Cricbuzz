"""Cricbuzz LiveStats - Streamlit entry point.

Run with:  streamlit run app.py
"""
import streamlit as st

from utils.db_connection import database_has_data

st.set_page_config(page_title="Cricbuzz LiveStats", page_icon="🏏", layout="wide")

PAGES = [
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/live_matches.py", title="Live Matches", icon="⚡"),
    st.Page("pages/top_stats.py", title="Top Player Stats", icon="📊"),
    st.Page("pages/sql_queries.py", title="SQL Analytics", icon="🔍"),
    st.Page("pages/crud_operations.py", title="CRUD Operations", icon="🛠️"),
]

with st.sidebar:
    st.caption("🏏 Cricbuzz LiveStats")
    if database_has_data():
        st.success("Database connected", icon="🗄️")
    else:
        st.warning(
            "Database is empty. Run `python scripts/seed_sample_data.py` "
            "(demo data) or `python scripts/fetch_and_load.py` (live API data).",
            icon="⚠️",
        )

st.navigation(PAGES).run()
