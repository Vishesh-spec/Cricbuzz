"""Home page: project overview and navigation help."""
import streamlit as st

st.title("🏏 Cricbuzz LiveStats")
st.subheader("Real-time cricket insights & SQL-based analytics")

st.markdown(
    """
A multi-page analytics dashboard that combines **live data from the Cricbuzz
Cricket API** with a **SQL database** for historical analysis.

| Page | What you can do |
|---|---|
| ⚡ **Live Matches** | Live / recent / upcoming matches, full scorecards (batting + bowling) |
| 📊 **Top Player Stats** | Top batting & bowling charts from the API, plus career leaderboards from the database |
| 🔍 **SQL Analytics** | Run 25 practice queries (beginner → advanced) and your own `SELECT` statements |
| 🛠️ **CRUD Operations** | Create, read, update and delete player records and career stats |
"""
)

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        """
**Tech stack**
- Python, Streamlit, pandas
- `requests` → Cricbuzz Cricket API (RapidAPI, JSON)
- SQLAlchemy → SQLite / MySQL / PostgreSQL
"""
    )
with col2:
    st.markdown(
        """
**Quick start**
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`, add `RAPIDAPI_KEY`
3. `python scripts/seed_sample_data.py` *(demo data)*
4. `streamlit run app.py`
"""
    )

st.info(
    "The bundled sample database is **synthetic** (fictional players and results) so the "
    "SQL and CRUD pages work offline. The Live Matches and Top Stats (API) tabs use real "
    "Cricbuzz data and need a valid `RAPIDAPI_KEY`.",
    icon="ℹ️",
)
