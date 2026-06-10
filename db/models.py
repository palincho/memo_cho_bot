from dataclasses import dataclass
from datetime import date, datetime

import aiosqlite

from db.database import get_db


@dataclass
class Memo:
    id: int
    text: str
    created_at: datetime
    status: str
    snoozed_until: date | None
    sender_name: str | None
    message_id: int | None
    chat_id: int | None
    sender_id: int | None = None


async def save_memo(
    text: str,
    sender_name: str | None = None,
    message_id: int | None = None,
    chat_id: int | None = None,
    sender_id: int | None = None,
) -> Memo:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO memos (text, sender_name, message_id, chat_id, sender_id) VALUES (?, ?, ?, ?, ?)",
            (text, sender_name, message_id, chat_id, sender_id),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM memos WHERE id = ?", (cursor.lastrowid,)
        )).fetchone()
    return _row_to_memo(row)


async def get_memo(memo_id: int) -> Memo | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM memos WHERE id = ?", (memo_id,))
        row = await cursor.fetchone()
    return _row_to_memo(row) if row else None


async def get_active_memos_for_user(sender_id: int) -> list[Memo]:
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM memos
            WHERE status = 'active'
              AND sender_id = ?
              AND (snoozed_until IS NULL OR snoozed_until <= ?)
            ORDER BY created_at ASC
            """,
            (sender_id, today),
        )
        rows = await cursor.fetchall()
    return [_row_to_memo(r) for r in rows]


async def get_memo_owner(memo_id: int) -> int | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT sender_id FROM memos WHERE id = ?", (memo_id,))
        row = await cursor.fetchone()
    return row["sender_id"] if row else None


async def get_active_memos() -> list[Memo]:
    today = date.today().isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM memos
            WHERE status = 'active'
              AND (snoozed_until IS NULL OR snoozed_until <= ?)
            ORDER BY created_at ASC
            """,
            (today,),
        )
        rows = await cursor.fetchall()
    return [_row_to_memo(r) for r in rows]


async def set_status(memo_id: int, status: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE memos SET status = ? WHERE id = ?",
            (status, memo_id),
        )
        await db.commit()


async def snooze_memo(memo_id: int, until: date) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE memos SET snoozed_until = ? WHERE id = ?",
            (until.isoformat(), memo_id),
        )
        await db.commit()


async def get_setting(key: str) -> str | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
    return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def add_trusted_user(user_id: int, name: str) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO trusted_users (user_id, name) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET name = excluded.name",
            (user_id, name),
        )
        await db.commit()


async def remove_trusted_user(user_id: int) -> None:
    async with get_db() as db:
        await db.execute("DELETE FROM trusted_users WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_trusted_user(user_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT 1 FROM trusted_users WHERE user_id = ?", (user_id,)
        )
        return await cursor.fetchone() is not None


async def list_trusted_users() -> list[tuple[int, str]]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT user_id, name FROM trusted_users ORDER BY added_at ASC"
        )
        rows = await cursor.fetchall()
    return [(row["user_id"], row["name"]) for row in rows]


def _row_to_memo(row: aiosqlite.Row) -> Memo:
    return Memo(
        id=row["id"],
        text=row["text"],
        created_at=datetime.fromisoformat(row["created_at"]),
        status=row["status"],
        snoozed_until=date.fromisoformat(row["snoozed_until"]) if row["snoozed_until"] else None,
        sender_name=row["sender_name"],
        message_id=row["message_id"],
        chat_id=row["chat_id"],
        sender_id=row["sender_id"],
    )
