-- =====================================================================
-- Cricbuzz LiveStats - database schema (SQLite flavour)
-- Works as-is on SQLite. For MySQL / PostgreSQL see the notes in README:
--   * MySQL:      use AUTO_INCREMENT where needed, VARCHAR(n) instead of TEXT keys
--   * PostgreSQL: DATE/REAL/TEXT are fine, replace strftime()/date('now') in queries
-- Run order matters because of foreign keys.
-- =====================================================================

CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,
    team_name   TEXT NOT NULL UNIQUE,
    short_name  TEXT,
    country     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id    INTEGER PRIMARY KEY,
    venue_name  TEXT NOT NULL,
    city        TEXT,
    country     TEXT,
    capacity    INTEGER CHECK (capacity IS NULL OR capacity >= 0)
);

CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    country       TEXT,
    playing_role  TEXT,            -- Batsman / Bowler / All-rounder / Wicket-keeper
    batting_style TEXT,
    bowling_style TEXT,
    team_id       INTEGER REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS series (
    series_id      INTEGER PRIMARY KEY,
    series_name    TEXT NOT NULL,
    host_country   TEXT,
    match_type     TEXT,           -- Test / ODI / T20I
    start_date     DATE,
    end_date       DATE,
    total_matches  INTEGER
);

CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY,
    series_id       INTEGER REFERENCES series(series_id),
    description     TEXT,
    match_format    TEXT CHECK (match_format IN ('Test', 'ODI', 'T20I')),
    team1_id        INTEGER NOT NULL REFERENCES teams(team_id),
    team2_id        INTEGER NOT NULL REFERENCES teams(team_id),
    venue_id        INTEGER REFERENCES venues(venue_id),
    match_date      DATE NOT NULL,
    toss_winner_id  INTEGER REFERENCES teams(team_id),
    toss_decision   TEXT CHECK (toss_decision IS NULL OR toss_decision IN ('bat', 'bowl')),
    winner_id       INTEGER REFERENCES teams(team_id),   -- NULL = tie / no result
    victory_margin  INTEGER,
    victory_type    TEXT CHECK (victory_type IS NULL OR victory_type IN ('runs', 'wickets')),
    status          TEXT DEFAULT 'Complete'
);

CREATE TABLE IF NOT EXISTS batting_scorecard (
    bat_id           INTEGER PRIMARY KEY,
    match_id         INTEGER NOT NULL REFERENCES matches(match_id),
    innings_no       INTEGER NOT NULL,
    player_id        INTEGER NOT NULL REFERENCES players(player_id),
    team_id          INTEGER NOT NULL REFERENCES teams(team_id),
    batting_position INTEGER NOT NULL,
    runs             INTEGER NOT NULL DEFAULT 0,
    balls            INTEGER NOT NULL DEFAULT 0,
    fours            INTEGER DEFAULT 0,
    sixes            INTEGER DEFAULT 0,
    strike_rate      REAL,
    is_out           INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bowling_scorecard (
    bowl_id        INTEGER PRIMARY KEY,
    match_id       INTEGER NOT NULL REFERENCES matches(match_id),
    innings_no     INTEGER NOT NULL,
    player_id      INTEGER NOT NULL REFERENCES players(player_id),
    team_id        INTEGER NOT NULL REFERENCES teams(team_id),
    overs          REAL NOT NULL,
    maidens        INTEGER DEFAULT 0,
    runs_conceded  INTEGER NOT NULL,
    wickets        INTEGER NOT NULL DEFAULT 0,
    economy        REAL
);

CREATE TABLE IF NOT EXISTS fielding_stats (
    field_id   INTEGER PRIMARY KEY,
    match_id   INTEGER NOT NULL REFERENCES matches(match_id),
    player_id  INTEGER NOT NULL REFERENCES players(player_id),
    catches    INTEGER DEFAULT 0,
    stumpings  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_career_stats (
    player_id      INTEGER NOT NULL REFERENCES players(player_id),
    match_format   TEXT NOT NULL CHECK (match_format IN ('Test', 'ODI', 'T20I')),
    matches        INTEGER DEFAULT 0,
    innings        INTEGER DEFAULT 0,
    runs           INTEGER DEFAULT 0,
    balls_faced    INTEGER DEFAULT 0,
    highest_score  INTEGER DEFAULT 0,
    batting_avg    REAL,
    strike_rate    REAL,
    centuries      INTEGER DEFAULT 0,
    fifties        INTEGER DEFAULT 0,
    wickets        INTEGER DEFAULT 0,
    bowling_avg    REAL,
    economy        REAL,
    catches        INTEGER DEFAULT 0,
    stumpings      INTEGER DEFAULT 0,
    PRIMARY KEY (player_id, match_format)
);

-- ---------------------------------------------------------------------
-- Indexes for the columns used most in joins / filters / GROUP BY
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_players_country      ON players(country);
CREATE INDEX IF NOT EXISTS idx_players_role         ON players(playing_role);
CREATE INDEX IF NOT EXISTS idx_matches_date         ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_winner       ON matches(winner_id);
CREATE INDEX IF NOT EXISTS idx_matches_venue        ON matches(venue_id);
CREATE INDEX IF NOT EXISTS idx_matches_teams        ON matches(team1_id, team2_id);
CREATE INDEX IF NOT EXISTS idx_bat_player           ON batting_scorecard(player_id);
CREATE INDEX IF NOT EXISTS idx_bat_match            ON batting_scorecard(match_id, innings_no, batting_position);
CREATE INDEX IF NOT EXISTS idx_bowl_player          ON bowling_scorecard(player_id);
CREATE INDEX IF NOT EXISTS idx_bowl_match           ON bowling_scorecard(match_id);
CREATE INDEX IF NOT EXISTS idx_field_player         ON fielding_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_series_start         ON series(start_date);
