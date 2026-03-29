"""SQLite database — tracks users and their funnel interactions."""

import aiosqlite
from config import now_moscow

DB_PATH = "growbot.db"


async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                first_name TEXT,
                started_at TEXT NOT NULL,
                booked     INTEGER DEFAULT 0,
                last_active TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                action    TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        # Track follow-up jobs so we can restore them after restart
        await db.execute("""
            CREATE TABLE IF NOT EXISTS followups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                stage       INTEGER NOT NULL,
                fire_at     TEXT NOT NULL,
                sent        INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def register_user(user_id: int, username: str = None, first_name: str = None):
    """Insert or update user on /start."""
    now = now_moscow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, started_at, booked, last_active)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active = excluded.last_active
        """, (user_id, username, first_name, now, now))
        await db.commit()


async def mark_booked(user_id: int):
    """Mark user as booked — cancels pending follow-ups."""
    now = now_moscow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET booked = 1, last_active = ? WHERE user_id = ?",
            (now, user_id),
        )
        # Cancel pending follow-ups
        await db.execute(
            "UPDATE followups SET sent = 1 WHERE user_id = ? AND sent = 0",
            (user_id,),
        )
        await db.commit()


async def is_booked(user_id: int) -> bool:
    """Check if user already booked."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT booked FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return bool(row and row[0])


async def log_interaction(user_id: int, action: str):
    """Log user action for analytics."""
    now = now_moscow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO interactions (user_id, action, timestamp) VALUES (?, ?, ?)",
            (user_id, action, now),
        )
        await db.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?", (now, user_id)
        )
        await db.commit()


async def save_followup(user_id: int, stage: int, fire_at: str):
    """Save scheduled follow-up to DB for crash recovery."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO followups (user_id, stage, fire_at) VALUES (?, ?, ?)",
            (user_id, stage, fire_at),
        )
        await db.commit()


async def mark_followup_sent(user_id: int, stage: int):
    """Mark a follow-up stage as sent."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE followups SET sent = 1 WHERE user_id = ? AND stage = ?",
            (user_id, stage),
        )
        await db.commit()


async def get_pending_followups() -> list[dict]:
    """Return all unsent follow-ups (for restoring after restart)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, stage, fire_at FROM followups WHERE sent = 0"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def cancel_followups(user_id: int):
    """Cancel all pending follow-ups for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE followups SET sent = 1 WHERE user_id = ? AND sent = 0",
            (user_id,),
        )
        await db.commit()


# --- Stats for admin ---

async def get_stats() -> dict:
    """Return funnel statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE booked = 1")
        booked = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT action, COUNT(*) FROM interactions GROUP BY action"
        )
        actions = {row[0]: row[1] for row in await cursor.fetchall()}

    conversion = round(booked / total * 100, 1) if total else 0
    return {
        "total_users": total,
        "booked_users": booked,
        "conversion": conversion,
        "actions": actions,
    }
