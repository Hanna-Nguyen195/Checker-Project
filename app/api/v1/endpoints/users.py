# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.core.security import get_password_hash
from app.db.models.user import User
from app.services.user_service import get_user_by_username_or_email

router = APIRouter()

@router.post("", response_model=UserOut)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # check unique username
    if await get_user_by_username_or_email(db, data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    # check unique email
    existing = (await db.execute(select(User).where(User.email == data.email))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        password_hash=get_password_hash(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.password:
        current_user.password_hash = get_password_hash(payload.password)
        current_user.token_version += 1  # revoke token cũ
    await db.commit()
    await db.refresh(current_user)
    return current_user
