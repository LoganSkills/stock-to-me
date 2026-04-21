"""
Daily Market Data Sync — fetches end-of-day OHLCV for all active companies.

Uses Yahoo Finance (yfinance) — no API key required.

Usage:
  python scripts/sync_market_data.py           # full sync
  python scripts/sync_market_data.py --days 5  # last 5 trading days
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import yfinance as yf
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.models import Company, MarketDataDaily


def fetch_ohlcv(ticker: str, days: int = 30) -> list[dict]:
    """Fetch OHLCV data from Yahoo Finance for the last N trading days."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=f"{days}d", auto_adjust=True)
        if hist.empty:
            return []
        records = []
        for ts, row in hist.iterrows():
            records.append({
                "date": ts.date() if hasattr(ts, "date") else ts,
                "open": float(row["Open"]) if row["Open"] else None,
                "high": float(row["High"]) if row["High"] else None,
                "low": float(row["Low"]) if row["Low"] else None,
                "close": float(row["Close"]) if row["Close"] else None,
                "volume": int(row["Volume"]) if row["Volume"] else None,
            })
        return records
    except Exception:
        return []


def calc_relative_volumes(records: list[dict]) -> list[dict]:
    """Add rel_volume_5d and rel_volume_20d to each record."""
    if len(records) < 5:
        for r in records:
            r["rel_volume_5d"] = None
            r["rel_volume_20d"] = None
        return records

    avg_5d = sum(r["volume"] for r in records[:5] if r["volume"]) / 5
    avg_20d = sum(r["volume"] for r in records[:20] if r["volume"]) / min(len(records), 20) if records else 1

    for r in records:
        if r["volume"] and avg_5d > 0:
            r["rel_volume_5d"] = round(r["volume"] / avg_5d, 2)
        else:
            r["rel_volume_5d"] = None

        if r["volume"] and avg_20d > 0:
            r["rel_volume_20d"] = round(r["volume"] / avg_20d, 2)
        else:
            r["rel_volume_20d"] = None

    return records


def calc_returns(records: list[dict]) -> list[dict]:
    """Add 1d, 3d, 5d returns to each record."""
    closes = [r["close"] for r in records if r["close"]]
    closes.reverse()  # oldest first

    for i, r in enumerate(records):
        r["return_1d"] = None
        r["return_3d"] = None
        r["return_5d"] = None

        if not r["close"] or i >= len(closes) - 1:
            continue

        prev = closes[i + 1] if i + 1 < len(closes) else None
        prev3 = closes[i + 3] if i + 3 < len(closes) else None
        prev5 = closes[i + 5] if i + 5 < len(closes) else None

        if prev and prev > 0:
            r["return_1d"] = round(((r["close"] - prev) / prev) * 100, 4)
        if prev3 and prev3 > 0:
            r["return_3d"] = round(((r["close"] - prev3) / prev3) * 100, 4)
        if prev5 and prev5 > 0:
            r["return_5d"] = round(((r["close"] - prev5) / prev5) * 100, 4)

    return records


async def sync_market_data(days: int = 30, batch_size: int = 50) -> dict:
    """Sync market data for all active companies."""
    print("=" * 60)
    print("MARKET DATA SYNC")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.is_active == True)
        )
        companies = result.scalars().all()
        print(f"\n📡 {len(companies):,} active companies to sync")

    processed = 0
    errors = 0
    no_data = 0

    for i, company in enumerate(companies):
        ticker = company.ticker

        if (i + 1) % batch_size == 0:
            print(f"   ... {i+1}/{len(companies)} processed")

        try:
            records = await asyncio.to_thread(fetch_ohlcv, ticker, days)
            if not records:
                no_data += 1
                continue

            records = calc_relative_volumes(records)
            records = calc_returns(records)

            async with AsyncSessionLocal() as session:
                for r in records:
                    # Check if already exists
                    existing = await session.execute(
                        select(MarketDataDaily).where(
                            MarketDataDaily.company_id == company.id,
                            MarketDataDaily.date == r["date"],
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # skip already stored

                    mkt = MarketDataDaily(
                        company_id=company.id,
                        date=r["date"],
                        open=r["open"],
                        high=r["high"],
                        low=r["low"],
                        close=r["close"],
                        volume=r["volume"],
                        rel_volume_5d=r["rel_volume_5d"],
                        rel_volume_20d=r["rel_volume_20d"],
                        return_1d=r["return_1d"],
                        return_3d=r["return_3d"],
                        return_5d=r["return_5d"],
                    )
                    session.add(mkt)

                await session.commit()
                processed += 1

        except Exception as e:
            errors += 1
            continue

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print(f"  ✅ Processed: {processed}")
    print(f"  ⏭️  No data:  {no_data}")
    print(f"  ❌ Errors:    {errors}")
    print("=" * 60)

    return {"processed": processed, "no_data": no_data, "errors": errors}


# ─── CLI ───────────────────────────────────────────────────────────────────────

import asyncio

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30, help="Days of history to fetch")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(sync_market_data(days=args.days, batch_size=args.batch_size))

if __name__ == "__main__":
    main()
