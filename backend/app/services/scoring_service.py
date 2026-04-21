"""Scoring Engine — calculates all 5 scores + Trap Score."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import (
    Company, Filing, FilingTag, FinancialSnapshot, MarketDataDaily,
    CompanyEvent, PressRelease, ScoreSnapshot, Offering,
)
from app.models.models import EventType


# ─── Score weights ──────────────────────────────────────────────────────────────

WEIGHTS = {
    "trap": {
        "dilution_pressure": 0.25,
        "cash_need": 0.20,
        "pump_setup": 0.20,
        "historical_repeat": 0.20,
        "timing_urgency": 0.15,
    }
}


# ─── Score Functions ────────────────────────────────────────────────────────────


def calc_cash_need_score(
    runway_months: Optional[float],
    going_concern: bool,
    revenue: Optional[int],
    net_loss: Optional[int],
    total_debt: Optional[int],
    cash: Optional[int],
    compliance_stress: bool = False,
) -> float:
    """Cash Need Score: how badly the company may need capital. 0–100."""
    score = 0.0

    if runway_months is not None:
        if runway_months <= 3:
            score += 40
        elif runway_months <= 6:
            score += 25
        elif runway_months <= 9:
            score += 10

    if going_concern:
        score += 20

    if revenue is not None and revenue < 1_000_000 and net_loss is not None and net_loss < -500_000:
        score += 15

    if total_debt is not None and cash is not None and total_debt > cash * 2:
        score += 10

    if compliance_stress:
        score += 10

    return min(100.0, score)


def calc_dilution_pressure_score(
    days_since_s1: Optional[int],
    days_since_424b: Optional[int],
    days_since_8k: Optional[int],
    has_atm: bool,
    warrants_near_market: bool,
    convertibles_outstanding: bool,
    has_resale_registration: bool,
) -> float:
    """Dilution Pressure Score: likelihood of near-term share supply increase. 0–100."""
    score = 0.0

    if days_since_s1 is not None and days_since_s1 <= 10:
        score += 25
    elif days_since_s1 is not None and days_since_s1 <= 30:
        score += 10

    if days_since_424b is not None and days_since_424b <= 5:
        score += 25
    elif days_since_424b is not None and days_since_424b <= 15:
        score += 10

    if days_since_8k is not None and days_since_8k <= 5:
        score += 20

    if has_atm:
        score += 15

    if warrants_near_market:
        score += 15

    if convertibles_outstanding:
        score += 15

    if has_resale_registration:
        score += 10

    return min(100.0, score)


def calc_pump_setup_score(
    rel_volume_5d: Optional[float],
    premarket_gap_pct: Optional[float],
    pr_count_10d: int,
    float_shares: Optional[int],
    return_3d: Optional[float],
    sector_hot: bool = False,
) -> float:
    """Pump Setup Score: likelihood of spec. momentum before financing. 0–100."""
    score = 0.0

    if rel_volume_5d is not None and rel_volume_5d >= 3.0:
        score += 20
    elif rel_volume_5d is not None and rel_volume_5d >= 2.0:
        score += 10

    if premarket_gap_pct is not None and premarket_gap_pct >= 15.0:
        score += 20
    elif premarket_gap_pct is not None and premarket_gap_pct >= 8.0:
        score += 10

    if pr_count_10d >= 3:
        score += 15
    elif pr_count_10d >= 1:
        score += 5

    if float_shares is not None and float_shares < 5_000_000:
        score += 15
    elif float_shares is not None and float_shares < 15_000_000:
        score += 8

    if return_3d is not None and return_3d >= 20.0:
        score += 15
    elif return_3d is not None and return_3d >= 10.0:
        score += 8

    if sector_hot:
        score += 10

    return min(100.0, score)


def calc_timing_urgency_score(
    runway_months: Optional[float],
    days_since_s1: Optional[int],
    days_since_424b: Optional[int],
    days_since_8k: Optional[int],
    compliance_deadline: bool,
) -> float:
    """Timing Urgency Score: how close a material event may be. 0–100."""
    score = 0.0

    if runway_months is not None and runway_months <= 3:
        score += 25
    elif runway_months is not None and runway_months <= 6:
        score += 10

    if days_since_s1 is not None and days_since_s1 <= 7:
        score += 20
    elif days_since_s1 is not None and days_since_s1 <= 21:
        score += 8

    if days_since_424b is not None and days_since_424b <= 3:
        score += 25
    elif days_since_424b is not None and days_since_424b <= 10:
        score += 10

    if days_since_8k is not None and days_since_8k <= 5:
        score += 20
    elif days_since_8k is not None and days_since_8k <= 14:
        score += 8

    if compliance_deadline:
        score += 10

    return min(100.0, score)


def calc_historical_repeat_score(
    prior_offerings_24m: int,
    pr_after_filing_repeat: bool,
    reverse_split_then_raise: bool,
    avg_post_filing_selloff: Optional[float],
    warrant_overhang_repeat: bool,
) -> float:
    """Historical Repeat Score: whether the company repeats capital-raise playbooks. 0–100."""
    score = 0.0

    if prior_offerings_24m >= 3:
        score += 25
    elif prior_offerings_24m >= 1:
        score += 10

    if pr_after_filing_repeat:
        score += 20

    if reverse_split_then_raise:
        score += 20

    if avg_post_filing_selloff is not None and avg_post_filing_selloff >= 20.0:
        score += 15

    if warrant_overhang_repeat:
        score += 10

    return min(100.0, score)


def calc_trap_score(
    dilution_pressure: float,
    cash_need: float,
    pump_setup: float,
    historical_repeat: float,
    timing_urgency: float,
) -> float:
    """Primary user-facing risk score. Weighted composite. 0–100."""
    w = WEIGHTS["trap"]
    score = (
        w["dilution_pressure"] * dilution_pressure
        + w["cash_need"] * cash_need
        + w["pump_setup"] * pump_setup
        + w["historical_repeat"] * historical_repeat
        + w["timing_urgency"] * timing_urgency
    )
    return round(min(100.0, max(0.0, score)))


def trap_label(score: float) -> str:
    """Map score to risk label."""
    if score >= 85:
        return "Severe"
    elif score >= 70:
        return "High Risk"
    elif score >= 50:
        return "Elevated"
    elif score >= 25:
        return "Watch"
    else:
        return "Low"


# ─── Score snapshot builder ──────────────────────────────────────────────────────


async def build_score_snapshot(
    company: Company,
    session: AsyncSession,
) -> ScoreSnapshot:
    """Compute all scores for a company and return a ScoreSnapshot."""

    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)
    cutoff_10d = now - timedelta(days=10)
    cutoff_24m = now - timedelta(days=730)

    # ── Recent filings ──────────────────────────────────────────────────────────
    result = await session.execute(
        select(Filing)
        .options(joinedload(Filing.tags))
        .where(Filing.company_id == company.id)
        .where(Filing.filed_at >= cutoff_30d)
        .order_by(Filing.filed_at.desc())
    )
    recent_filings = result.scalars().all()

    days_since_s1 = None
    days_since_424b = None
    days_since_8k = None
    has_atm = False
    has_resale_registration = False
    warrants_near_market = False
    convertibles_outstanding = False

    for filing in recent_filings:
        days_ago = (now - filing.filed_at).days
        if filing.filing_type in ("S-1", "S-1/A") and days_since_s1 is None:
            days_since_s1 = days_ago
        if filing.filing_type in ("424B3", "424B4", "424B5") and days_since_424b is None:
            days_since_424b = days_ago
        if filing.filing_type == "8-K" and days_since_8k is None:
            days_since_8k = days_ago

        for tag in filing.tags:
            if tag.tag_name == "atm" or "at-the-market" in str(tag.tag_value_text or ""):
                has_atm = True
            if tag.tag_name == "resale_registration":
                has_resale_registration = True
            if tag.tag_name == "warrants_issued":
                warrants_near_market = True
            if tag.tag_name == "convertible_notes":
                convertibles_outstanding = True

    # ── Financial snapshot ───────────────────────────────────────────────────────
    result = await session.execute(
        select(FinancialSnapshot)
        .where(FinancialSnapshot.company_id == company.id)
        .order_by(FinancialSnapshot.period_end.desc())
        .limit(1)
    )
    fin = result.scalar_one_or_none()

    cash = fin.cash_and_equivalents if fin else None
    debt = fin.total_debt if fin else None
    revenue = fin.revenue if fin else None
    net_loss = fin.net_loss if fin else None
    going_concern = fin.going_concern_flag if fin else False

    # Estimate runway
    runway_months = None
    if cash and fin and fin.op_cash_flow:
        monthly_burn = abs(fin.op_cash_flow / 3)  # quarterly burn / 3
        if monthly_burn > 0:
            runway_months = cash / monthly_burn

    # ── Market data ─────────────────────────────────────────────────────────────
    result = await session.execute(
        select(MarketDataDaily)
        .where(MarketDataDaily.company_id == company.id)
        .order_by(MarketDataDaily.date.desc())
        .limit(1)
    )
    mkt = result.scalar_one_or_none()

    rel_vol = mkt.rel_volume_5d if mkt else None
    premarket_gap = mkt.premarket_gap_pct if mkt else None
    ret_3d = mkt.return_3d if mkt else None

    # ── Press releases ─────────────────────────────────────────────────────────
    result = await session.execute(
        select(PressRelease)
        .where(PressRelease.company_id == company.id)
        .where(PressRelease.published_at >= cutoff_10d)
    )
    pr_count_10d = len(result.scalars().all())

    # ── Prior offerings (24 months) ─────────────────────────────────────────────
    result = await session.execute(
        select(func.count(Offering.id))
        .where(Offering.company_id == company.id)
        .where(Offering.announced_at >= cutoff_24m)
    )
    prior_offerings_24m = result.scalar() or 0

    # ── Prior events ─────────────────────────────────────────────────────────────
    result = await session.execute(
        select(CompanyEvent)
        .where(CompanyEvent.company_id == company.id)
        .where(CompanyEvent.event_timestamp >= cutoff_24m)
        .order_by(CompanyEvent.event_timestamp)
    )
    events = result.scalars().all()

    # Pattern detection
    pr_after_filing_repeat = False
    reverse_split_then_raise = False
    warrant_overhang_repeat = False

    prev_was_rs = False
    for evt in events:
        if evt.event_type == EventType.REVERSE_SPLIT:
            prev_was_rs = True
        elif evt.event_type == EventType.FINANCING_FILING and prev_was_rs:
            reverse_split_then_raise = True
            prev_was_rs = False
        elif evt.event_type == EventType.BULLISH_PR:
            # Check if a financing filing happened in prior 5 days (proxy)
            pr_after_filing_repeat = True  # simplified MVP

    # ── Calculate scores ───────────────────────────────────────────────────────
    cash_need_score = calc_cash_need_score(
        runway_months, going_concern, revenue, net_loss, debt, cash
    )
    dilution_pressure_score = calc_dilution_pressure_score(
        days_since_s1, days_since_424b, days_since_8k,
        has_atm, warrants_near_market, convertibles_outstanding, has_resale_registration
    )
    pump_setup_score = calc_pump_setup_score(
        rel_vol, premarket_gap, pr_count_10d,
        company.float_shares, ret_3d
    )
    timing_urgency_score = calc_timing_urgency_score(
        runway_months, days_since_s1, days_since_424b, days_since_8k, False
    )
    historical_repeat_score = calc_historical_repeat_score(
        prior_offerings_24m, pr_after_filing_repeat,
        reverse_split_then_raise, None, warrant_overhang_repeat
    )
    trap_score = calc_trap_score(
        dilution_pressure_score, cash_need_score, pump_setup_score,
        historical_repeat_score, timing_urgency_score
    )

    # ── Build snapshot ─────────────────────────────────────────────────────────
    snapshot = ScoreSnapshot(
        company_id=company.id,
        cash_need_score=cash_need_score,
        dilution_pressure_score=dilution_pressure_score,
        pump_setup_score=pump_setup_score,
        trap_score=trap_score,
        timing_urgency_score=timing_urgency_score,
        historical_repeat_score=historical_repeat_score,
        pattern_similarity_score=0.0,  # pattern engine in Phase 4
        dilution_impact_score=0.0,    # dilution calc in Phase 4
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot
