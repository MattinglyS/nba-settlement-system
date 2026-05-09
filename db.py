import sqlite3
from datetime import datetime, date

DB_PATH = "settlement.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            game_date TEXT NOT NULL,
            game_start_time TEXT,
            balldontlie_game_id INTEGER UNIQUE,
            kalshi_event_ticker TEXT,
            closing_spread REAL,
            closing_total REAL,
            home_final_score INTEGER,
            away_final_score INTEGER,
            spread_result TEXT,
            total_result TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database initialized.")


def game_exists_today(game_date):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM games WHERE game_date = ?", (game_date,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def insert_game(home_team, away_team, game_date, game_start_time, balldontlie_game_id):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO games 
            (home_team, away_team, game_date, game_start_time, balldontlie_game_id, status)
            VALUES (?, ?, ?, ?, ?, 'scheduled')
        """, (home_team, away_team, game_date, game_start_time, balldontlie_game_id))
        conn.commit()
    except Exception as e:
        print(f"[DB] Error inserting game: {e}")
    finally:
        conn.close()


def update_kalshi_ticker(balldontlie_game_id, ticker):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE games SET kalshi_event_ticker = ?
        WHERE balldontlie_game_id = ?
    """, (ticker, balldontlie_game_id))
    conn.commit()
    conn.close()


def update_closing_lines(balldontlie_game_id, spread, total):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE games SET closing_spread = ?, closing_total = ?
        WHERE balldontlie_game_id = ?
    """, (spread, total, balldontlie_game_id))
    conn.commit()
    conn.close()


def update_final_score(balldontlie_game_id, home_score, away_score, spread_result, total_result):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE games 
        SET home_final_score = ?, away_final_score = ?,
            spread_result = ?, total_result = ?, status = 'final'
        WHERE balldontlie_game_id = ?
    """, (home_score, away_score, spread_result, total_result, balldontlie_game_id))
    conn.commit()
    conn.close()


def get_recent_settled_games(days=3):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM games 
        WHERE status = 'final'
        AND game_date >= date('now', ?)
        ORDER BY game_date DESC, game_start_time DESC
    """, (f'-{days} days',))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_todays_upcoming_games():
    conn = get_conn()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        SELECT * FROM games
        WHERE game_date = ? AND status IN ('scheduled', 'live')
        ORDER BY game_start_time
    """, (today,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_games_needing_lines():
    conn = get_conn()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        SELECT * FROM games
        WHERE game_date = ?
        AND kalshi_event_ticker IS NOT NULL
        AND closing_spread IS NULL
        AND status = 'scheduled'
    """, (today,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_games_needing_settlement():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM games
        WHERE game_date = date('now', '-1 day')
        AND status != 'final'
        AND balldontlie_game_id IS NOT NULL
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows