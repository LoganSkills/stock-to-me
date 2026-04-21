"""Stock detail and list endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.models import (
    Company, Filing, FilingTag, MarketDataDaily, ScoreSnapshot,
    PressRelease, CompanyEvent, Offering, PatternMatch, FinancialSnapshot,
    User,
)
from app.schemas.schemas import (
    CompanyOut, CompanyDetailOut, StockListItem, StockListResponse,
    FilingOut, ScoreSnapshotOut, CompanyTimeline, TimelineEvent,
    DilutionImpactOut, StockFilter,
)
from app.services.scoring_service import trap_label, build_score_snapshot
from app.services.dilution_service import calc_dilution_impact
from app.services.ai_summary_service import build_stock_summary, build_what_changed

router = APIRouter()


def _score_snapshot_to_out(s: ScoreSnapshot) -> ScoreSnapshotOut:
    return ScoreSnapshotOut(
        id=s.id, company_id=s.company_id, as_of_timestamp=s.as_of_timestamp,
        cash_need_score=s.cash_need_score, dilution_pressure_score=s.dilution_pressure_score,
        pump_setup_score=s.pump_setup_score, trap_score=s.trap_score,
        timing_urgency_score=s.timing_urgency_score, historical_repeat_score=s.historical_repeat_score,
        pattern_similarity_score=s.pattern_similarity_score, dilution_impact_score=s.dilution_impact_score,
        ai_summary=s.ai_summary, version=s.version,
    )


@router.get("", response_model=StockListResponse)
async def list_stocks(
    min_market_cap: Optional[int] = None,
    max_market_cap: Optional[int] = None,
    sector: Optional[str] = None,
    exchange: Optional[str] = None,
    min_trap_score: Optional[int] = None,
    max_trap_score: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        query = (
            select(Company, ScoreSnapshot)
            .join(ScoreSnapshot, Company.id == ScoreSnapshot.company_id)
            .where(Company.is_active == True)
            .where(ScoreSnapshot.as_of_timestamp >= cutoff)
        )
        if min_market_cap:
            query = query.where(Company.market_cap >= min_market_cap)
        if max_market_cap:
            query = query.where(Company.market_cap <= max_market_cap)
        if sector:
            query = query.where(Company.sector == sector)
        if exchange:
            query = query.where(Company.exchange == exchange)
        if min_trap_score:
            query = query.where(ScoreSnapshot.trap_score >= min_trap_score)
        if max_trap_score:
            query = query.where(ScoreSnapshot.trap_score <= max_trap_score)

        # Get total count
        count_q = select(func.count()).select_from(query.subquery())
        total = (await session.execute(count_q)).scalar() or 0

        query = query.order_by(desc(ScoreSnapshot.trap_score)).offset((page - 1) * per_page).limit(per_page)
        result = await session.execute(query)
        rows = result.all()

        stocks = []
        for company, score in rows:
            stocks.append(StockListItem(
                ticker=company.ticker,
                name=company.name,
                exchange=company.exchange,
                sector=company.sector,
                market_cap=company.market_cap,
                current_price=company.current_price,
                trap_score=score.trap_score,
                trap_label=trap_label(score.trap_score),
                cash_need_score=score.cash_need_score,
                dilution_pressure_score=score.dilution_pressure_score,
                pump_setup_score=score.pump_setup_score,
                latest_filed_at=score.as_of_timestamp,
            ))

        return StockListResponse(stocks=stocks, total=total, page=page, per_page=per_page)


@router.get("/{ticker}")
async def get_stock(ticker: str, user: User = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        # Latest score
        score_result = await session.execute(
            select(ScoreSnapshot)
            .where(ScoreSnapshot.company_id == company.id)
            .order_by(desc(ScoreSnapshot.as_of_timestamp))
            .limit(1)
        )
        score = score_result.scalar_one_or_none()
        latest_scores = _score_snapshot_to_out(score) if score else None

        # Latest PR
        pr_result = await session.execute(
            select(PressRelease)
            .where(PressRelease.company_id == company.id)
            .order_by(desc(PressRelease.published_at))
            .limit(1)
        )
        pr = pr_result.scalar_one_or_none()

        # Days to runway
        fin_result = await session.execute(
            select(FinancialSnapshot)
            .where(FinancialSnapshot.company_id == company.id)
            .order_by(desc(FinancialSnapshot.period_end))
            .limit(1)
        )
        fin = fin_result.scalar_one_or_none()
        days_to_runway = None
        if fin and fin.cash_and_equivalents and fin.op_cash_flow:
            monthly_burn = abs(fin.op_cash_flow / 3)
            if monthly_burn > 0:
                days_to_runway = (fin.cash_and_equivalents / monthly_burn) * 30

        return CompanyDetailOut(
            id=company.id,
            ticker=company.ticker,
            name=company.name,
            exchange=company.exchange,
            sector=company.sector,
            industry=company.industry,
            market_cap=company.market_cap,
            float_shares=company.float_shares,
            shares_outstanding=company.shares_outstanding,
            avg_volume_20d=company.avg_volume_20d,
            current_price=company.current_price,
            is_active=company.is_active,
            created_at=company.created_at,
            latest_scores=latest_scores,
            latest_pr=pr,
            days_to_runway=days_to_runway,
        )


@router.get("/{ticker}/scores")
async def get_stock_scores(ticker: str, user: User = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        score_result = await session.execute(
            select(ScoreSnapshot)
            .where(ScoreSnapshot.company_id == company.id)
            .order_by(desc(ScoreSnapshot.as_of_timestamp))
            .limit(1)
        )
        score = score_result.scalar_one_or_none()
        if not score:
            raise HTTPException(status_code=404, detail="No scores available yet")

        return _score_snapshot_to_out(score)


@router.get("/{ticker}/timeline")
async def get_stock_timeline(ticker: str, user: User = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        # Fetch last 90 days of events
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        events_result = await session.execute(
            select(CompanyEvent)
            .where(CompanyEvent.company_id == company.id)
            .where(CompanyEvent.event_timestamp >= cutoff)
            .order_by(desc(CompanyEvent.event_timestamp))
        )
        events = events_result.scalars().all()

        timeline_events = []
        for evt in events:
            timeline_events.append(TimelineEvent(
                timestamp=evt.event_timestamp,
                event_type=evt.event_type,
                label=_event_label(evt.event_type),
                detail=evt.metadata_json.get("detail") if evt.metadata_json else None,
                source=evt.source_type,
                metadata=evt.metadata_json,
            ))

        return CompanyTimeline(ticker=ticker, events=timeline_events)


@router.get("/{ticker}/filings")
async def get_stock_filings(
    ticker: str,
    filing_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        query = (
            select(Filing)
            .options(joinedload(Filing.tags))
            .where(Filing.company_id == company.id)
            .order_by(desc(Filing.filed_at))
        )
        if filing_type:
            query = query.where(Filing.filing_type == filing_type)
        query = query.limit(limit)

        filings_result = await session.execute(query)
        filings = filings_result.scalars().all()

        return [
            FilingOut(
                id=f.id, company_id=f.company_id, accession_number=f.accession_number,
                filing_type=f.filing_type, filed_at=f.filed_at, source_url=f.source_url,
                parsed_json=f.parsed_json, created_at=f.created_at,
                tags=[FilingTagOut(id=t.id, tag_name=t.tag_name, tag_value_text=t.tag_value_text,
                                  tag_value_num=t.tag_value_num, confidence=t.confidence) for t in f.tags],
            )
            for f in filings
        ]


@router.get("/{ticker}/dilution-impact")
async def get_dilution_impact(ticker: str, user: User = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        # Get latest offering
        offering_result = await session.execute(
            select(Offering)
            .where(Offering.company_id == company.id)
            .order_by(desc(Offering.announced_at))
            .limit(1)
        )
        offering = offering_result.scalar_one_or_none()

        impact = calc_dilution_impact(
            current_price=company.current_price,
            current_shares=company.shares_outstanding,
            offering_shares=offering.shares_offered if offering else None,
            offering_price=offering.offering_price if offering else None,
            warrant_shares=offering.warrant_shares if offering else None,
            warrant_exercise_price=offering.warrant_exercise_price if offering else None,
            atm_capacity=offering.atm_capacity_remaining if offering else None,
        )
        impact.company_id = company.id
        impact.ticker = company.ticker
        return impact


def _event_label(event_type: str) -> str:
    labels = {
        "financing_filing": "Financing Filing",
        "shelf_filing": "Shelf Registration",
        "amendment_filing": "Filing Amendment",
        "prospectus_filing": "Prospectus Filing",
        "financing_8k": "Financing 8-K",
        "bullish_pr": "Bullish PR",
        "compliance_notice": "Compliance Notice",
        "reverse_split": "Reverse Split",
        "volume_spike": "Volume Spike",
        "price_spike": "Price Spike",
        "selloff": "Selloff",
        "offering_pressure": "Offering Pressure",
    }
    return labels.get(event_type, event_type.replace("_", " ").title())
