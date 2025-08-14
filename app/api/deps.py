# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.core.security import decode_token
from app.db.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_db() -> AsyncSession:
    async for s in get_session():
        yield s

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username_or_email = payload["sub"]
    token_version = payload.get("tv", 0)

    stmt = select(User).where((User.username == username_or_email) | (User.email == username_or_email))
    user = (await db.execute(stmt)).scalars().first()
    if not user or user.token_version != token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    if getattr(user, "status", None) and user.status.value != "active":
        raise HTTPException(status_code=403, detail="User inactive")
    return user
