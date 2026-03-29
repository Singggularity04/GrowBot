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
        
        # --- NailsBot telegram booking tables ---
        await db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,          -- YYYY-MM-DD
                time        TEXT NOT NULL,          -- HH:MM
                is_booked   INTEGER DEFAULT 0,      -- 0=free, 1=booked
                is_closed   INTEGER DEFAULT 0       -- 1=day closed by admin
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

# --------------- Slot management ---------------

async def add_slot(date: str, time: str):
    """Add a single available slot."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO slots (date, time) VALUES (?, ?)", (date, time)
        )
        await db.commit()


async def get_available_dates() -> list[str]:
    """Return sorted list of dates that have at least one free, open slot."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT DISTINCT date FROM slots
            WHERE is_booked = 0 AND is_closed = 0
            ORDER BY date
        """)
        rows = await cursor.fetchall()
        return [row["date"] for row in rows]


async def get_available_times(date: str) -> list[dict]:
    """Return free time slots for a given date."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, time FROM slots
            WHERE date = ? AND is_booked = 0 AND is_closed = 0
            ORDER BY time
        """, (date,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_slot_by_id(slot_id: int) -> dict | None:
    """Return a single slot by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_slot(slot_id: int):
    """Delete an unbooked slot."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM slots WHERE id = ? AND is_booked = 0", (slot_id,))
        await db.commit()


async def close_day(date: str):
    """Mark all slots on a date as closed (unavailable)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE slots SET is_closed = 1 WHERE date = ?", (date,)
        )
        await db.commit()


async def get_all_slots_for_date(date: str) -> list[dict]:
    """Return ALL slots for a date (for admin view)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM slots WHERE date = ? ORDER BY time", (date,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# --------------- Booking management ---------------

async def book_slot(user_id: int, slot_id: int, name: str, phone: str) -> int:
    """Create a booking and mark slot as booked. Returns booking ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (slot_id,))
        cursor = await db.execute(
            "INSERT INTO bookings (user_id, slot_id, name, phone) VALUES (?, ?, ?, ?)",
            (user_id, slot_id, name, phone),
        )
        await db.commit()
        return cursor.lastrowid


async def get_booking_by_user(user_id: int) -> dict | None:
    """Return active booking for a user (only one allowed at a time)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT b.*, s.date, s.time
            FROM bookings b JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def cancel_booking(booking_id: int) -> dict | None:
    """Cancel a booking: free the slot and delete the record. Returns slot info."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get slot_id before deleting
        cursor = await db.execute(
            "SELECT slot_id FROM bookings WHERE id = ?", (booking_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        slot_id = row["slot_id"]

        # Free slot and remove booking
        await db.execute("UPDATE slots SET is_booked = 0 WHERE id = ?", (slot_id,))
        await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        await db.commit()

        cursor = await db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
        slot = await cursor.fetchone()
        return dict(slot) if slot else None


async def get_bookings_for_date(date: str) -> list[dict]:
    """Return all bookings for a given date (for admin view)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT b.*, s.date, s.time
            FROM bookings b JOIN slots s ON b.slot_id = s.id
            WHERE s.date = ?
            ORDER BY s.time
        """, (date,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_future_bookings() -> list[dict]:
    """Return all future bookings (for scheduler restore on startup)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT b.*, s.date, s.time
            FROM bookings b JOIN slots s ON b.slot_id = s.id
            WHERE s.date >= date('now')
            ORDER BY s.date, s.time
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_booking_by_id(booking_id: int) -> dict | None:
    """Return a booking by its ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT b.*, s.date, s.time
            FROM bookings b JOIN slots s ON b.slot_id = s.id
            WHERE b.id = ?
        """, (booking_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_dates_with_slots() -> list[str]:
    """Return all dates that have any slots (for admin calendar)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT DISTINCT date FROM slots ORDER BY date"
        )
        rows = await cursor.fetchall()
        return [row["date"] for row in rows]
