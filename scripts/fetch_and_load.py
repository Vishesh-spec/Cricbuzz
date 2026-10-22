"""Fetch REAL data from the Cricbuzz API and load it into the SQL database.

    python scripts/fetch_and_load.py --teams --players --matches

Free RapidAPI plans have a small request quota, so this script is deliberately
incremental: choose what to load with flags, and re-running is safe (rows that
already exist are skipped).  Use a SEPARATE database (set DB_URL) if you also
use the synthetic seed data, because the IDs would clash.

Pipeline:  REST call -> JSON -> flatten/clean in Python -> INSERT into SQL
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import api_client as api  # noqa: E402
from utils.db_connection import execute, init_db, run_query, scalar  # noqa: E402

PAUSE = 1.0  # seconds between calls, to be polite to the API


def insert_if_missing(table: str, pk: str, row: dict[str, Any]) -> bool:
    """Insert ``row`` unless its primary key already exists. Returns True if inserted."""
    if scalar(f"SELECT 1 FROM {table} WHERE {pk} = :pk", {"pk": row[pk]}):
        return False
    cols = list(row)
    execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})", row
    )
    return True


# ------------------------------------------------------------------ teams
def load_teams() -> list[int]:
    data = api.get_international_teams()
    ids = []
    for item in data.get("list", []):
        if "teamId" not in item:  # section headers like "Test teams"
            continue
        row = {
            "team_id": int(item["teamId"]),
            "team_name": item["teamName"],
            "short_name": item.get("teamSName"),
            "country": item["teamName"],
        }
        insert_if_missing("teams", "team_id", row)
        ids.append(row["team_id"])
    print(f"Teams loaded: {len(ids)}")
    return ids


# ---------------------------------------------------------------- players
def load_players(team_ids: list[int]) -> None:
    count = 0
    for team_id in team_ids:
        time.sleep(PAUSE)
        try:
            data = api.get_team_players(team_id)
        except api.CricbuzzAPIError as exc:
            print(f"  skip team {team_id}: {exc}")
            continue
        role: Optional[str] = None
        country = scalar("SELECT team_name FROM teams WHERE team_id = :t", {"t": team_id})
        for item in data.get("player", []):
            if "id" not in item:  # section header e.g. "BATSMEN"
                role = item.get("name", "").title().replace("Wicket Keepers", "Wicket-keeper")
                role = {"Batsmen": "Batsman", "Bowlers": "Bowler",
                        "All Rounders": "All-rounder"}.get(role, role)
                continue
            if insert_if_missing("players", "player_id", {
                "player_id": int(item["id"]), "full_name": item["name"], "country": country,
                "playing_role": role, "batting_style": item.get("battingStyle"),
                "bowling_style": item.get("bowlingStyle"), "team_id": team_id,
            }):
                count += 1
    print(f"Players inserted: {count}")


# ---------------------------------------------------------------- matches
STATUS_RE = re.compile(r"^(?P<team>.+?) won by (?P<margin>\d+) (?P<kind>runs?|wkts?|wickets?)", re.I)


def parse_status(status: str) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """'India won by 5 wkts' -> ('India', 5, 'wickets')."""
    m = STATUS_RE.match(status or "")
    if not m:
        return None, None, None
    kind = "runs" if m["kind"].lower().startswith("run") else "wickets"
    return m["team"].strip(), int(m["margin"]), kind


def load_recent_matches() -> None:
    data = api.get_recent_matches()
    count = 0
    for block in data.get("typeMatches", []):
        for series_block in block.get("seriesMatches", []):
            wrapper = series_block.get("seriesAdWrapper")
            if not wrapper:
                continue
            for match in wrapper.get("matches", []):
                info = match.get("matchInfo", {})
                fmt = info.get("matchFormat")
                if fmt not in ("Test", "ODI", "T20I"):
                    continue  # schema only models international formats
                t1, t2 = info.get("team1", {}), info.get("team2", {})
                venue = info.get("venueInfo", {})
                start = api.ms_to_datetime(info.get("startDate"))
                if not (t1.get("teamId") and t2.get("teamId") and start and venue.get("id")):
                    continue
                for team in (t1, t2):
                    insert_if_missing("teams", "team_id", {
                        "team_id": int(team["teamId"]), "team_name": team["teamName"],
                        "short_name": team.get("teamSName"), "country": team["teamName"]})
                insert_if_missing("venues", "venue_id", {
                    "venue_id": int(venue["id"]), "venue_name": venue.get("ground"),
                    "city": venue.get("city"), "country": venue.get("country"), "capacity": None})
                if info.get("seriesId"):
                    insert_if_missing("series", "series_id", {
                        "series_id": int(info["seriesId"]), "series_name": info.get("seriesName"),
                        "host_country": venue.get("country"), "match_type": fmt,
                        "start_date": start.date().isoformat(), "end_date": None,
                        "total_matches": None})
                winner_name, margin, kind = parse_status(info.get("status", ""))
                winner_id = next((int(t["teamId"]) for t in (t1, t2) if t["teamName"] == winner_name), None)
                if insert_if_missing("matches", "match_id", {
                    "match_id": int(info["matchId"]),
                    "series_id": int(info["seriesId"]) if info.get("seriesId") else None,
                    "description": f"{t1['teamName']} vs {t2['teamName']}, {info.get('matchDesc')}",
                    "match_format": fmt, "team1_id": int(t1["teamId"]), "team2_id": int(t2["teamId"]),
                    "venue_id": int(venue["id"]), "match_date": start.date().isoformat(),
                    "toss_winner_id": None, "toss_decision": None, "winner_id": winner_id,
                    "victory_margin": margin, "victory_type": kind,
                    "status": "Complete" if winner_id else info.get("state", "Complete"),
                }):
                    count += 1
    print(f"Matches inserted: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--teams", action="store_true", help="load international teams")
    parser.add_argument("--players", action="store_true", help="load squads (needs teams)")
    parser.add_argument("--matches", action="store_true", help="load recent matches")
    args = parser.parse_args()
    if not (args.teams or args.players or args.matches):
        parser.print_help()
        return

    init_db()  # creates tables if they do not exist
    try:
        team_ids = load_teams() if args.teams else []
        if args.players:
            team_ids = team_ids or run_query("SELECT team_id FROM teams")["team_id"].astype(int).tolist()
            load_players(team_ids)
        if args.matches:
            load_recent_matches()
    except api.CricbuzzAPIError as exc:
        sys.exit(f"API error: {exc}")


if __name__ == "__main__":
    main()
