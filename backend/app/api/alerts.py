"""Alerts endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.models import Alert, Company, User
from app.schemas.schemas import AlertOut, AlertUpdate

router = APIRouter()


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    unread_only: bool = False,
    alert_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        query = select(Alert).order_by(desc(Alert.triggered_at))
        if unread_only:
            query = query.where(Alert.is_read == False)
        if alert_type:
            query = query.where(Alert.alert_type == alert_type)
        query = query.limit(limit)

        result = await session.execute(query)
        alerts = result.scalars().all()

        items = []
        for alert in alerts:
            ticker = None
            if alert.company_id:
                company_result = await session.execute(
                    select(Company.ticker).where(Company.id == alert.company_id)
                )
                ticker = company_result.scalar_one_or_none()

            items.append(AlertOut(
                id=alert.id, company_id=alert.company_id, alert_type=alert.alert_type,
                severity=alert.severity, triggered_at=alert.triggered_at,
                title=alert.title, body=alert.body, payload_json=alert.payload_json,
                is_read=alert.is_read,
            ))

        return items


@router.patch("/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert.is_read = True
        await session.commit()
        return {"ok": True}
