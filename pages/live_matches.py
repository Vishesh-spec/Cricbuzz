"""Live Matches page: match list + detailed scorecard from the Cricbuzz API."""
import pandas as pd
import streamlit as st

from utils import api_client as api

st.title("⚡ Live Matches")
st.caption("Data from the Cricbuzz Cricket API. Results are cached for 60 seconds to save API quota.")

LOADERS = {
    "Live": api.get_live_matches,
    "Recent": api.get_recent_matches,
    "Upcoming": api.get_upcoming_matches,
}


@st.cache_data(ttl=60, show_spinner="Fetching matches from Cricbuzz...")
def load_matches(kind: str) -> list[dict]:
    return api.flatten_matches(LOADERS[kind]())


@st.cache_data(ttl=60, show_spinner="Fetching scorecard...")
def load_scorecard(match_id: int) -> list[dict]:
    return api.parse_scorecard(api.get_scorecard(match_id))


col_kind, col_refresh = st.columns([4, 1])
kind = col_kind.radio("Match type", list(LOADERS), horizontal=True, label_visibility="collapsed")
if col_refresh.button("🔄 Refresh", width="stretch"):
    st.cache_data.clear()
    st.rerun()

try:
    matches = load_matches(kind)
except api.CricbuzzAPIError as exc:
    st.error(str(exc), icon="🚫")
    st.stop()

if not matches:
    st.info(f"No {kind.lower()} matches right now.")
    st.stop()

summary = pd.DataFrame(matches).drop(columns=["raw"])
st.dataframe(
    summary[["series", "match", "format", "team1", "team1_score", "team2", "team2_score", "status"]],
    width="stretch",
    hide_index=True,
)

st.divider()
st.subheader("Scorecard")
labels = {
    m["match_id"]: f"{m['team1']} vs {m['team2']} - {m['match']} ({m['series']})" for m in matches
}
match_id = st.selectbox("Choose a match", list(labels), format_func=labels.get)
selected = next(m for m in matches if m["match_id"] == match_id)

c1, c2, c3 = st.columns(3)
c1.metric("Status", selected["state"] or "-")
c2.metric("Venue", selected["venue"] or "-")
c3.metric("Start", selected["start"] or "-")
st.write(f"**{selected['status']}**")

if kind == "Upcoming":
    st.info("Scorecards are available once the match starts.")
    st.stop()

try:
    innings = load_scorecard(int(match_id))
except api.CricbuzzAPIError as exc:
    st.error(str(exc), icon="🚫")
    st.stop()

if not innings:
    st.info("No scorecard available yet for this match.")
for inn in innings:
    with st.expander(inn["title"], expanded=True):
        if not inn["batting_df"].empty:
            st.markdown("**Batting**")
            st.dataframe(inn["batting_df"], width="stretch", hide_index=True)
        if not inn["bowling_df"].empty:
            st.markdown("**Bowling**")
            st.dataframe(inn["bowling_df"], width="stretch", hide_index=True)
