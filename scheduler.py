import random
import requests
import pytz
from datetime import date, datetime, timedelta
from db import (
    insert_game, update_kalshi_ticker, update_closing_lines,
    update_final_score, get_games_needing_lines, get_games_needing_settlement
)

EASTERN = pytz.timezone("America/New_York")

# Note: In production these would be stored as environment variables.
BALLDONTLIE_API_KEY = "85b6f5d0-14f2-41b4-969e-be6844267348"
BALLDONTLIE_BASE = "https://api.balldontlie.io"
BALLDONTLIE_HEADERS = {"Authorization": BALLDONTLIE_API_KEY}

# Kalshi API configuration
# In production, individual game spread and total markets would be
# fetched from the Kalshi authenticated API using RSA key authentication.
# Sample data is used here for demonstration purposes.
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_API_KEY_ID = "YOUR_KALSHI_API_KEY_ID"


# ─────────────────────────────────────────────
# JOB 1: Pull today's NBA schedule at 9AM ET
# ─────────────────────────────────────────────
def job_pull_schedule():
    today = date.today().isoformat()
    print(f"[SCHEDULER] Running schedule job for {today}")

    try:
        response = requests.get(
            f"{BALLDONTLIE_BASE}/nba/v1/games",
            headers=BALLDONTLIE_HEADERS,
            params={"dates[]": today},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        games = data.get("data", [])
        print(f"[SCHEDULER] Found {len(games)} games for {today}")

        for game in games:
            home = game["home_team"]["full_name"]
            away = game["visitor_team"]["full_name"]
            bdl_id = game["id"]
            start_time = game.get("status", "")

            if "T" in str(start_time):
                try:
                    utc_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    et_time = utc_time.astimezone(EASTERN)
                    start_time = et_time.strftime("%I:%M %p ET")
                except Exception:
                    pass

            insert_game(home, away, today, start_time, bdl_id)
            print(f"[SCHEDULER] Stored: {away} @ {home} ({start_time})")

            ticker = find_kalshi_ticker(home, away)
            update_kalshi_ticker(bdl_id, ticker)
            print(f"[SCHEDULER] Ticker assigned: {ticker}")

    except Exception as e:
        print(f"[SCHEDULER] ERROR in schedule job: {e}")


# ─────────────────────────────────────────────
# KALSHI TICKER MATCHING
# In production this would search the Kalshi API for matching
# NBA game events using authenticated requests.
# ─────────────────────────────────────────────
def find_kalshi_ticker(home_team, away_team):
    home_abbr = home_team.split()[-1][:3].upper()
    away_abbr = away_team.split()[-1][:3].upper()
    ticker = f"KXNBA-{away_abbr}-{home_abbr}"
    print(f"[KALSHI] Sample ticker generated: {ticker}")
    return ticker


# ─────────────────────────────────────────────
# JOB 2: Pull closing lines every 5 minutes
# ─────────────────────────────────────────────
def job_pull_closing_lines():
    print("[SCHEDULER] Running closing lines job")
    games = get_games_needing_lines()

    if not games:
        print("[SCHEDULER] No games needing lines")
        return

    for game in games:
        ticker = game.get("kalshi_event_ticker")
        if not ticker:
            continue
        try:
            spread, total = get_kalshi_lines(ticker, game["home_team"], game["away_team"])
            if spread is not None or total is not None:
                update_closing_lines(game["balldontlie_game_id"], spread, total)
                print(f"[SCHEDULER] Lines stored for {game['away_team']} @ {game['home_team']}: spread={spread}, total={total}")
        except Exception as e:
            print(f"[SCHEDULER] Error pulling lines for {ticker}: {e}")


# ─────────────────────────────────────────────
# KALSHI LINES
# In production this would call the Kalshi authenticated API
# to fetch the spread and total contracts closest to 50/50
# for the given event ticker.
# Sample data is structured to mirror real Kalshi market responses.
# ─────────────────────────────────────────────
def get_kalshi_lines(event_ticker, home_team, away_team):
    print(f"[KALSHI] Fetching sample market data for {event_ticker}")

    spreads = [-1.5, -2.5, -3.5, -4.5, -5.5, -6.5, -7.5]
    totals = [214.5, 217.5, 220.5, 223.5, 226.5, 229.5, 232.5]

    spread = random.choice(spreads)
    total = random.choice(totals)

    print(f"[KALSHI] Sample data — spread: {spread}, total: {total}")
    return spread, total


# ─────────────────────────────────────────────
# JOB 3: Settle yesterday's games at 3AM ET
# ─────────────────────────────────────────────
def job_settle_games():
    print("[SCHEDULER] Running settlement job")
    games = get_games_needing_settlement()

    if not games:
        print("[SCHEDULER] No games to settle")
        return

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    try:
        response = requests.get(
            f"{BALLDONTLIE_BASE}/nba/v1/games",
            headers=BALLDONTLIE_HEADERS,
            params={"dates[]": yesterday},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        bdl_games = {g["id"]: g for g in data.get("data", [])}

        for game in games:
            bdl_id = game["balldontlie_game_id"]
            bdl_game = bdl_games.get(bdl_id)

            if not bdl_game:
                print(f"[SCHEDULER] Game {bdl_id} not found in BALLDONTLIE response")
                continue

            if bdl_game.get("status") != "Final":
                print(f"[SCHEDULER] Game {bdl_id} not final yet: {bdl_game.get('status')}")
                continue

            home_score = bdl_game["home_team_score"]
            away_score = bdl_game["visitor_team_score"]

            spread_result = None
            if game["closing_spread"] is not None:
                margin = home_score - away_score
                spread = game["closing_spread"]
                if margin > spread:
                    spread_result = "HOME COVERS"
                elif margin < spread:
                    spread_result = "AWAY COVERS"
                else:
                    spread_result = "PUSH"

            total_result = None
            if game["closing_total"] is not None:
                combined = home_score + away_score
                total = game["closing_total"]
                if combined > total:
                    total_result = "OVER"
                elif combined < total:
                    total_result = "UNDER"
                else:
                    total_result = "PUSH"

            update_final_score(bdl_id, home_score, away_score, spread_result, total_result)
            print(f"[SCHEDULER] Settled: {game['away_team']} @ {game['home_team']} | {away_score}-{home_score} | Spread: {spread_result} | Total: {total_result}")

    except Exception as e:
        print(f"[SCHEDULER] ERROR in settlement job: {e}")