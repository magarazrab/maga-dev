import aiosqlite
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.getenv("DB_PATH", "data/bot.db")


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                current_lesson INTEGER DEFAULT 0,
                is_subscribed INTEGER DEFAULT 0,
                joined_at TEXT,
                last_activity TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                day INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                youtube_url TEXT,
                material_file TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                channel_link TEXT NOT NULL,
                title TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        # Default lessons structure (1-6)
        defaults = [
            (1, "Урок 1 — Старт", "Старт.txt"),
            (2, "Урок 2 — Добавляем жизнь нашему приложению", "урок2.txt"),
            (3, "Урок 3 — Знакомимся с Python", "урок3.txt"),
            (4, "Урок 4 — Объединяем всё", "урок4.txt"),
            (5, "Урок 5 — Учимся сохранять данные", "Финал.txt"),
            (6, "Урок 6 — Из проекта в настоящее приложение", "урок5.txt"),
        ]
        for day, title, material in defaults:
            await db.execute(
                """
                INSERT OR IGNORE INTO lessons (day, title, youtube_url, material_file, is_active, created_at, updated_at)
                VALUES (?, ?, NULL, ?, 0, ?, ?)
                """,
                (day, title, material, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
            )
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, username: str = None, full_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username, full_name, current_lesson, is_subscribed, joined_at, last_activity)
            VALUES (?, ?, ?, 0, 0, ?, ?)
            """,
            (user_id, username, full_name, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        await db.commit()


async def update_user_activity(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_activity = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def set_user_subscribed(user_id: int, value: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_subscribed = ? WHERE user_id = ?",
            (1 if value else 0, user_id),
        )
        await db.commit()


async def set_user_lesson(user_id: int, lesson: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET current_lesson = ?, last_activity = ? WHERE user_id = ?",
            (lesson, datetime.utcnow().isoformat(), user_id),
        )
        await db.commit()


async def get_all_users() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_users_for_lesson(day: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE current_lesson >= ? AND is_subscribed = 1",
            (day - 1,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_lesson(day: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lessons WHERE day = ?", (day,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_lessons() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lessons ORDER BY day") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def update_lesson(day: int, title: str = None, youtube_url: str = None, is_active: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        lesson = await get_lesson(day)
        if not lesson:
            return False
        new_title = title if title is not None else lesson["title"]
        new_url = youtube_url if youtube_url is not None else lesson["youtube_url"]
        new_active = is_active if is_active is not None else lesson["is_active"]
        await db.execute(
            """
            UPDATE lessons
            SET title = ?, youtube_url = ?, is_active = ?, updated_at = ?
            WHERE day = ?
            """,
            (new_title, new_url, new_active, datetime.utcnow().isoformat(), day),
        )
        await db.commit()
        return True


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_setting(key: str, default: str = None) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


# ==================== CHANNELS (ОП) ====================

async def add_channel(channel_id: str, channel_link: str, title: str = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """
                INSERT INTO channels (channel_id, channel_link, title, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (channel_id.strip(), channel_link.strip(), title or channel_id, datetime.utcnow().isoformat()),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_channel(channel_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id.strip(),))
        await db.commit()
        return cur.rowcount > 0


async def remove_channel_by_db_id(db_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM channels WHERE id = ?", (db_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_all_channels(active_only: bool = True) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if active_only:
            query = "SELECT * FROM channels WHERE is_active = 1 ORDER BY id"
        else:
            query = "SELECT * FROM channels ORDER BY id"
        async with db.execute(query) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_channel_by_id(db_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE id = ?", (db_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
