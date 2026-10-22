"""Top Player Stats page: API leaderboards + database career leaderboards."""
import pandas as pd
import streamlit as st

from utils import api_client as api
from utils.db_connection import run_query

st.title("📊 Top Player Stats")
tab_api, tab_db = st.tabs(["🌐 Live from Cricbuzz API", "🗄️ From database"])


# ------------------------------------------------------------------ API tab
@st.cache_data(ttl=3600, show_spinner="Fetching stats...")
def load_top_stats(stats_type: str) -> pd.DataFrame:
    return api.parse_top_stats(api.get_top_stats(stats_type))


def chart_frame(df: pd.DataFrame) -> pd.DataFrame | None:
    """Pick a label column and the last numeric column for a bar chart."""
    numeric = df.apply(pd.to_numeric, errors="coerce")
    numeric_cols = [c for c in df.columns if numeric[c].notna().all() and c not in ("Rank", "#")]
    label_cols = [c for c in df.columns if c not in numeric_cols]
    if not numeric_cols or not label_cols:
        return None
    label = next((c for c in label_cols if "player" in c.lower() or "name" in c.lower()), label_cols[0])
    metric = numeric_cols[-1]
    out = pd.DataFrame({label: df[label], metric: numeric[metric]}).set_index(label)
    return out


with tab_api:
    group = st.radio("Category", ["Batting", "Bowling"], horizontal=True)
    options = api.BATTING_STATS if group == "Batting" else api.BOWLING_STATS
    label = st.selectbox("Statistic", list(options))
    try:
        df = load_top_stats(options[label])
        if df.empty:
            st.info("The API returned no rows for this statistic.")
        else:
            st.dataframe(df, width="stretch", hide_index=True)
            chart = chart_frame(df.head(10))
            if chart is not None:
                st.bar_chart(chart)
    except api.CricbuzzAPIError as exc:
        st.error(str(exc), icon="🚫")

# ------------------------------------------------------------------ DB tab
# column / sort direction / extra filter are whitelisted here (never user text)
DB_STATS = {
    "Most runs": ("runs", "DESC", ""),
    "Highest batting average": ("batting_avg", "DESC", "AND pcs.innings >= 20"),
    "Best strike rate": ("strike_rate", "DESC", "AND pcs.innings >= 20"),
    "Most centuries": ("centuries", "DESC", ""),
    "Highest score": ("highest_score", "DESC", ""),
    "Most wickets": ("wickets", "DESC", ""),
    "Best economy (min 20 wickets)": ("economy", "ASC", "AND pcs.wickets >= 20"),
}

with tab_db:
    fmt = st.selectbox("Format", ["ODI", "Test", "T20I"])
    stat_label = st.selectbox("Statistic ", list(DB_STATS))
    column, direction, extra = DB_STATS[stat_label]
    sql = f"""
        SELECT p.full_name AS player, p.country, pcs.{column} AS value
        FROM player_career_stats pcs
        JOIN players p ON p.player_id = pcs.player_id
        WHERE pcs.match_format = :fmt AND pcs.{column} IS NOT NULL {extra}
        ORDER BY pcs.{column} {direction}
        LIMIT 10"""
    try:
        data = run_query(sql, {"fmt": fmt})
        if data.empty:
            st.info("No data. Seed the database first (see Home page).")
        else:
            st.dataframe(data.rename(columns={"value": column}), width="stretch", hide_index=True)
            st.bar_chart(data.set_index("player")["value"])
    except Exception as exc:  # DB errors shouldn't crash the page
        st.error(f"Database error: {exc}")
