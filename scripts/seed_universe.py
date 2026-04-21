"""
Universe Seeder — loads and updates the stock universe from free public sources.

Data sources:
  - SEC EDGAR company JSON (CIK → company info, no registration needed)
  - Yahoo Finance (yfinance) for market data (no API key needed)
  - NASDAQ / NYSE public stock list CSVs

Usage:
  python scripts/seed_universe.py          # full refresh
  python scripts/seed_universe.py --test  # just 10 tickers for dev
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yfinance as yf
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal, engine
from app.core.config import get_settings
from app.models.models import Company

settings = get_settings()

# Market cap bounds (per spec)
MIN_CAP = settings.MIN_MARKET_CAP   # $10M
MAX_CAP = settings.MAX_MARKET_CAP   # $750M


# ─── SEC EDGAR helpers ──────────────────────────────────────────────────────────


async def fetch_edgar_company_list() -> list[dict]:
    """Download the SEC EDGAR company JSON and return a list of {cik, name, ...}."""
    url = "https://www.sec.gov/files/company_tickers.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        doc = await client.get(url, headers={"User-Agent": "Stock To Me bot agent@openclaw.ai"})
        doc.raise_for_status()
        data = doc.json()

    # Format: {"001":{"cik":"0000012345","name":"Example Inc","ticker":"EXMP"}}
    companies = []
    for entry in data.values():
        companies.append({
            "cik": entry["cik"].lstrip("0"),
            "ticker": entry["ticker"],
            "name": entry["name"],
        })
    return companies


async def enrich_with_edgar_submissions(company: dict) -> dict:
    """Fetch EDGAR submission index for a single CIK to get exchange + sic."""
    cik = company["cik"].zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        doc = await client.get(url, headers={"User-Agent": "Stock To Me bot agent@openclaw.ai"})
        if doc.status_code != 200:
            return company
        data = doc.json()

    company["exchange"] = data.get("exchanges", ["UNKNOWN"])[0] if data.get("exchanges") else "UNKNOWN"
    company["sic"] = data.get("sic")
    company["sic_description"] = data.get("sicDescription", "")
    company["state_of_inc"] = data.get("stateOfIncorporation", "")
    return company


# ─── Yahoo Finance helpers ──────────────────────────────────────────────────────


def fetch_yahoo_data(ticker: str) -> dict | None:
    """Fetch market cap, price, shares, avg volume from Yahoo Finance."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        if not info or info.get("regularMarketPrice") is None:
            return None

        market_cap = info.get("marketCap")
        if market_cap and (market_cap < MIN_CAP or market_cap > MAX_CAP):
            return None  # outside universe bounds

        return {
            "market_cap": market_cap,
            "current_price": info.get("regularMarketPrice"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "avg_volume_20d": info.get("averageVolume20days"),
            "exchange": info.get("exchange"),
            "sector": info.get("sector") or None,
            "industry": info.get("industry") or None,
        }
    except Exception:
        return None


# ─── Main seeder ───────────────────────────────────────────────────────────────


async def seed_universe(test_mode: bool = False, batch_size: int = 10) -> dict:
    """
    Main seeder function.

    1. Fetch list of all SEC-registered tickers
    2. Filter by market cap bounds using Yahoo Finance
    3. Insert / update companies in the database
    """
    print("=" * 60)
    print("UNIVERSE SEEDER — Starting")
    print("=" * 60)

    # Step 1: Get the full EDGAR company list
    print("\n📡 Fetching SEC EDGAR company list...")
    edgar_companies = await fetch_edgar_company_list()
    print(f"   Found {len(edgar_companies):,} companies in EDGAR registry")

    # Step 2: Load existing tickers from DB (to skip already-seeded)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Company.ticker).where(Company.is_active == True))
        existing_tickers = set(result.scalars().all())
        print(f"   {len(existing_tickers):,} already in database — will skip")

    # Step 3: Filter candidates
    candidates = [c for c in edgar_companies if c["ticker"] and c["ticker"] not in existing_tickers]
    print(f"   {len(candidates):,} new candidates to evaluate")

    if test_mode:
        candidates = candidates[:batch_size]
        print(f"   [TEST MODE] Limited to {batch_size} tickers")

    if not candidates:
        print("   Nothing new to seed.")
        return {"status": "ok", "seeded": 0, "skipped": 0}

    # Step 4: Fetch Yahoo Finance data for candidates
    print(f"\n🔍 Fetching Yahoo Finance data for {len(candidates):,} candidates...")
    seeded = 0
    skipped_cap = 0
    errors = 0

    async with AsyncSessionLocal() as session:
        for i, cand in enumerate(candidates):
            ticker = cand["ticker"]

            # Progress every 100
            if (i + 1) % 100 == 0:
                print(f"   ... {i+1}/{len(candidates)} processed ({seeded} seeded)")

            try:
                yf_data = await asyncio.to_thread(fetch_yahoo_data, ticker)
                if yf_data is None:
                    skipped_cap += 1
                    continue

                # Map exchange name
                exchange = yf_data.get("exchange", "UNKNOWN")
                if exchange == "USA": exchange = "NASDAQ"
                elif exchange == "USA": exchange = "NYSE"

                company = Company(
                    ticker=ticker,
                    cik=cand["cik"],
                    name=cand["name"],
                    exchange=exchange or "UNKNOWN",
                    sector=yf_data.get("sector"),
                    industry=yf_data.get("industry"),
                    market_cap=yf_data.get("market_cap"),
                    current_price=yf_data.get("current_price"),
                    float_shares=yf_data.get("float_shares"),
                    shares_outstanding=yf_data.get("shares_outstanding"),
                    avg_volume_20d=yf_data.get("avg_volume_20d"),
                    is_active=True,
                )
                session.add(company)
                seeded += 1

                # Commit in batches
                if seeded % 200 == 0:
                    await session.commit()
                    print(f"   ✓ {seeded} companies committed")

            except Exception as e:
                errors += 1
                continue

        await session.commit()

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  ✅ Seeded:    {seeded}")
    print(f"  ⏭️  Skipped (cap): {skipped_cap}")
    print(f"  ❌ Errors:   {errors}")
    print("=" * 60)

    return {"status": "ok", "seeded": seeded, "skipped_cap": skipped_cap, "errors": errors}


# ─── CLI ───────────────────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed stock universe")
    parser.add_argument("--test", action="store_true", help="Test mode — seed only 10 companies")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for test mode")
    args = parser.parse_args()

    asyncio.run(seed_universe(test_mode=args.test, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
