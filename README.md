<div align="center">

# 🏏 Cricbuzz LiveStats

**Real-time cricket insights and SQL-based analytics in one Streamlit dashboard**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00.svg)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Default%20DB-003B57.svg)](https://www.sqlite.org/)
[![API](https://img.shields.io/badge/Data-Cricbuzz%20via%20RapidAPI-1A73E8.svg)](https://rapidapi.com/)

</div>

---

## 📖 Overview

Cricbuzz LiveStats is a multi-page Streamlit app that combines two data sources:

- **Live data** from the Cricbuzz Cricket API (REST/JSON via RapidAPI): live scores, scorecards and top player charts.
- **A SQL database** for historical analytics, 25 practice queries (beginner to advanced) and full CRUD on players and career stats.

## ✨ Features

- 📡 **Live, recent and upcoming matches** with full scorecards
- 📊 **Top batting and bowling charts** from the API, plus career leaderboards from the database
- 🧠 **25 SQL questions** across three difficulty levels, using joins, CTEs and window functions (`RANK`, `ROW_NUMBER`, `LAG`)
- 🔒 **Safe custom SQL runner** (SELECT-only) with CSV download
- 🛠️ **CRUD interface** to add, view, edit and delete players and career stats
- ⚡ **Smart caching** (60 s for matches, 1 h for stats) to protect your free API quota
- 🔌 **Database-agnostic**: SQLite by default, MySQL and PostgreSQL supported via `DB_URL`

## 🗂️ Pages

| Page | File | Purpose |
|---|---|---|
| 🏠 Home | `pages/home.py` | Overview, tools, quick-start |
| 📡 Live Matches | `pages/live_matches.py` | Live / recent / upcoming matches and full scorecards (API) |
| 📊 Top Player Stats | `pages/top_stats.py` | Top batting/bowling charts (API) and career leaderboards (DB) |
| 🧠 SQL Analytics | `pages/sql_queries.py` | 25 practice queries and a safe custom SELECT runner |
| 🛠️ CRUD Operations | `pages/crud_operations.py` | Create, read, update and delete players and career stats |

<!-- Add screenshots here, for example:
![Live Matches](docs/live_matches.png)
-->

## 🧰 Tech Stack

| Layer | Tools |
|---|---|
| Frontend | Streamlit |
| Data access | SQLAlchemy |
| Database | SQLite (default), MySQL, PostgreSQL |
| Live data | Cricbuzz Cricket API on RapidAPI |
| Language | Python |

## 📁 Project Structure

```
cricbuzz_livestats/
├── app.py                    # Streamlit entry point (navigation)
├── requirements.txt
├── schema.sql                # table structure + indexes
├── sample_data.sql           # synthetic sample data (INSERT statements)
├── .env.example              # copy to .env and add your key
├── pages/                    # one file per Streamlit page
├── utils/
│   ├── api_client.py         # Cricbuzz REST calls + JSON parsers
│   ├── db_connection.py      # centralised DB connection (SQLAlchemy)
│   └── sql_queries.py        # the 25 questions and SQL answers
└── scripts/
    ├── seed_sample_data.py   # build synthetic DB (works offline)
    └── fetch_and_load.py     # pull REAL data from the API into the DB
```

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Vishesh-spec/Cricbuzz.git
cd Cricbuzz
```

### 2. Create a virtual environment

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure secrets

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

Then open `.env` and add your API key (see [API Key Configuration](#-api-key-configuration)).

### 5. Create the database with demo data

No API key is needed for this step:

```bash
python scripts/seed_sample_data.py
```

### 6. Run the app

```bash
streamlit run app.py
```

## 🔑 API Key Configuration

1. Create a free account at [rapidapi.com](https://rapidapi.com).
2. Open the **Cricbuzz Cricket** API listing and click **Subscribe to Test** on the free *Basic* plan.
3. In the API's *Playground* tab, copy the value of `X-RapidAPI-Key`.
4. Put it in `.env`:

   ```env
   RAPIDAPI_KEY=your_key_here
   ```

5. Restart Streamlit.

> [!WARNING]
> `.env` is git-ignored. **Never commit it.**

Free plans have a small monthly request quota, so the app caches responses to conserve it.

## 🌐 How Data Is Fetched

Every request is an HTTPS `GET` with two headers:

```python
import requests

r = requests.get(
    "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live",
    headers={
        "x-rapidapi-key": KEY,
        "x-rapidapi-host": "cricbuzz-cricket.p.rapidapi.com",
    },
    timeout=15,
)
r.raise_for_status()
data = r.json()   # nested dict -> flatten with utils/api_client.py
```

### Endpoints used

Verify in the RapidAPI *Playground* if one changes.

| Purpose | Endpoint |
|---|---|
| Live / recent / upcoming matches | `/matches/v1/live`, `/matches/v1/recent`, `/matches/v1/upcoming` |
| Scorecard | `/mcenter/v1/{matchId}/scard` |
| Match info | `/mcenter/v1/{matchId}` |
| Top stats | `/stats/v1/topstats/0?statsType=mostRuns` |
| Player search / profile | `/stats/v1/player/search?plrN=...`, `/stats/v1/player/{id}` |
| Teams / squads | `/teams/v1/international`, `/teams/v1/{teamId}/players` |
| Series / venues | `/series/v1/international`, `/venues/v1/{venueId}` |

### Loading real data into SQL

```bash
python scripts/fetch_and_load.py --teams --players --matches
```

> [!TIP]
> Use a separate database (`DB_URL=sqlite:///real.db`) so API IDs do not collide with the synthetic seed IDs.

The API does not expose full per-innings history for every match, so the advanced queries (partnerships, form, quarterly trends) need scorecard data. Load more scorecards with `api.get_scorecard(match_id)` as your quota allows.

## 🗄️ Database

**Tables:** `teams`, `venues`, `players`, `series`, `matches`, `batting_scorecard`, `bowling_scorecard`, `fielding_stats`, `player_career_stats`

See `schema.sql` for foreign keys and indexes on all frequently joined columns.

To load without Python:

```bash
sqlite3 cricbuzz.db < schema.sql
sqlite3 cricbuzz.db < sample_data.sql
```

> [!NOTE]
> `sample_data.sql` and the seed script generate **synthetic** data (fictional players and results) so that all 25 queries return rows. Dates are relative to the day the seed script runs.

### Using other databases

Set `DB_URL` in `.env`:

```env
# MySQL (pip install pymysql)
DB_URL=mysql+pymysql://user:pass@localhost:3306/cricbuzz

# PostgreSQL (pip install psycopg2-binary)
DB_URL=postgresql+psycopg2://user:pass@localhost:5432/cricbuzz
```

The queries are written for SQLite. `utils/sql_queries.py` lists the few functions to swap (`date('now', ...)`, `strftime`, `||`).

## 🧠 The 25 SQL Questions

All questions live in `utils/sql_queries.py` and are browsable on the **SQL Analytics** page.

| Level | Questions | Concepts |
|---|---|---|
| 🟢 Beginner | 1 to 8 | Filtering, sorting, aggregates |
| 🟡 Intermediate | 9 to 16 | Joins, grouping, subqueries |
| 🔴 Advanced | 17 to 25 | CTEs, `RANK`, `ROW_NUMBER`, `LAG` |

### Assumptions

- **Q13 / Q24:** following the brief, a "partnership" is two *consecutive batting positions* with their **combined individual runs** (not ball-by-ball partnership data).
- **Q22:** run-margins and wicket-margins are reported separately because they are not comparable.
- **Q23:** form thresholds are Excellent (average of 50 or more in the last 5 and at least 3 fifties), Good (35 or more) and Average (20 or more).
- **Q25:** trend thresholds are ±5% per quarter and ±10% for career phase.

The Q23 and Q25 thresholds are my own choices, so tune them as you like.

## 🔐 Code Quality and Security

- PEP 8 style with docstrings and a modular `utils/` layer
- `try/except` around API calls (`CricbuzzAPIError`) and database operations
- Secrets kept in `.env` (git-ignored)
- Custom SQL box is **SELECT-only**
- **Parameterised SQL** in CRUD (no string-built user input)

<details>
<summary><b>🎬 Demo video outline (3 to 5 min)</b></summary>

1. **Intro (20 s):** problem statement, tech stack, folder structure
2. **Home and sidebar (15 s):** DB status indicator
3. **Live Matches (60 s):** switch Live/Recent, open a scorecard
4. **Top Stats (40 s):** API tab, then database tab
5. **SQL Analytics (60 s):** run a beginner, an intermediate and an advanced query; show the SQL and CSV download; run a custom query
6. **CRUD (60 s):** add a player, edit, view, delete; edit a career-stats row
7. **Wrap-up (20 s):** error handling, modular utils, secrets in `.env`

</details>

## 👤 Author

**Vishesh Mani Tripathi** ([@Vishesh-spec](https://github.com/Vishesh-spec))
