"""
Score Pipeline — recomputes all scores for every active company.

This is the main nightly/ondemand job that:
  1. Runs build_score_snapshot() for every company
  2. Generates AI summaries and attaches them to the snapshot
  3. Checks alert thresholds and fires alerts

Usage:
  python scripts/run_score_pipeline.py          # full run
  python scripts/run_score_pipeline.py --ticker ZD  # single ticker
  python scripts/run_score_pipeline.py --dry-run  # show what would run
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.models import Company, Filing, PressRelease, ScoreSnapshot, Alert, AlertType, AlertSeverity
from app.services.scoring_service import build_score_snapshot
from app.services.ai_summary_service import build_stock_summary


ALERT_THRESHOLDS = {
    "trap_score": {
        "watch": 25,
        "elevated": 50,
        "high_risk": 70,
        "severe": 85,
    },
    "dilution_pressure_score": {"caution": 40, "high": 60, "severe": 80},
    "cash_need_score": {"caution": 40, "high": 60, "severe": 80},
}


async def generate_alert(
    company_id: int,
    score: float,
    score_name: str,
    threshold: float,
    severity: str,
    label: str,
    session: AsyncSession,
) -> None:
    """Fire an alert if the threshold is crossed and no recent unread alert exists."""
    # Check for recent unread alert of same type
    recent = await session.execute(
        select(Alert).where(
            Alert.company_id == company_id,
            Alert.alert_type == AlertType.TRAP_SCORE if score_name == "trap_score" else AlertType.CASH_RUNWAY,
            Alert.is_read == False,
        )
    )
    if recent.scalar_one_or_none():
        return  # already alerted

    alert = Alert(
        company_id=company_id,
        alert_type=AlertType.TRAP_SCORE if score_name == "trap_score" else AlertType.CASH_RUNWAY,
        severity=severity,
        title=f"{label}: {score_name.replace('_', ' ').title()} {score:.0f}",
        body=f"{label} threshold crossed. {score_name.replace('_', ' ').title()} is {score:.0f}/100 (threshold: {threshold}).",
        payload_json={"score_name": score_name, "score_value": score, "threshold": threshold},
    )
    session.add(alert)


async def run_score_pipeline(ticker: str | None = None, dry_run: bool = False) -> dict:
    """Run the full scoring pipeline."""
    print("=" * 60)
    print("SCORE PIPELINE" + (" [DRY RUN]" if dry_run else ""))
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

    print(f"\n📡 {len(companies):,} companies to score")
    if not companies:
        print("   No active companies. Run seed_universe.py first.")
        return {"status": "empty", "scored": 0}

    scored = 0
    alerts_fired = 0
    errors = 0

    for i, company in enumerate(companies):
        if (i + 1) % 50 == 0:
            print(f"   ... {i+1}/{len(companies)} processed ({scored} scored)")

        try:
            async with AsyncSessionLocal() as session:
                # Build scores
                snapshot = await build_score_snapshot(company, session)

                # Get recent filings for AI summary
                filings_result = await session.execute(
                    select(Filing)
                    .options()
                    .where(Filing.company_id == company.id)
                    .order_by(Filing.filed_at.desc())
                    .limit(5)
                )
                recent_filings = filings_result.scalars().all()

                # Get latest PR
                pr_result = await session.execute(
                    select(PressRelease)
                    .where(PressRelease.company_id == company.id)
                    .order_by(PressRelease.published_at.desc())
                    .limit(1)
                )
                latest_pr = pr_result.scalar_one_or_none()

                # Get previous snapshot for "what changed"
                prev_result = await session.execute(
                    select(ScoreSnapshot)
                    .where(
                        ScoreSnapshot.company_id == company.id,
                        ScoreSnapshot.id != snapshot.id,
                    )
                    .order_by(ScoreSnapshot.as_of_timestamp.desc())
                    .limit(1)
                )
                prev_snapshot = prev_result.scalar_one_or_none()

                # Build AI summary
                ai_summary = build_stock_summary(
                    ticker=company.ticker,
                    company_name=company.name,
                    scores=snapshot,
                    recent_filings=recent_filings,
                    latest_pr=latest_pr,
                    days_to_runway=None,
                )
                snapshot.ai_summary = ai_summary
                await session.commit()

                # Check alert thresholds
                for score_name, thresholds in ALERT_THRESHOLDS.items():
                    score_value = getattr(snapshot, score_name, None)
                    if score_value is None:
                        continue

                    for level_name, threshold in thresholds.items():
                        if score_value >= threshold:
                            severity_map = {
                                "watch": AlertSeverity.INFO,
                                "elevated": AlertSeverity.CAUTION,
                                "high_risk": AlertSeverity.HIGH,
                                "severe": AlertSeverity.SEVERE,
                                "caution": AlertSeverity.CAUTION,
                                "high": AlertSeverity.HIGH,
                            }
                            severity = severity_map.get(level_name, AlertSeverity.INFO)

                            if dry_run:
                                print(f"   [DRY RUN] Would alert {company.ticker}: {score_name}={score_value}")
                            else:
                                await generate_alert(
                                    company.id, score_value, score_name,
                                    threshold,
                                    severity,
                                    company.ticker,
                                    session,
                                )
                                alerts_fired += 1
                            break  # only fire highest level

                if not dry_run:
                    await session.commit()
                scored += 1

        except Exception as e:
            errors += 1
            print(f"   ❌ {company.ticker}: {e}")
            continue

    print("\n" + "=" * 60)
    print("SCORING COMPLETE" + (" [DRY RUN]" if dry_run else ""))
    print(f"  ✅ Scored:       {scored}")
    print(f"  🚨 Alerts fired: {alerts_fired}")
    print(f"  ❌ Errors:       {errors}")
    print("=" * 60)

    return {"scored": scored, "alerts_fired": alerts_fired, "errors": errors}


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_score_pipeline(ticker=args.ticker, dry_run=args.dry_run))

if __name__ == "__main__":
    main()
