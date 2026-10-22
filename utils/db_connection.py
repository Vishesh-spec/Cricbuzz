"""Centralised database connection logic.

All pages and scripts talk to the database through this module, so switching
from SQLite to MySQL/PostgreSQL only requires changing ``DB_URL`` in ``.env``.
"""
from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_URL = f"sqlite:///{ROOT / 'cricbuzz.db'}"

# Children first, so tables can be dropped without violating foreign keys.
TABLES_DROP_ORDER = [
    "fielding_stats",
    "bowling_scorecard",
    "batting_scorecard",
    "player_career_stats",
    "matches",
    "series",
    "players",
    "venues",
    "teams",
]


def _safe_sqrt(value: Optional[float]) -> Optional[float]:
    """SQRT for SQLite (older builds lack math functions)."""
    if value is None:
        return None
    return math.sqrt(max(float(value), 0.0))


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create (once) and return the SQLAlchemy engine."""
    url = os.getenv("DB_URL", DEFAULT_DB_URL)
    engine = create_engine(url, future=True, pool_pre_ping=True)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _sqlite_setup(dbapi_conn, _record):  # pragma: no cover
            dbapi_conn.create_function("sqrt", 1, _safe_sqrt)
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

    return engine


def run_query(sql: str, params: Optional[dict[str, Any]] = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame.

    Without ``params`` the statement is sent to the driver untouched, so
    characters such as ':' or '%' in ad-hoc SQL are not misread as binds.
    """
    with get_engine().connect() as conn:
        if params:
            result = conn.execute(text(sql), params)
        else:
            result = conn.exec_driver_sql(sql)
        return pd.DataFrame(result.fetchall(), columns=list(result.keys()))


def execute(sql: str, params: Optional[dict[str, Any]] = None) -> int:
    """Run one INSERT/UPDATE/DELETE inside a transaction; return rows affected."""
    with get_engine().begin() as conn:
        return conn.execute(text(sql), params or {}).rowcount


def run_transaction(statements: Iterable[tuple[str, dict[str, Any]]]) -> None:
    """Run several statements atomically (all succeed or none do)."""
    with get_engine().begin() as conn:
        for sql, params in statements:
            conn.execute(text(sql), params)


def scalar(sql: str, params: Optional[dict[str, Any]] = None) -> Any:
    """Return the first column of the first row (or None)."""
    with get_engine().connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


def init_db(reset: bool = False) -> None:
    """Create all tables from ``schema.sql`` (optionally dropping them first)."""
    engine = get_engine()
    with engine.begin() as conn:
        if reset:
            for table in TABLES_DROP_ORDER:
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
        script = (ROOT / "schema.sql").read_text(encoding="utf-8")
        script = re.sub(r"--.*", "", script)  # strip comments
        for statement in script.split(";"):
            if statement.strip():
                conn.exec_driver_sql(statement)


def database_has_data() -> bool:
    """True when the players table exists and has at least one row."""
    try:
        return bool(scalar("SELECT COUNT(*) FROM players"))
    except Exception:  # table missing / DB unreachable
        return False
