import asyncio
import os
from datetime import date, timedelta

import pytest
import pytest_asyncio

os.environ.setdefault("DB_PATH", ":memory:")

import db.database as database
from db.database import init_db
from db.models import get_active_memos, save_memo, snooze_memo


@pytest.fixture(autouse=True)
def set_in_memory_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setattr(database, "DB_PATH", db_file)
    import db.models as models_module
    import db.database as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_file)


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

    tomorrow = date.today() + timedelta(days=1)
    await snooze_memo(memo.id, tomorrow)

    active = await get_active_memos()
    assert not any(m.id == memo.id for m in active)


@pytest.mark.asyncio
async def test_snoozed_memo_reappears_when_due():
    await init_db()
    memo = await save_memo("Past snoozed memo")

    yesterday = date.today() - timedelta(days=1)
    await snooze_memo(memo.id, yesterday)

    active = await get_active_memos()
    assert any(m.id == memo.id for m in active)
