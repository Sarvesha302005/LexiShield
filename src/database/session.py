"""
Database Session Management & Async Engine Configuration.
Provides connection pooling, session lifecycle, and automatic table initialization.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings
from src.database.models import Base

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure async engine
# For SQLite, check_same_thread must be false
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for database session injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_DISPUTES_COLUMN_MIGRATIONS: dict[str, str] = {
    "recommended_action": "VARCHAR(100)",
    "hitl_reviewed_by": "VARCHAR(100)",
    "hitl_override_action": "VARCHAR(100)",
    "pdf_dossier_sha256": "VARCHAR(64)",
    "specialist_agent": "VARCHAR(100)",
    "persona_mode": "VARCHAR(100)",
    "llm_tier_used": "VARCHAR(100)",
    "seller_rights_met": "BOOLEAN",
    "reasoning_steps": "JSON",
    "telemetry_billing": "JSON",
}


async def init_db() -> None:
    """Creates database schema if not already initialized and applies safe additive migrations."""
    logger.info("Verifying and initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in settings.DATABASE_URL:
            res = await conn.execute(text("PRAGMA table_info(disputes)"))
            existing_cols = {row[1] for row in res.fetchall()}
            for col_name, col_type in _DISPUTES_COLUMN_MIGRATIONS.items():
                if col_name not in existing_cols:
                    await conn.execute(
                        text(f"ALTER TABLE disputes ADD COLUMN {col_name} {col_type}")
                    )
                    logger.info(f"Migrated disputes table: added column '{col_name}'.")
    logger.info("Database schema initialized successfully.")
