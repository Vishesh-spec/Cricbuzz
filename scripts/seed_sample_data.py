"""Generate a SYNTHETIC cricket dataset so every page and all 25 SQL queries work
offline, with no API key.

* Team and venue names are real; **players and all match results are fictional**.
* Use ``scripts/fetch_and_load.py`` to load real data from the Cricbuzz API.

Usage:  python scripts/seed_sample_data.py          (drops and recreates tables)
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from utils.db_connection import get_engine, init_db  # noqa: E402

random.seed(42)
TODAY = date.today()

TEAMS = [
    ("India", "IND"), ("Australia", "AUS"), ("England", "ENG"), ("Pakistan", "PAK"),
    ("South Africa", "SA"), ("New Zealand", "NZ"), ("Sri Lanka", "SL"), ("West Indies", "WI"),
]
# (name, city, country, approx. capacity)
VENUES = [
    ("Narendra Modi Stadium", "Ahmedabad", "India", 132000),
    ("Eden Gardens", "Kolkata", "India", 68000),
    ("Wankhede Stadium", "Mumbai", "India", 33000),
    ("Melbourne Cricket Ground", "Melbourne", "Australia", 100000),
    ("Sydney Cricket Ground", "Sydney", "Australia", 48000),
    ("Lord's", "London", "England", 31000),
    ("The Oval", "London", "England", 27500),
    ("Gaddafi Stadium", "Lahore", "Pakistan", 34000),
    ("Wanderers Stadium", "Johannesburg", "South Africa", 34000),
    ("Newlands", "Cape Town", "South Africa", 25000),
    ("Basin Reserve", "Wellington", "New Zealand", 11600),
    ("Galle International Stadium", "Galle", "Sri Lanka", 35000),
    ("Kensington Oval", "Bridgetown", "West Indies", 28000),
    ("Dubai International Stadium", "Dubai", "UAE", 25000),
]
FIRST = ["Aarav", "Rohan", "Liam", "Noah", "Ethan", "Mason", "Kabir", "Imran", "Hamza", "Dev",
         "Jack", "Oliver", "Sam", "Tom", "Zain", "Arjun", "Callum", "Dylan", "Ravi", "Isaac",
         "Marcus", "Nikhil", "Owen", "Rahul", "Shane", "Tariq", "Umar", "Vikram", "Wesley", "Yash"]
LAST = ["Ashford", "Bennett", "Carver", "Dalton", "Everett", "Fairley", "Granger", "Harlow",
        "Ibsen", "Jarvis", "Kendall", "Lowell", "Maddox", "Norwood", "Oakley", "Prescott",
        "Quinlan", "Rowland", "Sinclair", "Thorne", "Underhill", "Vickers", "Whitlock",
        "Yardley", "Zimmer", "Almeida", "Brennan", "Castillo", "Devlin", "Eastwood"]

ROLES = ["Batsman", "Wicket-keeper", "All-rounder", "Bowler"]
SQUAD_PLAN = ["Batsman"] * 6 + ["Wicket-keeper"] * 2 + ["All-rounder"] * 3 + ["Bowler"] * 4
BOWL_STYLES = ["Right-arm fast", "Right-arm medium", "Right-arm offbreak",
               "Left-arm orthodox", "Legbreak", "Left-arm fast"]
FORMATS = {
    "Test": {"runs": 1.0, "sr": 55, "eco": 3.0, "overs": (15, 30)},
    "ODI": {"runs": 0.9, "sr": 88, "eco": 5.4, "overs": (8, 10)},
    "T20I": {"runs": 0.55, "sr": 135, "eco": 8.1, "overs": (3, 4)},
}
BAT_SKILL = {"Batsman": (36, 46), "Wicket-keeper": (26, 34), "All-rounder": (22, 30), "Bowler": (5, 10)}


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------
def build_players() -> list[dict]:
    names = [f"{f} {l}" for f in FIRST for l in LAST]
    random.shuffle(names)
    players, pid = [], 1
    for team_id, (country, _) in enumerate(TEAMS, start=1):
        for role in SQUAD_PLAN:
            lo, hi = BAT_SKILL[role]
            bowls = role in ("Bowler", "All-rounder")
            players.append({
                "player_id": pid, "full_name": names.pop(), "country": country,
                "playing_role": role,
                "batting_style": random.choice(["Right-hand bat", "Left-hand bat"]),
                "bowling_style": random.choice(BOWL_STYLES) if bowls else None,
                "team_id": team_id,
                "bat_skill": random.uniform(lo, hi),
                "eco_factor": random.uniform(0.8, 1.2),
            })
            pid += 1
    return players


def career_stats(players: list[dict]) -> list[dict]:
    rows = []
    for p in players:
        role = p["playing_role"]
        played = [f for f in FORMATS if random.random() < 0.8] or ["ODI"]
        for fmt in played:
            top = {"Test": 120, "ODI": 220, "T20I": 150}[fmt]
            matches = random.randint(10, top)
            innings = int(matches * 0.9)
            base_avg = p["bat_skill"] * (0.95 if fmt != "T20I" else 0.7)
            avg = round(random.uniform(0.85, 1.15) * base_avg, 2)
            runs = int(avg * innings * 0.85)
            sr = round(random.uniform(*{"Test": (48, 62), "ODI": (76, 98), "T20I": (118, 150)}[fmt]), 2)
            hs = min(400, int(avg * random.uniform(2.5, 5.5)))
            per_ton = {"Batsman": 550, "Wicket-keeper": 900, "All-rounder": 1300, "Bowler": 10 ** 9}[role]
            centuries = int(runs / (per_ton * random.uniform(0.8, 1.3)))
            fifties = int(runs / (per_ton * random.uniform(0.25, 0.4)))
            wk_rate = {"Bowler": (1.2, 2.2), "All-rounder": (0.6, 1.2)}.get(role)
            wickets = int(matches * random.uniform(*wk_rate)) if wk_rate else random.randint(0, 3)
            bowling_avg = round(random.uniform(22, 38), 2) if wickets else None
            eco = round({"Test": 3.0, "ODI": 5.2, "T20I": 7.8}[fmt] * p["eco_factor"], 2) if wickets else None
            catches = int(matches * random.uniform(0.2, 0.7))
            stumpings = int(matches * random.uniform(0.2, 0.7)) if role == "Wicket-keeper" else 0
            rows.append({
                "player_id": p["player_id"], "match_format": fmt, "matches": matches,
                "innings": innings, "runs": runs, "balls_faced": int(runs * 100 / sr),
                "highest_score": hs, "batting_avg": avg, "strike_rate": sr,
                "centuries": centuries, "fifties": fifties, "wickets": wickets,
                "bowling_avg": bowling_avg, "economy": eco, "catches": catches,
                "stumpings": stumpings,
            })
    return rows


# --------------------------------------------------------------------------
# Series & matches
# --------------------------------------------------------------------------
def build_series_plan() -> list[dict]:
    plan = []
    for year in range(2023, TODAY.year + 1):
        for _ in range(36):
            start = date(year, 1, 1) + timedelta(days=random.randint(0, 364))
            if start > TODAY:
                continue
            fmt = random.choices(list(FORMATS), weights=[25, 35, 40])[0]
            n = random.randint(2, 3) if fmt == "Test" else random.randint(3, 5)
            plan.append({"start": start, "fmt": fmt, "n": n, "gap": 5 if fmt == "Test" else 3,
                         "teams": random.sample(range(1, len(TEAMS) + 1), 2)})
    # A series that is "live" right now (guarantees data for the last-30-days query)
    plan.append({"start": TODAY - timedelta(days=24), "fmt": "ODI", "n": 6, "gap": 4,
                 "teams": [1, 2]})
    return plan


def venue_for(host_country: str, venues: list[dict]) -> dict:
    home = [v for v in venues if v["country"] == host_country]
    neutral = [v for v in venues if v["country"] == "UAE"]
    return random.choice(neutral if (not home or random.random() < 0.08) else home)


def make_xi(squad: list[dict]) -> list[dict]:
    by_role = {r: [p for p in squad if p["playing_role"] == r] for r in ROLES}
    xi = (random.sample(by_role["Batsman"], 4) + random.sample(by_role["Wicket-keeper"], 1)
          + random.sample(by_role["All-rounder"], 2) + by_role["Bowler"])
    return sorted(xi, key=lambda p: -p["bat_skill"])  # stable batting order


def play_innings(xi, fmt, team_id, innings_no, match_id, ids, bat_rows):
    f = FORMATS[fmt]
    total, outs = 0, 0
    for pos, p in enumerate(xi, start=1):
        runs = min(int(random.expovariate(1 / (p["bat_skill"] * f["runs"]))), 220)
        sr = max(30.0, random.gauss(f["sr"], f["sr"] * 0.2))
        balls = max(1, round(runs * 100 / sr)) if runs else random.randint(1, 8)
        fours = int(runs * random.uniform(0.25, 0.5) / 4)
        sixes = int(max(0, runs - fours * 4) * random.uniform(0.0, 0.4) / 6)
        is_out = 1 if (random.random() < 0.8 and outs < 10) else 0
        outs += is_out
        total += runs
        bat_rows.append({
            "bat_id": ids["bat"], "match_id": match_id, "innings_no": innings_no,
            "player_id": p["player_id"], "team_id": team_id, "batting_position": pos,
            "runs": runs, "balls": balls, "fours": fours, "sixes": sixes,
            "strike_rate": round(runs * 100 / balls, 2), "is_out": is_out,
        })
        ids["bat"] += 1
    return total + random.randint(5, 15), outs


def bowl_innings(xi, fmt, team_id, innings_no, match_id, ids, bowl_rows):
    f = FORMATS[fmt]
    candidates = [p for p in xi if p["playing_role"] in ("Bowler", "All-rounder")]
    for p in random.sample(candidates, 5):
        overs = random.randint(*f["overs"])
        eco = max(1.5, random.gauss(f["eco"] * p["eco_factor"], f["eco"] * 0.15))
        runs = round(overs * eco)
        bowl_rows.append({
            "bowl_id": ids["bowl"], "match_id": match_id, "innings_no": innings_no,
            "player_id": p["player_id"], "team_id": team_id, "overs": float(overs),
            "maidens": random.choice([0, 0, 0, 1, 2]), "runs_conceded": runs,
            "wickets": random.choice([0, 0, 1, 1, 2, 3, 4]),
            "economy": round(runs / overs, 2),
        })
        ids["bowl"] += 1


def build_matches(players, venues):
    squads = {tid: [p for p in players if p["team_id"] == tid] for tid in range(1, len(TEAMS) + 1)}
    team_name = {i: t[0] for i, t in enumerate(TEAMS, start=1)}

    series_rows, drafts = [], []
    for sid, sp in enumerate(build_series_plan(), start=1):
        t1, t2 = sp["teams"]
        host = team_name[t1]
        venue = venue_for(host, venues)
        dates = [sp["start"] + timedelta(days=i * sp["gap"]) for i in range(sp["n"])]
        series_rows.append({
            "series_id": sid,
            "series_name": f"{host} v {team_name[t2]} {sp['fmt']} Series {sp['start'].year}",
            "host_country": venue["country"], "match_type": sp["fmt"],
            "start_date": dates[0].isoformat(), "end_date": dates[-1].isoformat(),
            "total_matches": sp["n"],
        })
        for i, d in enumerate(dates, start=1):
            if d <= TODAY:
                drafts.append({"series_id": sid, "fmt": sp["fmt"], "date": d, "t1": t1, "t2": t2,
                               "venue": venue, "n": i,
                               "desc": f"{team_name[t1]} vs {team_name[t2]}, {i}{_ord(i)} {sp['fmt']}"})
    # An upcoming series (no matches played yet)
    series_rows.append({
        "series_id": len(series_rows) + 1, "series_name": f"India v England T20I Series {TODAY.year}",
        "host_country": "India", "match_type": "T20I",
        "start_date": (TODAY + timedelta(days=20)).isoformat(),
        "end_date": (TODAY + timedelta(days=30)).isoformat(), "total_matches": 3,
    })

    drafts.sort(key=lambda d: (d["date"], d["series_id"], d["n"]))
    matches, bat_rows, bowl_rows, field = [], [], [], {}
    ids = {"bat": 1, "bowl": 1}
    for mid, d in enumerate(drafts, start=1):
        t1, t2, fmt = d["t1"], d["t2"], d["fmt"]
        toss_winner = random.choice([t1, t2])
        decision = random.choices(["bat", "bowl"], weights=[45, 55])[0]
        first = toss_winner if decision == "bat" else (t2 if toss_winner == t1 else t1)
        second = t2 if first == t1 else t1
        xi = {t1: make_xi(squads[t1]), t2: make_xi(squads[t2])}

        first_total, _ = play_innings(xi[first], fmt, first, 1, mid, ids, bat_rows)
        second_total, second_outs = play_innings(xi[second], fmt, second, 2, mid, ids, bat_rows)
        bowl_innings(xi[second], fmt, second, 1, mid, ids, bowl_rows)
        bowl_innings(xi[first], fmt, first, 2, mid, ids, bowl_rows)

        winner = margin = vtype = None
        if second_total > first_total:
            winner, vtype, margin = second, "wickets", max(1, 10 - second_outs)
        elif first_total > second_total:
            winner, vtype, margin = first, "runs", first_total - second_total

        for fielding_team in (t1, t2):  # fielding stats
            for p in random.sample(xi[fielding_team], 3):
                rec = field.setdefault((mid, p["player_id"]), {"catches": 0, "stumpings": 0})
                rec["catches"] += random.choice([0, 1, 1, 2])
                if p["playing_role"] == "Wicket-keeper":
                    rec["stumpings"] += random.choice([0, 0, 1])

        matches.append({
            "match_id": mid, "series_id": d["series_id"], "description": d["desc"],
            "match_format": fmt, "team1_id": t1, "team2_id": t2,
            "venue_id": d["venue"]["venue_id"], "match_date": d["date"].isoformat(),
            "toss_winner_id": toss_winner, "toss_decision": decision, "winner_id": winner,
            "victory_margin": margin, "victory_type": vtype,
            "status": "Complete" if winner else "Tie",
        })
    field_rows = [{"field_id": i, "match_id": k[0], "player_id": k[1], **v}
                  for i, (k, v) in enumerate(field.items(), start=1)]
    return series_rows, matches, bat_rows, bowl_rows, field_rows


def _ord(n: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(n if n < 4 else 4, "th")


# --------------------------------------------------------------------------
def insert(conn, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0])
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
    conn.execute(text(sql), rows)
    print(f"  {table:<22}{len(rows):>7} rows")


def main() -> None:
    init_db(reset=True)
    players = build_players()
    venues = [{"venue_id": i, "venue_name": n, "city": c, "country": k, "capacity": cap}
              for i, (n, c, k, cap) in enumerate(VENUES, start=1)]
    series_rows, matches, bat, bowl, field = build_matches(players, venues)
    db_players = [{k: p[k] for k in ("player_id", "full_name", "country", "playing_role",
                                     "batting_style", "bowling_style", "team_id")} for p in players]
    print("Seeding synthetic data ...")
    with get_engine().begin() as conn:
        insert(conn, "teams", [{"team_id": i, "team_name": n, "short_name": s, "country": n}
                               for i, (n, s) in enumerate(TEAMS, start=1)])
        insert(conn, "venues", venues)
        insert(conn, "players", db_players)
        insert(conn, "series", series_rows)
        insert(conn, "matches", matches)
        insert(conn, "batting_scorecard", bat)
        insert(conn, "bowling_scorecard", bowl)
        insert(conn, "fielding_stats", field)
        insert(conn, "player_career_stats", career_stats(players))
    print("Done.")


if __name__ == "__main__":
    main()
