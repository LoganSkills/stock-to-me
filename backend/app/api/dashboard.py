"""Dashboard endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.models import (
    Company, Alert, Filing, ScoreSnapshot, PressRelease, User,
)
from app.schemas.schemas import (
    DashboardOverview, TopTrapItem, NewFilingItem,
    AlertSummaryItem, StockFilter,
)
from app.services.scoring_service import trap_label

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        # Total companies
        total_result = await session.execute(select(func.count(Company.id)).where(Company.is_active == True))
        total_companies = total_result.scalar() or 0

        # High trap count (>=70)
        trap_result = await session.execute(
            select(func.count(ScoreSnapshot.id))
            .join(Company)
            .where(Company.is_active == True)
            .where(ScoreSnapshot.as_of_timestamp >= datetime.now(timezone.utc) - timedelta(hours=24))
            .where(ScoreSnapshot.trap_score >= 70)
        )
        high_trap_count = trap_result.scalar() or 0

        # New filings today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        filings_result = await session.execute(
            select(func.count(Filing.id)).where(Filing.filed_at >= today_start)
        )
        new_filings_today = filings_result.scalar() or 0

        # Active alerts (unread)
        alerts_result = await session.execute(
            select(func.count(Alert.id)).where(Alert.is_read == False)
        active_alerts = alerts_result.scalar() or 0

        # Trap score breakdown
        breakdown = {}
        for label, min_s, max_s in [("Low", 0, 24), ("Watch", 25, 49), ("Elevated", 50, 69), ("High Risk", 70, 84), ("Severe", 85, 100)]:
            count_result = await session.execute(
                select(func.count(ScoreSnapshot.id))
                .join(Company)
                .where(Company.is_active == True)
                .where(ScoreSnapshot.as_of_timestamp >= datetime.now(timezone.utc) - timedelta(hours=24))
                .where(ScoreSnapshot.trap_score >= min_s)
                .where(ScoreSnapshot.trap_score <= max_s)
            )
            breakdown[label] = count_result.scalar() or 0

        return DashboardOverview(
            total_companies=total_companies,
            high_trap_count=high_trap_count,
            new_filings_today=new_filings_today,
            active_alerts=active_alerts,
            trap_score_breakdown=breakdown,
        )


@router.get("/top-traps")
async def top_traps(
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await session.execute(
            select(ScoreSnapshot, Company)
            .join(Company)
            .where(Company.is_active == True)
            .where(ScoreSnapshot.as_of_timestamp >= cutoff)
            .order_by(desc(ScoreSnapshot.trap_score))
            .limit(limit)
        )
        rows = result.all()

        items = []
        for snapshot, company in rows:
            # Latest PR
            pr_result = await session.execute(
                select(PressRelease.title)
                .where(PressRelease.company_id == company.id)
                .order_by(desc(PressRelease.published_at))
                .limit(1)
            )
            latest_pr = pr_result.scalar_one_or_none()

            items.append(TopTrapItem(
                ticker=company.ticker,
                name=company.name,
                trap_score=snapshot.trap_score,
                trap_label=trap_label(snapshot.trap_score),
                dilution_pressure_score=snapshot.dilution_pressure_score,
                cash_need_score=snapshot.cash_need_score,
                pump_setup_score=snapshot.pump_setup_score,
                latest_pr=latest_pr,
            ))

        return items


@router.get("/new-filings")
async def new_filings(
    limit: int = Query(default=20, ge=1, le=100),
    filing_type: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        query = (
            select(Filing, Company)
            .join(Company)
            .where(Company.is_active == True)
            .where(Filing.filed_at >= cutoff)
            .order_by(desc(Filing.filed_at))
        )
        if filing_type:
            query = query.where(Filing.filing_type == filing_type)
        query = query.limit(limit)

        result = await session.execute(query)
        rows = result.all()

        items = []
        for filing, company in rows:
            tag_names = [tag.tag_name for tag in filing.tags]
            items.append(NewFilingItem(
                ticker=company.ticker,
                name=company.name,
                filing_type=filing.filing_type,
                filed_at=filing.filed_at,
                tags=tag_names,
            ))

        return items
