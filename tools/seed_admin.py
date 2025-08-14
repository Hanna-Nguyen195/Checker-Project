import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.models.user import User, UserRole, UserStatus

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Administrator",
            role=UserRole.admin,
            status=UserStatus.active,
        )
        db.add(admin)
        await db.commit()
    await engine.dispose()
    print("✅ Seeded admin: admin/admin123")

if __name__ == "__main__":
    asyncio.run(main())
