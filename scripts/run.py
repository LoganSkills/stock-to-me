#!/usr/bin/env python3
"""
Daily Runner — executes the full Phase 1 data pipeline in order.

Usage:
  python scripts/run.py               # full pipeline (seed → market data → filings → financials → scores)
  python scripts/run.py --phase 1    # same as above
  python scripts/run.py --phase 2    # filings + scores only (already seeded)
  python scripts/run.py --ticker ZD   # single ticker through full pipeline
"""

import asyncio
import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from scripts.seed_universe import seed_universe
from scripts.sync_market_data import sync_market_data
from scripts.run_filing_scan import run_filing_scan
from scripts.run_financial_scan import run_financial_scan
from scripts.run_score_pipeline import run_score_pipeline

cli = typer.Typer()


@cli.command()
def main(
    phase: int = typer.Option(1, help="Phase to run: 1 = seed+sync, 2 = filings+scores, 3 = all"),
    ticker: str | None = typer.Option(None, help="Single ticker to process (all phases)"),
    test: bool = typer.Option(False, help="Test mode — seed only 10 companies"),
    dry_run: bool = typer.Option(False, help="Dry run for score pipeline"),
):
    """Run the daily data pipeline."""
    print()
    print("=" * 60)
    print("STOCK TO ME — DAILY PIPELINE")
    print("=" * 60)
    print(f"  Phase: {phase}  |  Ticker: {ticker or 'all'}  |  Test: {test}")
    print("=" * 60)
    print()

    if phase >= 1:
        print("\n📦 PHASE 1: Seed Universe + Market Data\n")
        result = asyncio.run(seed_universe(test_mode=test))
        if ticker:
            asyncio.run(sync_market_data())
        elif result.get("seeded", 0) > 0 or not test:
            asyncio.run(sync_market_data())

    if phase >= 2:
        print("\n📦 PHASE 2: SEC Filings + Financial Snapshots\n")
        asyncio.run(run_filing_scan(days_back=30, ticker=ticker))
        asyncio.run(run_financial_scan(ticker=ticker))

    if phase >= 3:
        print("\n📦 PHASE 3: Scoring + AI Summaries + Alerts\n")
        asyncio.run(run_score_pipeline(ticker=ticker, dry_run=dry_run))

    print("\n✅ Pipeline complete!")
    print("  Check the dashboard at http://localhost:3000")


@cli.command()
def seed_only(test: bool = False):
    """Seed universe only."""
    asyncio.run(seed_universe(test_mode=test))


@cli.command()
def score_only(ticker: str | None = None, dry_run: bool = False):
    """Run score pipeline only."""
    asyncio.run(run_score_pipeline(ticker=ticker, dry_run=dry_run))


if __name__ == "__main__":
    cli()
