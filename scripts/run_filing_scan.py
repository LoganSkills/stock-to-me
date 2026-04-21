"""
SEC Bulk Filing Runner — ingests recent SEC filings for all active companies.

Fetches filings from EDGAR (public, no registration needed) and stores
them in the database. Designed to run daily or more frequently.

Usage:
  python scripts/run_filing_scan.py            # full scan
  python scripts/run_filing_scan.py --days 7  # last 7 days only
  python scripts/run_filing_scan.py --ticker ZD --days 30  # single ticker
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.models import Company
from app.services.edgar_service import ingest_company_filings


async def run_filing_scan(
    days_back: int = 7,
    ticker: str | None = None,
    batch_size: int = 20,
) -> dict:
    """
    Run the SEC filing scan across all active companies.

    Args:
        days_back: how many days of filings to fetch per company
        ticker: if set, only scan this ticker
        batch_size: pause every N companies to avoid rate limiting
    """
    print("=" * 60)
    print(f"SEC FILING SCAN  (last {days_back} days)" + (f"  — {ticker}" if ticker else ""))
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        if ticker:
            result = await session.execute(
                select(Company).where(Company.ticker == ticker.upper())
            )
        else:
            result = await session.execute(
                select(Company).where(Company.is_active == True)
            )
        companies = result.scalars().all()

    print(f"\n📡 {len(companies):,} companies to scan")
    if not companies:
        print("   Nothing to scan — add companies first with seed_universe.py")
        return {"status": "empty", "scanned": 0}

    scanned = 0
    filings_found = 0
    errors = 0

    for i, company in enumerate(companies):
        if (i + 1) % batch_size == 0:
            print(f"   ... {i+1}/{len(companies)} processed  ({scanned} companies with new filings)")
            await asyncio.sleep(2)  # brief pause to avoid hammering EDGAR

        try:
            async with AsyncSessionLocal() as session:
                new_filings = await ingest_company_filings(
                    company, session, days_back=days_back
                )
                if new_filings:
                    filings_found += len(new_filings)
                    print(
                        f"   ✓ {company.ticker}: {len(new_filings)} new filing(s)"
                        + f" — {[f.filing_type for f in new_filings]}"
                    )
                scanned += 1

        except Exception as e:
            errors += 1
            print(f"   ❌ {company.ticker}: {e}")
            continue

    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print(f"  ✅ Companies scanned:    {scanned}")
    print(f"  📄 New filings stored:   {filings_found}")
    print(f"  ❌ Errors:              {errors}")
    print("=" * 60)

    return {
        "status": "ok",
        "scanned": scanned,
        "filings_found": filings_found,
        "errors": errors,
    }


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--ticker", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(run_filing_scan(days_back=args.days, ticker=args.ticker, batch_size=args.batch_size))

if __name__ == "__main__":
    main()
