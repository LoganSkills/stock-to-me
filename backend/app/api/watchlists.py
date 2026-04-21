"""Watchlist endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.models import Watchlist, WatchlistItem, Company, User
from app.schemas.schemas import WatchlistOut, WatchlistCreate, WatchlistItemCreate

router = APIRouter()


@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(user: User = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Watchlist)
            .options(joinedload(Watchlist.items))
            .where(Watchlist.user_id == user.id)
        )
        watchlists = result.scalars().all()
        return [
            WatchlistOut(
                id=w.id, name=w.name, created_at=w.created_at,
                item_count=len(w.items),
            )
            for w in watchlists
        ]


@router.post("", response_model=WatchlistOut, status_code=201)
async def create_watchlist(data: WatchlistCreate, user: User = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        wl = Watchlist(name=data.name, user_id=user.id)
        session.add(wl)
        await session.commit()
        await session.refresh(wl)
        return WatchlistOut(id=wl.id, name=wl.name, created_at=wl.created_at, item_count=0)


@router.post("/{watchlist_id}/items", status_code=201)
async def add_to_watchlist(
    watchlist_id: int,
    data: WatchlistItemCreate,
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        # Verify ownership
        wl_result = await session.execute(
            select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
        )
        wl = wl_result.scalar_one_or_none()
        if not wl:
            raise HTTPException(status_code=404, detail="Watchlist not found")

        # Find company
        company_result = await session.execute(
            select(Company).where(Company.ticker == data.ticker.upper())
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        # Check duplicate
        existing = await session.execute(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.company_id == company.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already in watchlist")

        item = WatchlistItem(watchlist_id=watchlist_id, company_id=company.id)
        session.add(item)
        await session.commit()
        return {"ok": True, "ticker": company.ticker}


@router.delete("/{watchlist_id}/items/{ticker}")
async def remove_from_watchlist(
    watchlist_id: int,
    ticker: str,
    user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        wl_result = await session.execute(
            select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
        )
        if not wl_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Watchlist not found")

        company_result = await session.execute(
            select(Company).where(Company.ticker == ticker.upper())
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="Ticker not found")

        item_result = await session.execute(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.company_id == company.id,
            )
        )
        item = item_result.scalar_one_or_none()
        if item:
            await session.delete(item)
            await session.commit()

        return {"ok": True}
