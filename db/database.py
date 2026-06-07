import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "./drift.db")

CREATE_MEMOS = """
CREATE TABLE IF NOT EXISTS memos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at DATETIME DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'active',
    snoozed_until DATE,
    source TEXT,
    message_id INTEGER,
    chat_id INTEGER
)
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

CREATE_TRUSTED_USERS = """
CREATE TABLE IF NOT EXISTS trusted_users (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    added_at DATETIME DEFAULT (datetime('now'))
)
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_MEMOS)
        await db.execute(CREATE_SETTINGS)
        await db.execute(CREATE_TRUSTED_USERS)
        for col, col_type in [("message_id", "INTEGER"), ("chat_id", "INTEGER"), ("user_id", "INTEGER")]:
            try:
                await db.execute(f"ALTER TABLE memos ADD COLUMN {col} {col_type}")
            except aiosqlite.OperationalError:
                pass  # column already exists (existing DB)
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
