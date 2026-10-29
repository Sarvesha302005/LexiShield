"""
Database Initialization and Seeding Script.
"""

import asyncio
from src.database import engine, init_db, seed_db_if_empty


async def main():
    print("Initializing database schema...")
    await init_db()
    print("Seeding database...")
    seeded = await seed_db_if_empty()
    print(f"Seed complete. New seed applied: {seeded}")
    await engine.dispose()
    print("DATABASE_SEEDED_SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())

