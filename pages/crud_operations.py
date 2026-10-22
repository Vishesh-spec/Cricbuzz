"""CRUD page: manage player records and per-format career stats via forms."""
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from utils.db_connection import execute, run_query, run_transaction, scalar

st.title("🛠️ CRUD Operations")

ROLES = ["Batsman", "Bowler", "All-rounder", "Wicket-keeper"]
BAT_STYLES = ["Right-hand bat", "Left-hand bat"]
BOWL_STYLES = ["None", "Right-arm fast", "Right-arm medium", "Right-arm offbreak",
               "Left-arm orthodox", "Legbreak", "Left-arm fast"]
FORMATS = ["Test", "ODI", "T20I"]

# (column, label, type)
STAT_FIELDS = [
    ("matches", "Matches", int), ("innings", "Innings", int), ("runs", "Runs", int),
    ("highest_score", "Highest score", int), ("batting_avg", "Batting average", float),
    ("strike_rate", "Strike rate", float), ("centuries", "Centuries", int),
    ("fifties", "Fifties", int), ("wickets", "Wickets", int),
    ("bowling_avg", "Bowling average", float), ("economy", "Economy", float),
    ("catches", "Catches", int), ("stumpings", "Stumpings", int),
]


def pick(options: list[str], value: Optional[str]) -> int:
    """Index of ``value`` in ``options`` (0 when missing)."""
    return options.index(value) if value in options else 0


def load_teams() -> pd.DataFrame:
    return run_query("SELECT team_id, team_name FROM teams ORDER BY team_name")


def load_players() -> pd.DataFrame:
    return run_query("SELECT player_id, full_name FROM players ORDER BY full_name")


def player_label(df: pd.DataFrame):
    names = dict(zip(df["player_id"], df["full_name"]))
    return lambda pid: f"{names[pid]} (#{pid})"


# =========================================================================
# PLAYERS
# =========================================================================
def players_crud() -> None:
    teams = load_teams()
    team_ids = teams["team_id"].tolist()
    team_names = dict(zip(teams["team_id"], teams["team_name"]))
    tab_c, tab_r, tab_u, tab_d = st.tabs(["➕ Create", "📖 Read", "✏️ Update", "🗑️ Delete"])

    # ---- Create
    with tab_c, st.form("create_player", clear_on_submit=True):
        name = st.text_input("Full name *")
        team_id = st.selectbox("Team", team_ids, format_func=team_names.get) if team_ids else None
        role = st.selectbox("Playing role", ROLES)
        bat = st.selectbox("Batting style", BAT_STYLES)
        bowl = st.selectbox("Bowling style", BOWL_STYLES)
        if st.form_submit_button("Add player"):
            if not name.strip():
                st.error("Full name is required.")
            else:
                try:
                    new_id = int(scalar("SELECT COALESCE(MAX(player_id), 0) + 1 FROM players"))
                    execute(
                        "INSERT INTO players (player_id, full_name, country, playing_role, "
                        "batting_style, bowling_style, team_id) "
                        "VALUES (:id, :name, :country, :role, :bat, :bowl, :team)",
                        {"id": new_id, "name": name.strip(),
                         "country": team_names.get(team_id), "role": role, "bat": bat,
                         "bowl": None if bowl == "None" else bowl, "team": team_id},
                    )
                    st.success(f"Added {name.strip()} with player_id {new_id}.")
                except SQLAlchemyError as exc:
                    st.error(f"Could not add player: {exc}")

    # ---- Read
    with tab_r:
        c1, c2 = st.columns([2, 1])
        search = c1.text_input("Search by name")
        role_filter = c2.selectbox("Role", ["All"] + ROLES)
        df = run_query(
            "SELECT p.player_id, p.full_name, p.country, p.playing_role, p.batting_style, "
            "p.bowling_style, t.team_name FROM players p LEFT JOIN teams t ON t.team_id = p.team_id "
            "WHERE LOWER(p.full_name) LIKE :q AND (:role = 'All' OR p.playing_role = :role) "
            "ORDER BY p.full_name",
            {"q": f"%{search.lower()}%", "role": role_filter},
        )
        st.caption(f"{len(df)} player(s)")
        st.dataframe(df, width="stretch", hide_index=True)

    # ---- Update
    with tab_u:
        players = load_players()
        if players.empty:
            st.info("No players yet.")
        else:
            pid = st.selectbox("Player to edit", players["player_id"], format_func=player_label(players))
            row = run_query("SELECT * FROM players WHERE player_id = :id", {"id": int(pid)}).iloc[0]
            with st.form(f"update_player_{pid}"):
                name = st.text_input("Full name *", row["full_name"])
                cur_team = int(row["team_id"]) if pd.notna(row["team_id"]) else None
                team_id = st.selectbox("Team", team_ids, index=pick(team_ids, cur_team),
                                       format_func=team_names.get)
                role = st.selectbox("Playing role", ROLES, index=pick(ROLES, row["playing_role"]))
                bat = st.selectbox("Batting style", BAT_STYLES, index=pick(BAT_STYLES, row["batting_style"]))
                bowl = st.selectbox("Bowling style", BOWL_STYLES,
                                    index=pick(BOWL_STYLES, row["bowling_style"] or "None"))
                if st.form_submit_button("Save changes"):
                    if not name.strip():
                        st.error("Full name is required.")
                    else:
                        try:
                            execute(
                                "UPDATE players SET full_name=:name, country=:country, playing_role=:role, "
                                "batting_style=:bat, bowling_style=:bowl, team_id=:team WHERE player_id=:id",
                                {"name": name.strip(), "country": team_names.get(team_id), "role": role,
                                 "bat": bat, "bowl": None if bowl == "None" else bowl,
                                 "team": team_id, "id": int(pid)},
                            )
                            st.success("Player updated.")
                        except SQLAlchemyError as exc:
                            st.error(f"Could not update player: {exc}")

    # ---- Delete
    with tab_d:
        players = load_players()
        if players.empty:
            st.info("No players yet.")
        else:
            pid = st.selectbox("Player to delete", players["player_id"],
                               format_func=player_label(players), key="del_player")
            cascade = st.checkbox("Also delete this player's scorecards and career stats")
            confirm = st.checkbox("I understand this cannot be undone")
            if st.button("Delete player", type="primary", disabled=not confirm):
                params = {"id": int(pid)}
                try:
                    stmts = []
                    if cascade:
                        stmts += [(f"DELETE FROM {t} WHERE player_id = :id", params) for t in
                                  ("batting_scorecard", "bowling_scorecard", "fielding_stats",
                                   "player_career_stats")]
                    stmts.append(("DELETE FROM players WHERE player_id = :id", params))
                    run_transaction(stmts)
                    st.success("Player deleted.")
                    st.rerun()
                except IntegrityError:
                    st.error("This player is referenced by scorecards or career stats. "
                             "Tick the cascade option to delete those rows too.")
                except SQLAlchemyError as exc:
                    st.error(f"Could not delete player: {exc}")


# =========================================================================
# CAREER STATS
# =========================================================================
def stats_crud() -> None:
    tab_r, tab_w, tab_d = st.tabs(["📖 Read", "✏️ Add / Update", "🗑️ Delete"])

    with tab_r:
        fmt = st.selectbox("Format", ["All"] + FORMATS, key="stats_read_fmt")
        df = run_query(
            "SELECT p.full_name, pcs.* FROM player_career_stats pcs "
            "JOIN players p ON p.player_id = pcs.player_id "
            "WHERE (:fmt = 'All' OR pcs.match_format = :fmt) ORDER BY pcs.runs DESC",
            {"fmt": fmt},
        )
        st.dataframe(df, width="stretch", hide_index=True)

    players = load_players()
    if players.empty:
        with tab_w:
            st.info("Add a player first.")
        return
    fmt_label = player_label(players)

    with tab_w:
        c1, c2 = st.columns(2)
        pid = int(c1.selectbox("Player", players["player_id"], format_func=fmt_label, key="stats_pid"))
        fmt = c2.selectbox("Format", FORMATS, key="stats_fmt")
        existing = run_query(
            "SELECT * FROM player_career_stats WHERE player_id=:p AND match_format=:f",
            {"p": pid, "f": fmt},
        )
        current = existing.iloc[0].to_dict() if not existing.empty else {}
        st.caption("Editing an existing record" if current else "No record yet - this will create one")

        with st.form(f"stats_form_{pid}_{fmt}"):
            values = {}
            cols = st.columns(3)
            for i, (col, label, typ) in enumerate(STAT_FIELDS):
                default = current.get(col)
                default = 0 if default is None or pd.isna(default) else default
                with cols[i % 3]:
                    if typ is int:
                        values[col] = st.number_input(label, min_value=0, value=int(default), step=1)
                    else:
                        values[col] = st.number_input(label, min_value=0.0, value=float(default), step=0.1)
            if st.form_submit_button("Save stats"):
                values["balls_faced"] = (
                    int(values["runs"] * 100 / values["strike_rate"]) if values["strike_rate"] else 0
                )
                for nullable in ("bowling_avg", "economy"):  # 0 means "not applicable"
                    if not values[nullable]:
                        values[nullable] = None
                cols_sql = ["player_id", "match_format", *values]
                params = {"player_id": pid, "match_format": fmt, **values}
                try:
                    run_transaction([
                        ("DELETE FROM player_career_stats WHERE player_id=:player_id AND match_format=:match_format",
                         params),
                        (f"INSERT INTO player_career_stats ({', '.join(cols_sql)}) "
                         f"VALUES ({', '.join(':' + c for c in cols_sql)})", params),
                    ])
                    st.success("Career stats saved.")
                except SQLAlchemyError as exc:
                    st.error(f"Could not save stats: {exc}")

    with tab_d:
        c1, c2 = st.columns(2)
        pid = int(c1.selectbox("Player", players["player_id"], format_func=fmt_label, key="stats_del_pid"))
        fmt = c2.selectbox("Format", FORMATS, key="stats_del_fmt")
        confirm = st.checkbox("I understand this cannot be undone", key="stats_del_confirm")
        if st.button("Delete stats row", type="primary", disabled=not confirm):
            try:
                n = execute("DELETE FROM player_career_stats WHERE player_id=:p AND match_format=:f",
                            {"p": pid, "f": fmt})
                st.success("Deleted.") if n else st.warning("No matching row found.")
            except SQLAlchemyError as exc:
                st.error(f"Could not delete: {exc}")


entity = st.radio("Manage", ["Players", "Career stats"], horizontal=True)
try:
    players_crud() if entity == "Players" else stats_crud()
except SQLAlchemyError as exc:
    st.error(f"Database error: {exc}")
