from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User

async def get_user_by_username_or_email(db: AsyncSession, value: str) -> User | None:
    stmt = select(User).where((User.username == value) | (User.email == value))
    return (await db.execute(stmt)).scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return (await db.execute(stmt)).scalars().first()
