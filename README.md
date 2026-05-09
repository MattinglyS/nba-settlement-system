# NBA Settlement System
### Author: Mattingly Siegel

A locally hosted web application that tracks, grades, and displays NBA prediction market settlement data in real time. Built as preparation for a role in prediction market operations at a CFTC-regulated derivatives exchange.

## How It Works

The system runs three automated jobs:

- **9:00 AM ET daily** — Pulls today's NBA schedule from BALLDONTLIE and assigns Kalshi market tickers to each game
- **Every 5 minutes** — Fetches closing spread and total lines from Kalshi for each game
- **3:00 AM ET daily** — Pulls final scores from BALLDONTLIE and settles all contracts

The dashboard auto-refreshes every 60 seconds and displays settled contracts from the last 3 days alongside today's upcoming games.

## Settlement Logic

- **Spread** (home team perspective): home score minus away score vs closing spread — HOME COVERS / AWAY COVERS / PUSH
- **Total**: home score plus away score vs closing total — OVER / UNDER / PUSH

## How To Run

Step 1 — Install required libraries:

pip install flask apscheduler requests pytz

Step 2 — Add your API keys in scheduler.py:
- BALLDONTLIE API key — free at app.balldontlie.io
- Kalshi API key — free at kalshi.com

Step 3 — Run the application:

python app.py

Step 4 — Open your browser:

http://localhost:8080

## Data Sources
- **BALLDONTLIE API** — NBA schedule and final scores
- **Kalshi API** — CFTC-regulated prediction market spread and total contracts

## Tech Stack
- Python / Flask — web server and API routes
- SQLite — local database for storing contracts and settlement results
- APScheduler — automated scheduling of data jobs
- HTML / CSS / JavaScript — auto-refreshing dashboard UI

## Files
- `app.py` — Flask application, routes, and scheduler setup
- `db.py` — SQLite database module
- `scheduler.py` — automated job functions
- `templates/index.html` — dashboard UI

## Notes
- API keys are stored as variables in scheduler.py. In production these would be stored as environment variables.
- Kalshi individual game market data requires authenticated API access. Sample data structured to mirror real Kalshi NBA market responses is used here for demonstration.
- The database (settlement.db) is created automatically on first run and is not tracked in version control.

## Related
This project is a rebuild of an earlier sandbox version built to learn the stack:
https://github.com/MattinglyS/sports-market-settlement-system