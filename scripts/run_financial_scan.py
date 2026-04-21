"""
Financial Snapshot Runner — extracts cash, debt, revenue, burn from 10-Q/10-K filings.

Parses the raw filing text (already stored by run_filing_scan.py) to extract
key financial items, and stores them as FinancialSnapshot records.

Usage:
  python scripts/run_financial_scan.py         # scan all companies
  python scripts/run_financial_scan.py --ticker ZD  # single company
"""

import asyncio
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.models import Company, Filing, FinancialSnapshot


FINANCIAL_PATTERNS = {
    # Cash
    "cash_and_equivalents": [
        re.compile(r"cash and cash equivalents[\r\n\s]*\$\s*([\d,]+)", re.I),
        re.compile(r"cash and equivalents[\r\n\s]*\$\s*([\d,]+)", re.I),
        re.compile(r"cash\s+at\s+end\s+of\s+period[\r\n\s]*\$\s*([\d,]+)", re.I),
    ],
    # Total debt
    "total_debt": [
        re.compile(r"total debt[\r\n\s]*\$?\s*([\d,]+)", re.I),
        re.compile(r"long[\- ]term debt[\r\n\s]*\$?\s*([\d,]+)", re.I),
        re.compile(r"short[\- ]term borrowings[\r\n\s]*\$?\s*([\d,]+)", re.I),
    ],
    # Revenue
    "revenue": [
        re.compile(r"revenue[\r\n\s]*\$?\s*([\d,]+)", re.I),
        re.compile(r"net sales[\r\n\s]*\$?\s*([\d,]+)", re.I),
        re.compile(r"total revenues?[\r\n\s]*\$?\s*([\d,]+)", re.I),
    ],
    # Operating cash flow
    "op_cash_flow": [
        re.compile(r"net cash[\r\n\s]*(?:provided|used)[\r\n\s]*(?:by|from)[\r\n\s]*operations?[\r\n\s]*\$?\s*([\d,()\-]+)", re.I),
        re.compile(r"cash flows?[\r\n\s]*from[\r\n\s]*operations?[\r\n\s]*\$?\s*([\d,()\-]+)", re.I),
    ],
    # Net loss
    "net_loss": [
        re.compile(r"net loss[\r\n\s]*\$?\s*([\d,()\-]+)", re.I),
        re.compile(r"net income[\r\n\s]*\$?\s*([\d,()\-]+)", re.I),
        re.compile(r"net loss[\r\n\s]*\(?\s*([\d,.]+)\s*\)", re.I),
    ],
    # Going concern
    "going_concern": [
        re.compile(r"going concern", re.I),
        re.compile(r"substantial doubt", re.I),
        re.compile(r"may not continue as a going concern", re.I),
    ],
}


def extract_number(text: str, patterns: list[re.Pattern]) -> int | None:
    """Run a list of regex patterns against text; return first match as int."""
    for p in patterns:
        m = p.search(text[:200_000])  # first 200k chars
        if m:
            val = m.group(1).replace(",", "").replace("(", "-").replace(")", "")
            try:
                return int(float(val))
            except ValueError:
                pass
    return None


def extract_financials(filing: Filing) -> dict:
    """Extract all financial items from a filing's raw text."""
    if not filing.raw_text:
        return {}

    text = filing.raw_text[:200_000]
    result = {}

    for field, patterns in FINANCIAL_PATTERNS.items():
        value = extract_number(text, patterns)
        result[field] = value

    return result


async def run_financial_scan(ticker: str | None = None) -> dict:
    """Scan 10-Q/10-K filings and store financial snapshots."""
    print("=" * 60)
    print("FINANCIAL SNAPSHOT SCAN")
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

    processed = 0
    snapshots = 0
    errors = 0

    for i, company in enumerate(companies):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Filing)
                .where(Filing.company_id == company.id)
                .where(Filing.filing_type.in_(["10-Q", "10-K"]))
                .where(Filing.raw_text.isnot(None))
                .order_by(Filing.filed_at.desc())
                .limit(2)
            )
            filings = result.scalars().all()

        if not filings:
            continue

        for filing in filings:
            # Check if snapshot already exists
            async with AsyncSessionLocal() as session:
                existing = await session.execute(
                    select(FinancialSnapshot).where(
                        FinancialSnapshot.company_id == company.id,
                        FinancialSnapshot.period_end == filing.filed_at.date(),
                        FinancialSnapshot.report_type == filing.filing_type,
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # already have this period

            data = extract_financials(filing)

            async with AsyncSessionLocal() as session:
                snapshot = FinancialSnapshot(
                    company_id=company.id,
                    period_end=filing.filed_at.date(),
                    report_type=filing.filing_type,
                    cash_and_equivalents=data.get("cash_and_equivalents"),
                    total_debt=data.get("total_debt"),
                    revenue=data.get("revenue"),
                    op_cash_flow=data.get("op_cash_flow"),
                    net_loss=data.get("net_loss"),
                    going_concern_flag=data.get("going_concern") is not None,
                )
                session.add(snapshot)
                await session.commit()
                snapshots += 1

        processed += 1
        if (i + 1) % 100 == 0:
            print(f"   ... {i+1}/{len(companies)} processed ({snapshots} snapshots stored)")

    print("\n" + "=" * 60)
    print("FINANCIAL SCAN COMPLETE")
    print(f"  ✅ Companies processed:  {processed}")
    print(f"  📊 Snapshots stored:      {snapshots}")
    print(f"  ❌ Errors:               {errors}")
    print("=" * 60)

    return {"processed": processed, "snapshots": snapshots, "errors": errors}


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default=None)
    args = parser.parse_args()
    asyncio.run(run_financial_scan(ticker=args.ticker))

if __name__ == "__main__":
    main()
