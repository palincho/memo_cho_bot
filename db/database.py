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
    source TEXT
)
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_MEMOS)
        await db.execute(CREATE_SETTINGS)
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
