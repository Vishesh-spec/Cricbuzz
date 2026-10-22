"""Thin client for the Cricbuzz Cricket API hosted on RapidAPI.

Every request needs two headers:
    x-rapidapi-key   -> your personal key (read from the RAPIDAPI_KEY env var)
    x-rapidapi-host  -> cricbuzz-cricket.p.rapidapi.com

NOTE: endpoint paths and JSON field names below follow the RapidAPI docs at the
time of writing. If a call returns 404 or an unexpected shape, open the API's
"Playground" tab on RapidAPI, compare, and adjust the path/parser here.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = "cricbuzz-cricket.p.rapidapi.com"
BASE_URL = f"https://{HOST}"

BATTING_STATS = {
    "Most runs": "mostRuns",
    "Highest score": "highestScore",
    "Highest average": "highestAvg",
    "Highest strike rate": "highestSr",
    "Most hundreds": "mostHundreds",
    "Most fifties": "mostFifties",
    "Most fours": "mostFours",
    "Most sixes": "mostSixes",
}
BOWLING_STATS = {
    "Most wickets": "mostWickets",
    "Best bowling average": "lowestAvg",
    "Best bowling in an innings": "bestBowlingInnings",
    "Most five-wicket hauls": "mostFiveWickets",
    "Best economy": "lowestEcon",
    "Best strike rate": "lowestSr",
}


class CricbuzzAPIError(RuntimeError):
    """Raised for any problem talking to the Cricbuzz API."""


# --------------------------------------------------------------------------
# Low-level request helper
# --------------------------------------------------------------------------
def _headers() -> dict[str, str]:
    key = os.getenv("RAPIDAPI_KEY")
    if not key:
        raise CricbuzzAPIError(
            "RAPIDAPI_KEY is not set. Copy .env.example to .env and paste your "
            "RapidAPI key into it, then restart the app."
        )
    return {"x-rapidapi-key": key, "x-rapidapi-host": HOST}


def get(endpoint: str, params: Optional[dict[str, Any]] = None, timeout: int = 15) -> dict:
    """GET ``endpoint`` and return the decoded JSON, or raise CricbuzzAPIError."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=_headers(), params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        code = exc.response.status_code
        hints = {
            401: "Invalid API key.",
            403: "Your key is not subscribed to the Cricbuzz Cricket API.",
            404: "Endpoint or ID not found.",
            429: "Rate limit / monthly quota reached. Wait or upgrade your plan.",
        }
        raise CricbuzzAPIError(f"HTTP {code} for {endpoint}. {hints.get(code, '')}") from exc
    except requests.Timeout as exc:
        raise CricbuzzAPIError(f"Request to {endpoint} timed out.") from exc
    except requests.RequestException as exc:
        raise CricbuzzAPIError(f"Network error calling {endpoint}: {exc}") from exc
    except ValueError as exc:
        raise CricbuzzAPIError(f"{endpoint} did not return valid JSON.") from exc


# --------------------------------------------------------------------------
# Endpoint wrappers
# --------------------------------------------------------------------------
def get_live_matches() -> dict:
    return get("/matches/v1/live")


def get_recent_matches() -> dict:
    return get("/matches/v1/recent")


def get_upcoming_matches() -> dict:
    return get("/matches/v1/upcoming")


def get_match_info(match_id: int) -> dict:
    return get(f"/mcenter/v1/{match_id}")


def get_scorecard(match_id: int) -> dict:
    return get(f"/mcenter/v1/{match_id}/scard")


def get_top_stats(stats_type: str, match_type: Optional[int] = None) -> dict:
    params: dict[str, Any] = {"statsType": stats_type}
    if match_type is not None:
        params["matchType"] = match_type
    return get("/stats/v1/topstats/0", params)


def search_player(name: str) -> dict:
    return get("/stats/v1/player/search", {"plrN": name})


def get_player_info(player_id: int) -> dict:
    return get(f"/stats/v1/player/{player_id}")


def get_player_batting(player_id: int) -> dict:
    return get(f"/stats/v1/player/{player_id}/batting")


def get_player_bowling(player_id: int) -> dict:
    return get(f"/stats/v1/player/{player_id}/bowling")


def get_international_teams() -> dict:
    return get("/teams/v1/international")


def get_team_players(team_id: int) -> dict:
    return get(f"/teams/v1/{team_id}/players")


def get_international_series() -> dict:
    return get("/series/v1/international")


def get_venue(venue_id: int) -> dict:
    return get(f"/venues/v1/{venue_id}")


# --------------------------------------------------------------------------
# Parsers: turn nested API JSON into flat rows / DataFrames
# --------------------------------------------------------------------------
def ms_to_datetime(value: Any) -> Optional[datetime]:
    """Cricbuzz sends epoch milliseconds as strings."""
    try:
        return datetime.fromtimestamp(int(value) / 1000)
    except (TypeError, ValueError, OSError):
        return None


def _format_team_score(team_score: Optional[dict]) -> str:
    """{'inngs1': {'runs': 210, 'wickets': 3, 'overs': 35.2}} -> '210/3 (35.2 ov)'."""
    if not team_score:
        return "-"
    parts = []
    for key in sorted(k for k in team_score if k.startswith("inngs")):
        inn = team_score[key]
        wickets = inn.get("wickets", 10)
        overs = f" ({inn['overs']} ov)" if "overs" in inn else ""
        parts.append(f"{inn.get('runs', 0)}/{wickets}{overs}")
    return " & ".join(parts) if parts else "-"


def flatten_matches(payload: dict) -> list[dict]:
    """Flatten the typeMatches -> seriesMatches -> matches tree into rows."""
    rows: list[dict] = []
    for type_block in payload.get("typeMatches", []):
        for series_block in type_block.get("seriesMatches", []):
            wrapper = series_block.get("seriesAdWrapper")
            if not wrapper:  # ad slots have no wrapper
                continue
            for match in wrapper.get("matches", []):
                info = match.get("matchInfo", {})
                score = match.get("matchScore", {})
                venue = info.get("venueInfo", {})
                start = ms_to_datetime(info.get("startDate"))
                rows.append(
                    {
                        "match_id": info.get("matchId"),
                        "series": info.get("seriesName"),
                        "match": info.get("matchDesc"),
                        "format": info.get("matchFormat"),
                        "state": info.get("state"),
                        "status": info.get("status"),
                        "team1": info.get("team1", {}).get("teamName"),
                        "team1_score": _format_team_score(score.get("team1Score")),
                        "team2": info.get("team2", {}).get("teamName"),
                        "team2_score": _format_team_score(score.get("team2Score")),
                        "venue": ", ".join(
                            x for x in (venue.get("ground"), venue.get("city")) if x
                        ),
                        "start": start.strftime("%Y-%m-%d %H:%M") if start else None,
                        "raw": match,
                    }
                )
    return rows


def parse_scorecard(payload: dict) -> list[dict]:
    """Return one dict per innings with title, batting_df and bowling_df."""
    innings_list = []
    for inn in payload.get("scoreCard", []):
        bat = inn.get("batTeamDetails", {})
        bowl = inn.get("bowlTeamDetails", {})
        score = inn.get("scoreDetails", {})

        batting = [
            {
                "Batter": b.get("batName"),
                "Dismissal": b.get("outDesc") or "not out",
                "Runs": b.get("runs"),
                "Balls": b.get("balls"),
                "4s": b.get("fours"),
                "6s": b.get("sixes"),
                "SR": b.get("strikeRate"),
            }
            for b in bat.get("batsmenData", {}).values()
        ]
        bowling = [
            {
                "Bowler": b.get("bowlName"),
                "Overs": b.get("overs"),
                "Maidens": b.get("maidens"),
                "Runs": b.get("runs"),
                "Wickets": b.get("wickets"),
                "Econ": b.get("economy"),
            }
            for b in bowl.get("bowlersData", {}).values()
        ]
        title = (
            f"{bat.get('batTeamName', 'Team')} - "
            f"{score.get('runs', '?')}/{score.get('wickets', '?')} "
            f"({score.get('overs', '?')} ov)"
        )
        innings_list.append(
            {
                "title": title,
                "batting_df": pd.DataFrame(batting),
                "bowling_df": pd.DataFrame(bowling),
            }
        )
    return innings_list


def parse_top_stats(payload: dict) -> pd.DataFrame:
    """Top-stats come back as {'headers': [...], 'values': [{'values': [...]}]}."""
    headers = payload.get("headers") or []
    rows = [row.get("values", []) for row in payload.get("values", [])]
    if not headers or not rows:
        return pd.DataFrame()
    width = max(len(headers), max(len(r) for r in rows))
    headers = list(headers) + [f"col{i}" for i in range(len(headers), width)]
    rows = [list(r) + [None] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows, columns=headers)
