import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("DB_PATH", ":memory:")

import db.database as database
from db.database import init_db
from db.models import (
    add_trusted_user,
    get_active_memos,
    get_active_memos_for_user,
    get_memo_owner,
    get_setting,
    is_trusted_user,
    list_trusted_users,
    remove_trusted_user,
    save_memo,
    set_setting,
    set_status,
    snooze_memo,
)


@pytest.fixture(autouse=True)
def set_in_memory_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    import db.database as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_file)


# ---------------------------------------------------------------------------
# Existing: basic capture and snooze
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_retrieve_memo():
    await init_db()
    memo = await save_memo("Hello world")
    assert memo.id is not None
    assert memo.text == "Hello world"
    assert memo.status == "active"
    active = await get_active_memos()
    assert any(m.id == memo.id for m in active)


@pytest.mark.asyncio
async def test_snoozed_memo_hidden_from_active():
    await init_db()
    memo = await save_memo("Snoozable memo")
    await snooze_memo(memo.id, date.today() + timedelta(days=1))
    active = await get_active_memos()
    assert not any(m.id == memo.id for m in active)


@pytest.mark.asyncio
async def test_snoozed_memo_reappears_when_due():
    await init_db()
    memo = await save_memo("Past snoozed memo")
    await snooze_memo(memo.id, date.today() - timedelta(days=1))
    active = await get_active_memos()
    assert any(m.id == memo.id for m in active)


# ---------------------------------------------------------------------------
# set_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_status_done_removes_from_active():
    await init_db()
    memo = await save_memo("To be done")
    await set_status(memo.id, "done")
    assert not any(m.id == memo.id for m in await get_active_memos())


@pytest.mark.asyncio
async def test_set_status_dropped_removes_from_active():
    await init_db()
    memo = await save_memo("To be dropped")
    await set_status(memo.id, "dropped")
    assert not any(m.id == memo.id for m in await get_active_memos())


# ---------------------------------------------------------------------------
# Per-user memo queries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_active_memos_for_user_isolation():
    await init_db()
    memo_a = await save_memo("Alice task", sender_id=111)
    memo_b = await save_memo("Bob task", sender_id=222)
    alice = await get_active_memos_for_user(111)
    assert any(m.id == memo_a.id for m in alice)
    assert not any(m.id == memo_b.id for m in alice)


@pytest.mark.asyncio
async def test_get_active_memos_for_user_respects_snooze():
    await init_db()
    memo = await save_memo("Snoozed user task", sender_id=111)
    await snooze_memo(memo.id, date.today() + timedelta(days=1))
    assert not any(m.id == memo.id for m in await get_active_memos_for_user(111))


@pytest.mark.asyncio
async def test_get_memo_owner_returns_sender_id():
    await init_db()
    memo = await save_memo("Owned task", sender_id=999)
    assert await get_memo_owner(memo.id) == 999


@pytest.mark.asyncio
async def test_get_memo_owner_missing_returns_none():
    await init_db()
    assert await get_memo_owner(99999) is None


# ---------------------------------------------------------------------------
# Trusted users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trusted_user_crud():
    await init_db()
    assert not await is_trusted_user(42)
    await add_trusted_user(42, "Bob")
    assert await is_trusted_user(42)
    users = await list_trusted_users()
    assert any(uid == 42 for uid, _ in users)
    await remove_trusted_user(42)
    assert not await is_trusted_user(42)


@pytest.mark.asyncio
async def test_add_trusted_user_upserts_name():
    await init_db()
    await add_trusted_user(7, "Old Name")
    await add_trusted_user(7, "New Name")
    users = await list_trusted_users()
    names = {name for _, name in users if _ == 7}
    assert names == {"New Name"}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_setting_missing_returns_none():
    await init_db()
    assert await get_setting("nonexistent") is None


@pytest.mark.asyncio
async def test_settings_round_trip():
    await init_db()
    await set_setting("reminder_time", "09:00")
    assert await get_setting("reminder_time") == "09:00"


@pytest.mark.asyncio
async def test_settings_upsert():
    await init_db()
    await set_setting("reminder_time", "08:00")
    await set_setting("reminder_time", "10:30")
    assert await get_setting("reminder_time") == "10:30"
