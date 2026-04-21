"""Background job triggers (Celery / cron)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.models import Company, User
from app.services.edgar_service import ingest_company_filings
from app.services.scoring_service import build_score_snapshot

router = APIRouter()


@router.post("/run-daily-scan")
async def run_daily_scan(user: User = Depends(get_current_user)):
    """Trigger daily scan across all active companies."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).where(Company.is_active == True)
        )
        companies = result.scalars().all()

        results = []
        for company in companies:
            try:
                # Ingest recent filings
                await ingest_company_filings(company, session, days_back=7)
                # Recompute scores
                await build_score_snapshot(company, session)
                results.append({"ticker": company.ticker, "status": "ok"})
            except Exception as e:
                results.append({"ticker": company.ticker, "status": "error", "detail": str(e)})

        return {"total": len(companies), "results": results}


@router.post("/reparse-filing/{filing_id}")
async def reparse_filing(
    filing_id: int,
    user: User = Depends(get_current_user),
):
    """Trigger re-parse of a specific filing."""
    # Placeholder — full implementation in Phase 4
    return {"filing_id": filing_id, "status": "reparse_triggered"}
