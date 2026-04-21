"""
Broker Watcher — monitors high-trap-score setups and fires alerts.

This is the live operational loop that ties the data pipeline to the Broker agent.
It runs continuously (or via cron) and checks for new high-trap setups,
then fires notifications through the Broker notification service.

Usage:
  python scripts/run_broker_watcher.py              # continuous (checks every 15 min)
  python scripts/run_broker_watcher.py --once        # single check
  python scripts/run_broker_watcher.py --min-score 70  # only alert scores >= 70
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.models import Company, ScoreSnapshot, Filing, Offering
from app.schemas.schemas import AlertType, AlertSeverity
from app.services.scoring_service import trap_label
from scripts.broker_notifications import (
    BrokerAlert,
    AlertSeverity,
    AlertPriority,
    send_broker_alert,
    should_escalate,
    log_to_mission_control,
)


MIN_TRAP_SCORE = int(os.getenv("BROKER_MIN_TRAP_SCORE", "60"))
PREVIOUS_SCORE_CUTOFF = 72  # hours


async def check_for_trap_setups() -> list[dict]:
    """
    Scan for companies with high trap scores and new financing filings
    that haven't been alerted yet.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=PREVIOUS_SCORE_CUTOFF)
    findings = []

    async with AsyncSessionLocal() as session:
        # Get latest score snapshots with their companies
        result = await session.execute(
            select(ScoreSnapshot, Company)
            .join(Company)
            .where(Company.is_active == True)
            .where(ScoreSnapshot.as_of_timestamp >= cutoff)
            .order_by(ScoreSnapshot.trap_score.desc())
            .limit(50)
        )
        rows = result.all()

    for snapshot, company in rows:
        if snapshot.trap_score < MIN_TRAP_SCORE:
            continue

        # Get recent financing filings
        async with AsyncSessionLocal() as session:
            filings_result = await session.execute(
                select(Filing)
                .where(
                    and_(
                        Filing.company_id == company.id,
                        Filing.filing_type.in_(["S-1", "S-1/A", "424B3", "424B4", "424B5", "8-K"]),
                        Filing.filed_at >= cutoff,
                    )
                )
                .order_by(Filing.filed_at.desc())
            )
            filings = filings_result.scalars().all()

        # Get latest offering
        async with AsyncSessionLocal() as session:
            offering_result = await session.execute(
                select(Offering)
                .where(Offering.company_id == company.id)
                .order_by(Offering.announced_at.desc())
                .limit(1)
            )
            offering = offering_result.scalar_one_or_none()

        findings.append({
            "company": company,
            "snapshot": snapshot,
            "filings": filings,
            "offering": offering,
        })

    return findings


async def run_broker_watcher(once: bool = False, min_score: int = MIN_TRAP_SCORE) -> dict:
    """
    Run the Broker watcher loop.
    Checks for high-trap setups and fires alerts through notification channels.
    """
    global MIN_TRAP_SCORE
    MIN_TRAP_SCORE = min_score

    print("=" * 60)
    print(f"BROKER WATCHER  (min trap score: {MIN_TRAP_SCORE})")
    print("=" * 60)

    findings = await check_for_trap_setups()

    if not findings:
        print("\n✅ No high-trap setups detected.")
        return {"setups": 0, "alerts_fired": 0}

    print(f"\n📡 {len(findings)} high-trap setup(s) found:\n")

    alerts_fired = 0

    for item in findings:
        company = item["company"]
        snapshot = item["snapshot"]
        filings = item["filings"]
        offering = item["offering"]

        # Build alert message
        filing_types = [f.filing_type for f in filings]
        filing_str = ", ".join(filing_types) if filing_types else "score spike only"
        days_ago = (datetime.now(timezone.utc) - snapshot.as_of_timestamp).days

        # Determine severity
        if snapshot.trap_score >= 85:
            severity = AlertSeverity.SEVERE
        elif snapshot.trap_score >= 70:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.CAUTION

        # Determine priority
        if offering and offering.shares_offered:
            priority = AlertPriority.HIGH
        elif snapshot.dilution_pressure_score >= 60:
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.NORMAL

        # Build dilution info
        dilution_pct = None
        if offering and offering.shares_offered and company.shares_outstanding:
            dilution_pct = (offering.shares_offered / company.shares_outstanding) * 100

        message = (
            f"Trap Score {snapshot.trap_score:.0f} ({trap_label(snapshot.trap_score)}). "
            f"New filings: {filing_str}. "
            f"Score updated {days_ago}d ago."
        )

        alert = BrokerAlert(
            ticker=company.ticker,
            severity=severity,
            message=message,
            trap_score=snapshot.trap_score,
            dilution_pct=dilution_pct,
            source="Broker Watcher",
            priority=priority,
        )

        # Log to Mission Control (always)
        log_to_mission_control(alert)

        # Fire to notification channels
        results = await send_broker_alert(alert)
        channels_sent = [k for k, v in results.items() if v]

        if channels_sent or should_escalate(alert):
            print(
                f"  🚨 {company.ticker} | Score: {snapshot.trap_score:.0f} | "
                f"Severity: {severity.value} | Dilution: {dilution_pct:.1f}% | "
                f"Channels: {', '.join(channels_sent) or 'logged only'}"
            )
            alerts_fired += 1

        if once:
            break  # only report the top one in --once mode

    print("\n" + "=" * 60)
    print(f"✅ Watcher complete | {alerts_fired} alert(s) fired")
    print("=" * 60)

    return {"setups": len(findings), "alerts_fired": alerts_fired}


# ─── CLI ───────────────────────────────────────────────────────────────────────

import os

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single check then exit")
    parser.add_argument("--min-score", type=int, default=60, help="Minimum trap score to alert on")
    parser.add_argument("--interval", type=int, default=15, help="Minutes between checks (continuous mode)")
    args = parser.parse_args()

    if args.once:
        asyncio.run(run_broker_watcher(once=True, min_score=args.min_score))
    else:
        print("🔁 Broker Watcher running continuously. Press Ctrl+C to stop.\n")
        while True:
            try:
                asyncio.run(run_broker_watcher(once=True, min_score=args.min_score))
                print(f"\n💤 Sleeping {args.interval} minutes...\n")
                asyncio.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n👋 Broker Watcher stopped.")
                break

if __name__ == "__main__":
    main()
