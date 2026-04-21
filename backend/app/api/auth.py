"""Auth endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, UserOut, Token

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(email=data.email, hashed_password=hash_password(data.password))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@router.post("/login", response_model=Token)
async def login(data: UserLogin):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"sub": str(user.id)})
        return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
