import aiosqlite
from database import DB_PATH

async def run_migration():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                time        TEXT NOT NULL,
                is_booked   INTEGER DEFAULT 0,
                is_closed   INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                slot_id     INTEGER NOT NULL,
                name        TEXT NOT NULL,
                phone       TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (slot_id) REFERENCES slots(id)
            )
        """)
        await db.commit()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_migration())
    print("Migration complete!")
