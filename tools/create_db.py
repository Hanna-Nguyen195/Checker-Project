import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.base import Base
# import models để Base biết schema
from app.db.models import user as user_model  # noqa: F401

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=True, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✅ Created tables if not existing.")

if __name__ == "__main__":
    asyncio.run(main())
