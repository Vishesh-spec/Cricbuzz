"""SQL Analytics page: the 25 practice queries + a safe custom-query box."""
import re

import streamlit as st

from utils.db_connection import run_query
from utils.sql_queries import QUERIES, get_query_parts

st.title("🔍 SQL Analytics")
st.caption("25 practice queries on the player and match database, plus a custom query runner.")

# ---------------------------------------------------------------- 25 queries
levels = ["All"] + sorted({q["level"] for q in QUERIES}, key=["Beginner", "Intermediate", "Advanced"].index)
level = st.radio("Level", levels, horizontal=True)
visible = [q for q in QUERIES if level == "All" or q["level"] == level]

query = st.selectbox(
    "Choose a question",
    visible,
    format_func=lambda q: f"Q{q['number']}. {q['title']}  ·  {q['level']}",
)

st.markdown(f"**Question {query['number']}:** {query['question']}")

for label, sql in get_query_parts(query):
    if len(get_query_parts(query)) > 1:
        st.markdown(f"##### {label}")
    with st.expander("Show SQL"):
        st.code(sql, language="sql")
    try:
        df = run_query(sql)
        st.caption(f"{len(df):,} row(s)")
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"q{query['number']}_{label.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"dl_{query['number']}_{label}",
        )
    except Exception as exc:
        st.error(f"Query failed: {exc}")

# ---------------------------------------------------------------- custom SQL
st.divider()
st.subheader("Custom query")
st.caption("Read-only: only a single SELECT / WITH statement is allowed.")

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|grant|revoke)\b",
    re.IGNORECASE,
)


def is_safe(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()
    return (
        bool(re.match(r"^(select|with)\b", stripped, re.IGNORECASE))
        and ";" not in stripped
        and not FORBIDDEN.search(stripped)
    )


custom = st.text_area("SQL", "SELECT * FROM players LIMIT 10", height=140)
if st.button("▶️ Run query"):
    if not is_safe(custom):
        st.error("Only a single read-only SELECT / WITH statement is allowed.")
    else:
        try:
            result = run_query(custom.strip().rstrip(";"))
            st.caption(f"{len(result):,} row(s)")
            st.dataframe(result, width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"Query failed: {exc}")

with st.expander("Tables in the database"):
    st.markdown(
        "`teams`, `venues`, `players`, `series`, `matches`, `batting_scorecard`, "
        "`bowling_scorecard`, `fielding_stats`, `player_career_stats` - see `schema.sql`."
    )
