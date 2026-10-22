"""The 25 practice questions and their SQL answers (SQLite dialect).

Each entry:  number, level, title, question, sql
``sql`` is either a string or a list of (label, sql) tuples for multi-part answers.

Dialect notes for MySQL / PostgreSQL:
  date('now', '-30 day')   -> CURDATE() - INTERVAL 30 DAY  /  CURRENT_DATE - INTERVAL '30 days'
  strftime('%Y', d)        -> YEAR(d)                      /  EXTRACT(YEAR FROM d)
  a || b                   -> CONCAT(a, b)                 (MySQL)
  sqrt(avg(x*x)-avg(x)^2)  -> STDDEV_POP(x)                (both)
"""

# ---------------------------------------------------------------------------
# Shared CTE for Q22 (head-to-head, last 3 years)
# ---------------------------------------------------------------------------
_PAIR_CTE = """
WITH pair_matches AS (
    SELECT m.*,
           CASE WHEN m.team1_id < m.team2_id THEN m.team1_id ELSE m.team2_id END AS team_a,
           CASE WHEN m.team1_id < m.team2_id THEN m.team2_id ELSE m.team1_id END AS team_b,
           CASE WHEN m.toss_decision = 'bat' THEN m.toss_winner_id
                WHEN m.toss_winner_id = m.team1_id THEN m.team2_id
                ELSE m.team1_id END AS bat_first_id
    FROM matches m
    WHERE m.status = 'Complete'
      AND m.winner_id IS NOT NULL
      AND m.match_date >= date('now', '-3 year')
)"""

_PARTNERSHIP_JOIN = """
    FROM batting_scorecard b1
    JOIN batting_scorecard b2
      ON  b2.match_id         = b1.match_id
      AND b2.innings_no       = b1.innings_no
      AND b2.team_id          = b1.team_id
      AND b2.batting_position = b1.batting_position + 1"""

_Q25_CTE = """
WITH quarterly AS (
    SELECT b.player_id,
           strftime('%Y', m.match_date) || '-Q' ||
               ((CAST(strftime('%m', m.match_date) AS INTEGER) + 2) / 3) AS quarter,
           COUNT(DISTINCT b.match_id) AS matches,
           AVG(b.runs)                AS avg_runs,
           AVG(b.strike_rate)         AS avg_sr
    FROM batting_scorecard b
    JOIN matches m ON m.match_id = b.match_id
    GROUP BY b.player_id, quarter
    HAVING COUNT(DISTINCT b.match_id) >= 3
),
trend AS (
    SELECT q.*,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY quarter) AS rn,
           COUNT(*)     OVER (PARTITION BY player_id)                  AS n_quarters,
           LAG(avg_runs) OVER (PARTITION BY player_id ORDER BY quarter) AS prev_runs,
           LAG(avg_sr)   OVER (PARTITION BY player_id ORDER BY quarter) AS prev_sr
    FROM quarterly q
)"""

QUERIES = [
    # ======================= BEGINNER (1-8) =======================
    {
        "number": 1, "level": "Beginner",
        "title": "Players who represent India",
        "question": "Find all players who represent India. Display full name, playing role, batting style and bowling style.",
        "sql": """
SELECT full_name, playing_role, batting_style, bowling_style
FROM players
WHERE country = 'India'
ORDER BY full_name""",
    },
    {
        "number": 2, "level": "Beginner",
        "title": "Matches in the last 30 days",
        "question": "Show matches played in the last 30 days with description, both teams, venue (with city) and date, most recent first.",
        "sql": """
SELECT m.description AS match_description,
       t1.team_name  AS team1,
       t2.team_name  AS team2,
       v.venue_name || ', ' || v.city AS venue,
       m.match_date
FROM matches m
JOIN teams  t1 ON t1.team_id  = m.team1_id
JOIN teams  t2 ON t2.team_id  = m.team2_id
JOIN venues v  ON v.venue_id  = m.venue_id
WHERE m.match_date >= date('now', '-30 day')
  AND m.match_date <= date('now')
ORDER BY m.match_date DESC""",
    },
    {
        "number": 3, "level": "Beginner",
        "title": "Top 10 ODI run scorers",
        "question": "List the top 10 highest run scorers in ODI cricket: name, total runs, batting average, centuries.",
        "sql": """
SELECT p.full_name, pcs.runs AS total_runs, pcs.batting_avg, pcs.centuries
FROM player_career_stats pcs
JOIN players p ON p.player_id = pcs.player_id
WHERE pcs.match_format = 'ODI'
ORDER BY pcs.runs DESC
LIMIT 10""",
    },
    {
        "number": 4, "level": "Beginner",
        "title": "Venues with capacity above 50,000",
        "question": "Display venues with seating capacity > 50,000: name, city, country, capacity, largest first.",
        "sql": """
SELECT venue_name, city, country, capacity
FROM venues
WHERE capacity > 50000
ORDER BY capacity DESC""",
    },
    {
        "number": 5, "level": "Beginner",
        "title": "Matches won by each team",
        "question": "Calculate how many matches each team has won, most wins first.",
        "sql": """
SELECT t.team_name, COUNT(*) AS total_wins
FROM matches m
JOIN teams t ON t.team_id = m.winner_id
GROUP BY t.team_id, t.team_name
ORDER BY total_wins DESC""",
    },
    {
        "number": 6, "level": "Beginner",
        "title": "Players per playing role",
        "question": "Count how many players belong to each playing role.",
        "sql": """
SELECT playing_role, COUNT(*) AS player_count
FROM players
GROUP BY playing_role
ORDER BY player_count DESC""",
    },
    {
        "number": 7, "level": "Beginner",
        "title": "Highest individual score per format",
        "question": "Find the highest individual batting score in each format (Test, ODI, T20I).",
        "sql": """
SELECT match_format, MAX(highest_score) AS highest_score
FROM player_career_stats
GROUP BY match_format
ORDER BY highest_score DESC""",
    },
    {
        "number": 8, "level": "Beginner",
        "title": "Series that started in 2024",
        "question": "Show all series that started in 2024: name, host country, match type, start date, matches planned.",
        "sql": """
SELECT series_name, host_country, match_type, start_date, total_matches
FROM series
WHERE strftime('%Y', start_date) = '2024'
ORDER BY start_date""",
    },
    # ======================= INTERMEDIATE (9-16) =======================
    {
        "number": 9, "level": "Intermediate",
        "title": "All-rounders with 1000+ runs and 50+ wickets",
        "question": "Find all-rounders with more than 1000 runs AND more than 50 wickets: name, runs, wickets, format.",
        "sql": """
SELECT p.full_name,
       pcs.runs    AS total_runs,
       pcs.wickets AS total_wickets,
       pcs.match_format
FROM player_career_stats pcs
JOIN players p ON p.player_id = pcs.player_id
WHERE p.playing_role LIKE '%All%'
  AND pcs.runs > 1000
  AND pcs.wickets > 50
ORDER BY pcs.runs DESC""",
    },
    {
        "number": 10, "level": "Intermediate",
        "title": "Last 20 completed matches",
        "question": "Details of the last 20 completed matches: description, teams, winner, margin, victory type and venue, newest first.",
        "sql": """
SELECT m.description,
       t1.team_name AS team1,
       t2.team_name AS team2,
       w.team_name  AS winning_team,
       m.victory_margin,
       m.victory_type,
       v.venue_name,
       m.match_date
FROM matches m
JOIN teams  t1 ON t1.team_id = m.team1_id
JOIN teams  t2 ON t2.team_id = m.team2_id
JOIN teams  w  ON w.team_id  = m.winner_id
JOIN venues v  ON v.venue_id = m.venue_id
WHERE m.status = 'Complete'
ORDER BY m.match_date DESC, m.match_id DESC
LIMIT 20""",
    },
    {
        "number": 11, "level": "Intermediate",
        "title": "Player performance across formats",
        "question": "For players who played at least 2 formats: runs in Test, ODI, T20I and overall batting average.",
        "sql": """
SELECT p.full_name,
       SUM(CASE WHEN pcs.match_format = 'Test' THEN pcs.runs ELSE 0 END) AS test_runs,
       SUM(CASE WHEN pcs.match_format = 'ODI'  THEN pcs.runs ELSE 0 END) AS odi_runs,
       SUM(CASE WHEN pcs.match_format = 'T20I' THEN pcs.runs ELSE 0 END) AS t20i_runs,
       -- overall average = total runs / total dismissals, dismissals = runs / avg
       ROUND(SUM(pcs.runs) * 1.0 / SUM(pcs.runs * 1.0 / NULLIF(pcs.batting_avg, 0)), 2) AS overall_batting_avg,
       COUNT(DISTINCT pcs.match_format) AS formats_played
FROM player_career_stats pcs
JOIN players p ON p.player_id = pcs.player_id
WHERE pcs.runs > 0 AND pcs.batting_avg > 0
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT pcs.match_format) >= 2
ORDER BY overall_batting_avg DESC""",
    },
    {
        "number": 12, "level": "Intermediate",
        "title": "Home vs away wins per team",
        "question": "Analyse each team's home vs away record (home = venue country equals the team's country).",
        "sql": """
WITH team_matches AS (
    SELECT m.match_id, m.team1_id AS team_id, m.winner_id, v.country AS venue_country
    FROM matches m JOIN venues v ON v.venue_id = m.venue_id
    WHERE m.status = 'Complete'
    UNION ALL
    SELECT m.match_id, m.team2_id AS team_id, m.winner_id, v.country AS venue_country
    FROM matches m JOIN venues v ON v.venue_id = m.venue_id
    WHERE m.status = 'Complete'
)
SELECT t.team_name,
       CASE WHEN t.country = tm.venue_country THEN 'Home' ELSE 'Away' END AS venue_type,
       COUNT(*) AS matches_played,
       SUM(CASE WHEN tm.winner_id = tm.team_id THEN 1 ELSE 0 END) AS wins,
       ROUND(100.0 * SUM(CASE WHEN tm.winner_id = tm.team_id THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM team_matches tm
JOIN teams t ON t.team_id = tm.team_id
GROUP BY t.team_name, venue_type
ORDER BY t.team_name, venue_type""",
    },
    {
        "number": 13, "level": "Intermediate",
        "title": "Partnerships of 100+ (consecutive batsmen)",
        "question": "Find consecutive batsmen (adjacent positions) whose combined runs in an innings are 100 or more.",
        "sql": f"""
SELECT p1.full_name AS batsman_1,
       p2.full_name AS batsman_2,
       b1.runs + b2.runs AS partnership_runs,
       b1.match_id,
       b1.innings_no AS innings
{_PARTNERSHIP_JOIN}
JOIN players p1 ON p1.player_id = b1.player_id
JOIN players p2 ON p2.player_id = b2.player_id
WHERE b1.runs + b2.runs >= 100
ORDER BY partnership_runs DESC""",
    },
    {
        "number": 14, "level": "Intermediate",
        "title": "Bowling performance by venue",
        "question": "Bowlers with 3+ matches at the same venue (4+ overs each match): average economy, total wickets, matches.",
        "sql": """
SELECT p.full_name,
       v.venue_name,
       COUNT(DISTINCT bw.match_id) AS matches_played,
       SUM(bw.wickets)             AS total_wickets,
       ROUND(AVG(bw.economy), 2)   AS avg_economy
FROM bowling_scorecard bw
JOIN matches m ON m.match_id  = bw.match_id
JOIN venues  v ON v.venue_id  = m.venue_id
JOIN players p ON p.player_id = bw.player_id
WHERE bw.overs >= 4
GROUP BY p.player_id, p.full_name, v.venue_id, v.venue_name
HAVING COUNT(DISTINCT bw.match_id) >= 3
ORDER BY avg_economy ASC""",
    },
    {
        "number": 15, "level": "Intermediate",
        "title": "Performance in close matches",
        "question": "Close match = won by < 50 runs OR < 5 wickets. Per player: average runs, close matches played, close matches won by their team.",
        "sql": """
SELECT p.full_name,
       ROUND(AVG(b.runs), 2)         AS avg_runs_in_close_matches,
       COUNT(DISTINCT b.match_id)    AS close_matches_played,
       COUNT(DISTINCT CASE WHEN m.winner_id = b.team_id THEN b.match_id END) AS close_matches_won
FROM batting_scorecard b
JOIN matches m ON m.match_id  = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE (m.victory_type = 'runs'    AND m.victory_margin < 50)
   OR (m.victory_type = 'wickets' AND m.victory_margin < 5)
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT b.match_id) >= 3
ORDER BY avg_runs_in_close_matches DESC""",
    },
    {
        "number": 16, "level": "Intermediate",
        "title": "Batting performance by year (since 2020)",
        "question": "Since 2020: each player's average runs per match and strike rate per year (min 5 matches in that year).",
        "sql": """
SELECT p.full_name,
       strftime('%Y', m.match_date) AS match_year,
       COUNT(DISTINCT b.match_id)   AS matches,
       ROUND(AVG(b.runs), 2)        AS avg_runs,
       ROUND(AVG(b.strike_rate), 2) AS avg_strike_rate
FROM batting_scorecard b
JOIN matches m ON m.match_id  = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE m.match_date >= '2020-01-01'
GROUP BY p.player_id, p.full_name, match_year
HAVING COUNT(DISTINCT b.match_id) >= 5
ORDER BY match_year, avg_runs DESC""",
    },
    # ======================= ADVANCED (17-25) =======================
    {
        "number": 17, "level": "Advanced",
        "title": "Does winning the toss help?",
        "question": "What percentage of matches are won by the toss winner, split by toss decision (bat / bowl)?",
        "sql": """
SELECT toss_decision,
       COUNT(*) AS matches,
       SUM(CASE WHEN toss_winner_id = winner_id THEN 1 ELSE 0 END) AS toss_winner_won,
       ROUND(100.0 * SUM(CASE WHEN toss_winner_id = winner_id THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_pct
FROM matches
WHERE winner_id IS NOT NULL AND toss_winner_id IS NOT NULL AND toss_decision IS NOT NULL
GROUP BY toss_decision
UNION ALL
SELECT 'overall',
       COUNT(*),
       SUM(CASE WHEN toss_winner_id = winner_id THEN 1 ELSE 0 END),
       ROUND(100.0 * SUM(CASE WHEN toss_winner_id = winner_id THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM matches
WHERE winner_id IS NOT NULL AND toss_winner_id IS NOT NULL AND toss_decision IS NOT NULL""",
    },
    {
        "number": 18, "level": "Advanced",
        "title": "Most economical limited-overs bowlers",
        "question": "ODI + T20I bowlers with 10+ matches and at least 2 overs per match on average: economy rate and wickets.",
        "sql": """
SELECT p.full_name,
       COUNT(DISTINCT bw.match_id) AS matches,
       ROUND(SUM(bw.overs), 1)     AS total_overs,
       SUM(bw.wickets)             AS total_wickets,
       ROUND(SUM(bw.runs_conceded) * 1.0 / SUM(bw.overs), 2) AS economy_rate
FROM bowling_scorecard bw
JOIN matches m ON m.match_id  = bw.match_id
JOIN players p ON p.player_id = bw.player_id
WHERE m.match_format IN ('ODI', 'T20I')
GROUP BY p.player_id, p.full_name
HAVING COUNT(DISTINCT bw.match_id) >= 10
   AND SUM(bw.overs) * 1.0 / COUNT(DISTINCT bw.match_id) >= 2
ORDER BY economy_rate ASC
LIMIT 25""",
    },
    {
        "number": 19, "level": "Advanced",
        "title": "Most consistent batsmen",
        "question": "Since 2022, innings where the batter faced 10+ balls: average runs and standard deviation (lower = more consistent).",
        "sql": """
SELECT p.full_name,
       COUNT(*)                 AS innings,
       ROUND(AVG(b.runs), 2)    AS avg_runs,
       ROUND(sqrt(AVG(b.runs * 1.0 * b.runs) - AVG(b.runs * 1.0) * AVG(b.runs * 1.0)), 2) AS std_dev_runs
FROM batting_scorecard b
JOIN matches m ON m.match_id  = b.match_id
JOIN players p ON p.player_id = b.player_id
WHERE m.match_date >= '2022-01-01'
  AND b.balls >= 10
GROUP BY p.player_id, p.full_name
HAVING COUNT(*) >= 10          -- need a reasonable sample for a std-dev
ORDER BY std_dev_runs ASC""",
    },
    {
        "number": 20, "level": "Advanced",
        "title": "Matches and batting average per format",
        "question": "Per player: number of Test / ODI / T20 matches and batting average in each (min 20 total matches).",
        "sql": """
SELECT p.full_name,
       SUM(CASE WHEN pcs.match_format = 'Test' THEN pcs.matches ELSE 0 END) AS test_matches,
       SUM(CASE WHEN pcs.match_format = 'ODI'  THEN pcs.matches ELSE 0 END) AS odi_matches,
       SUM(CASE WHEN pcs.match_format = 'T20I' THEN pcs.matches ELSE 0 END) AS t20i_matches,
       MAX(CASE WHEN pcs.match_format = 'Test' THEN pcs.batting_avg END)    AS test_avg,
       MAX(CASE WHEN pcs.match_format = 'ODI'  THEN pcs.batting_avg END)    AS odi_avg,
       MAX(CASE WHEN pcs.match_format = 'T20I' THEN pcs.batting_avg END)    AS t20i_avg,
       SUM(pcs.matches) AS total_matches
FROM player_career_stats pcs
JOIN players p ON p.player_id = pcs.player_id
GROUP BY p.player_id, p.full_name
HAVING SUM(pcs.matches) >= 20
ORDER BY total_matches DESC""",
    },
    {
        "number": 21, "level": "Advanced",
        "title": "Weighted player performance ranking",
        "question": "Combine batting, bowling and fielding points using the given formula and rank the top performers in each format.",
        "sql": """
WITH scored AS (
    SELECT p.full_name,
           pcs.match_format,
           (pcs.runs * 0.01 + COALESCE(pcs.batting_avg, 0) * 0.5 + COALESCE(pcs.strike_rate, 0) * 0.3)
               AS batting_points,
           CASE WHEN pcs.wickets > 0
                THEN pcs.wickets * 2
                     + (50 - COALESCE(pcs.bowling_avg, 50)) * 0.5
                     + (6  - COALESCE(pcs.economy, 6)) * 2
                ELSE 0 END AS bowling_points,
           (pcs.catches * 3 + pcs.stumpings * 5) AS fielding_points
    FROM player_career_stats pcs
    JOIN players p ON p.player_id = pcs.player_id
),
ranked AS (
    SELECT s.*,
           batting_points + bowling_points + fielding_points AS total_points,
           RANK() OVER (PARTITION BY match_format
                        ORDER BY batting_points + bowling_points + fielding_points DESC) AS rank_in_format
    FROM scored s
)
SELECT match_format, rank_in_format, full_name,
       ROUND(batting_points, 2)  AS batting_points,
       ROUND(bowling_points, 2)  AS bowling_points,
       fielding_points,
       ROUND(total_points, 2)    AS total_points
FROM ranked
WHERE rank_in_format <= 10
ORDER BY match_format, rank_in_format""",
    },
    {
        "number": 22, "level": "Advanced",
        "title": "Head-to-head prediction analysis (last 3 years)",
        "question": "For team pairs with 5+ matches in the last 3 years: wins, average victory margins, win %, and batting-first vs bowling-first results by venue.",
        "sql": [
            (
                "Head-to-head summary",
                _PAIR_CTE + """
SELECT ta.team_name AS team_a,
       tb.team_name AS team_b,
       COUNT(*)     AS total_matches,
       SUM(CASE WHEN pm.winner_id = pm.team_a THEN 1 ELSE 0 END) AS team_a_wins,
       SUM(CASE WHEN pm.winner_id = pm.team_b THEN 1 ELSE 0 END) AS team_b_wins,
       ROUND(AVG(CASE WHEN pm.winner_id = pm.team_a AND pm.victory_type = 'runs'    THEN pm.victory_margin END), 1) AS a_avg_win_runs,
       ROUND(AVG(CASE WHEN pm.winner_id = pm.team_a AND pm.victory_type = 'wickets' THEN pm.victory_margin END), 1) AS a_avg_win_wkts,
       ROUND(AVG(CASE WHEN pm.winner_id = pm.team_b AND pm.victory_type = 'runs'    THEN pm.victory_margin END), 1) AS b_avg_win_runs,
       ROUND(AVG(CASE WHEN pm.winner_id = pm.team_b AND pm.victory_type = 'wickets' THEN pm.victory_margin END), 1) AS b_avg_win_wkts,
       ROUND(100.0 * SUM(CASE WHEN pm.winner_id = pm.team_a THEN 1 ELSE 0 END) / COUNT(*), 1) AS team_a_win_pct,
       ROUND(100.0 * SUM(CASE WHEN pm.winner_id = pm.team_b THEN 1 ELSE 0 END) / COUNT(*), 1) AS team_b_win_pct
FROM pair_matches pm
JOIN teams ta ON ta.team_id = pm.team_a
JOIN teams tb ON tb.team_id = pm.team_b
GROUP BY pm.team_a, pm.team_b, ta.team_name, tb.team_name
HAVING COUNT(*) >= 5
ORDER BY total_matches DESC""",
            ),
            (
                "Batting first vs bowling first, by venue",
                _PAIR_CTE + """,
eligible AS (
    SELECT team_a, team_b FROM pair_matches GROUP BY team_a, team_b HAVING COUNT(*) >= 5
)
SELECT ta.team_name AS team_a,
       tb.team_name AS team_b,
       v.venue_name,
       COUNT(*)     AS matches,
       SUM(CASE WHEN pm.winner_id =  pm.bat_first_id THEN 1 ELSE 0 END) AS won_batting_first,
       SUM(CASE WHEN pm.winner_id <> pm.bat_first_id THEN 1 ELSE 0 END) AS won_bowling_first
FROM pair_matches pm
JOIN eligible e ON e.team_a = pm.team_a AND e.team_b = pm.team_b
JOIN teams  ta ON ta.team_id = pm.team_a
JOIN teams  tb ON tb.team_id = pm.team_b
JOIN venues v  ON v.venue_id = pm.venue_id
GROUP BY ta.team_name, tb.team_name, v.venue_name
ORDER BY team_a, team_b, matches DESC""",
            ),
        ],
    },
    {
        "number": 23, "level": "Advanced",
        "title": "Recent player form and momentum",
        "question": "From each player's last 10 innings: avg of last 5 vs last 10, strike-rate trend, 50+ scores, consistency, and a form category.",
        "sql": """
WITH recent AS (
    SELECT b.player_id, b.runs, b.strike_rate,
           ROW_NUMBER() OVER (PARTITION BY b.player_id
                              ORDER BY m.match_date DESC, m.match_id DESC, b.innings_no DESC) AS rn
    FROM batting_scorecard b
    JOIN matches m ON m.match_id = b.match_id
    WHERE b.balls > 0
),
agg AS (
    SELECT player_id,
           COUNT(*)                                       AS innings_used,
           AVG(CASE WHEN rn <= 5 THEN runs END)           AS avg_last5,
           AVG(runs)                                      AS avg_last10,
           AVG(CASE WHEN rn <= 5 THEN strike_rate END)    AS sr_last5,
           AVG(strike_rate)                               AS sr_last10,
           SUM(CASE WHEN runs >= 50 THEN 1 ELSE 0 END)    AS scores_50_plus,
           sqrt(AVG(runs * 1.0 * runs) - AVG(runs * 1.0) * AVG(runs * 1.0)) AS std_dev
    FROM recent
    WHERE rn <= 10
    GROUP BY player_id
    HAVING COUNT(*) >= 5
)
SELECT p.full_name,
       ROUND(a.avg_last5, 1)  AS avg_last_5,
       ROUND(a.avg_last10, 1) AS avg_last_10,
       ROUND(a.sr_last5, 1)   AS sr_last_5,
       ROUND(a.sr_last10, 1)  AS sr_last_10,
       CASE WHEN a.sr_last5 > a.sr_last10 THEN 'Rising'
            WHEN a.sr_last5 < a.sr_last10 THEN 'Falling' ELSE 'Flat' END AS sr_trend,
       a.scores_50_plus,
       ROUND(a.std_dev, 1)    AS std_dev,
       ROUND(a.avg_last10 / (a.std_dev + 1), 2) AS consistency_score,   -- mean / spread, higher is steadier
       CASE WHEN a.avg_last5 >= 50 AND a.scores_50_plus >= 3 THEN 'Excellent Form'
            WHEN a.avg_last5 >= 35 THEN 'Good Form'
            WHEN a.avg_last5 >= 20 THEN 'Average Form'
            ELSE 'Poor Form' END AS form_category
FROM agg a
JOIN players p ON p.player_id = a.player_id
ORDER BY a.avg_last5 DESC""",
    },
    {
        "number": 24, "level": "Advanced",
        "title": "Best batting partnerships",
        "question": "Pairs who batted as consecutive batsmen in 5+ partnerships: average runs, 50+ count, highest, success rate; rank them.",
        "sql": f"""
WITH pairs AS (
    SELECT CASE WHEN b1.player_id < b2.player_id THEN b1.player_id ELSE b2.player_id END AS player_a,
           CASE WHEN b1.player_id < b2.player_id THEN b2.player_id ELSE b1.player_id END AS player_b,
           b1.runs + b2.runs AS pair_runs
{_PARTNERSHIP_JOIN}
),
stats AS (
    SELECT player_a, player_b,
           COUNT(*)                                           AS partnerships,
           ROUND(AVG(pair_runs), 1)                           AS avg_runs,
           SUM(CASE WHEN pair_runs > 50 THEN 1 ELSE 0 END)    AS over_50,
           MAX(pair_runs)                                     AS highest,
           ROUND(100.0 * SUM(CASE WHEN pair_runs > 50 THEN 1 ELSE 0 END) / COUNT(*), 1) AS success_rate_pct
    FROM pairs
    GROUP BY player_a, player_b
    HAVING COUNT(*) >= 5
)
SELECT RANK() OVER (ORDER BY s.success_rate_pct DESC, s.avg_runs DESC) AS rank_no,
       pa.full_name AS batsman_1,
       pb.full_name AS batsman_2,
       s.partnerships, s.avg_runs, s.over_50, s.highest, s.success_rate_pct
FROM stats s
JOIN players pa ON pa.player_id = s.player_a
JOIN players pb ON pb.player_id = s.player_b
ORDER BY rank_no
LIMIT 25""",
    },
    {
        "number": 25, "level": "Advanced",
        "title": "Quarterly performance evolution / career phase",
        "question": "Quarterly averages for runs and strike rate, quarter-on-quarter comparison and career phase (min 6 quarters, 3 matches per quarter).",
        "sql": [
            (
                "Career phase summary",
                _Q25_CTE + """,
summary AS (
    SELECT player_id,
           MAX(n_quarters) AS quarters_analysed,
           AVG(CASE WHEN rn <= 3 THEN avg_runs END)               AS early_avg,
           AVG(CASE WHEN rn > n_quarters - 3 THEN avg_runs END)   AS recent_avg,
           SUM(CASE WHEN avg_runs > prev_runs * 1.05 THEN 1 ELSE 0 END) AS improving_quarters,
           SUM(CASE WHEN avg_runs < prev_runs * 0.95 THEN 1 ELSE 0 END) AS declining_quarters
    FROM trend
    WHERE n_quarters >= 6
    GROUP BY player_id
)
SELECT p.full_name,
       s.quarters_analysed,
       ROUND(s.early_avg, 1)  AS first_3_qtr_avg,
       ROUND(s.recent_avg, 1) AS last_3_qtr_avg,
       s.improving_quarters,
       s.declining_quarters,
       CASE WHEN s.recent_avg > s.early_avg * 1.10 THEN 'Career Ascending'
            WHEN s.recent_avg < s.early_avg * 0.90 THEN 'Career Declining'
            ELSE 'Career Stable' END AS career_phase
FROM summary s
JOIN players p ON p.player_id = s.player_id
ORDER BY s.recent_avg - s.early_avg DESC""",
            ),
            (
                "Quarter-by-quarter detail",
                _Q25_CTE + """
SELECT p.full_name,
       t.quarter,
       t.matches,
       ROUND(t.avg_runs, 1) AS avg_runs,
       ROUND(t.avg_sr, 1)   AS avg_strike_rate,
       ROUND(t.prev_runs, 1) AS prev_quarter_runs,
       CASE WHEN t.prev_runs IS NULL THEN 'n/a'
            WHEN t.avg_runs > t.prev_runs * 1.05 THEN 'Improving'
            WHEN t.avg_runs < t.prev_runs * 0.95 THEN 'Declining'
            ELSE 'Stable' END AS vs_previous_quarter
FROM trend t
JOIN players p ON p.player_id = t.player_id
WHERE t.n_quarters >= 6
ORDER BY p.full_name, t.quarter""",
            ),
        ],
    },
]


def get_query_parts(query: dict) -> list[tuple[str, str]]:
    """Normalise ``sql`` into a list of (label, sql) tuples."""
    sql = query["sql"]
    if isinstance(sql, str):
        return [("Result", sql.strip())]
    return [(label, text.strip()) for label, text in sql]
