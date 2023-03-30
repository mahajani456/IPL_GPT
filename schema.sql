DROP TABLE IF EXISTS match_ball_by_ball;

CREATE TABLE match_ball_by_ball (
    match_id INTEGER,
    season INTEGER,
    start_date TEXT,
    venue TEXT,
    innings INTEGER,
    ball REAL,
    batting_team TEXT,
    bowling_team TEXT,
    striker TEXT,
    non_striker TEXT,
    bowler TEXT,
    runs_off_bat INTEGER,
    extras INTEGER,
    wides INTEGER,
    noballs INTEGER,
    byes INTEGER,
    legbyes INTEGER,
    penalty INTEGER,
    wicket_type TEXT,
    player_dismissed TEXT,
    other_wicket_type TEXT,
    other_player_dismissed TEXT
);

DROP TABLE IF EXISTS match_info;

CREATE TABLE match_info (
    match_id INTEGER PRIMARY KEY,
    season INTEGER,
    date TEXT,
    city TEXT,
    venue TEXT,
    team1 TEXT,
    team2 TEXT,
    toss_winner TEXT,
    toss_decision TEXT,
    player_of_match TEXT,
    winner TEXT,
    winner_wickets INTEGER,
    winner_runs INTEGER,
    outcome TEXT,
    result_type TEXT,
    results TEXT,
    gender TEXT,
    event TEXT,
    match_number INTEGER,
    umpire1 TEXT,
    umpire2 TEXT,
    reserve_umpire TEXT,
    tv_umpire TEXT,
    match_referee TEXT,
    eliminator TEXT,
    method TEXT,
    date_1 TEXT
);

DROP TABLE IF EXISTS query_history;

CREATE TABLE query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    query_count INTEGER NOT NULL DEFAULT 1
);