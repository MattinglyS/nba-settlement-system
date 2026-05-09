from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime, date
from db import (
    init_db, game_exists_today,
    get_recent_settled_games, get_todays_upcoming_games
)
from scheduler import job_pull_schedule, job_pull_closing_lines, job_settle_games

app = Flask(__name__)
EASTERN = pytz.timezone("America/New_York")


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    settled = get_recent_settled_games(days=3)
    upcoming = get_todays_upcoming_games()
    now_et = datetime.now(EASTERN)

    return jsonify({
        "settled": settled,
        "upcoming": upcoming,
        "last_updated": now_et.strftime("%B %d, %Y at %I:%M %p ET")
    })


# ─────────────────────────────────────────────
# SCHEDULER SETUP
# ─────────────────────────────────────────────
def setup_scheduler():
    scheduler = BackgroundScheduler(timezone=EASTERN)

    # Job 1: Pull NBA schedule every day at 9AM ET
    scheduler.add_job(
        job_pull_schedule,
        CronTrigger(hour=9, minute=0, timezone=EASTERN),
        id="pull_schedule",
        name="Pull NBA Schedule"
    )

    # Job 2: Pull closing lines every 5 minutes
    scheduler.add_job(
        job_pull_closing_lines,
        "interval",
        minutes=5,
        id="pull_closing_lines",
        name="Pull Closing Lines"
    )

    # Job 3: Settle yesterday's games at 3AM ET
    scheduler.add_job(
        job_settle_games,
        CronTrigger(hour=3, minute=0, timezone=EASTERN),
        id="settle_games",
        name="Settle Games"
    )

    scheduler.start()
    print("\n[SCHEDULER] Jobs scheduled:")
    print("  → 9:00 AM ET daily  — Pull NBA schedule")
    print("  → Every 5 minutes   — Pull closing lines")
    print("  → 3:00 AM ET daily  — Settle yesterday's games")
    return scheduler


# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────
def on_startup():
    init_db()
    today = date.today().isoformat()

    if not game_exists_today(today):
        print(f"\n[STARTUP] No games found for {today} — running schedule job now...")
        job_pull_schedule()
    else:
        print(f"\n[STARTUP] Games already loaded for {today}")

    job_pull_closing_lines()


if __name__ == "__main__":
    print("=" * 55)
    print("  NBA SETTLEMENT SYSTEM")
    print("  Starting up...")
    print("=" * 55)

    on_startup()
    scheduler = setup_scheduler()

    print("\n[APP] Running at http://localhost:8080")
    print("[APP] Press CTRL+C to stop\n")

    app.run(host="0.0.0.0", port=8080, debug=False)