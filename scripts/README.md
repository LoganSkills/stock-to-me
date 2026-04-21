# Stock To Me — Operational Scripts

All scripts are run from the `stock-to-me/` root directory.

```bash
# Full daily pipeline (Phase 1 → 2 → 3)
python scripts/run.py

# Seed universe + market data (first time only)
python scripts/run.py --phase 1

# SEC filings + financial snapshots
python scripts/run.py --phase 2

# Scoring + AI summaries + alerts
python scripts/run.py --phase 3

# Single ticker through full pipeline
python scripts/run.py --ticker ZD

# Test mode (seeds only 10 companies)
python scripts/run.py --test

# Individual scripts
python scripts/seed_universe.py --test           # seed 10 test companies
python scripts/sync_market_data.py --days 30     # fetch OHLCV data
python scripts/run_filing_scan.py --days 7       # ingest recent filings
python scripts/run_financial_scan.py            # parse 10-Q/10-K financials
python scripts/run_score_pipeline.py --dry-run   # compute scores (dry run)
python scripts/run_score_pipeline.py --ticker ZD # score single ticker

# Mission Control (live office floor backend)
python scripts/mission_control_server.py
```

## Prerequisites

```bash
# Install dependencies
pip install -r backend/requirements.txt
pip install yfinance httpx typer

# Start Postgres + Redis
docker compose up -d

# Apply database migrations
cd backend && alembic upgrade head
```
