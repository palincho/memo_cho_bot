import os
import re
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import memo_keyboard
from db.models import (
    get_active_memos,
    get_setting,
    save_memo,
    set_setting,
    set_status,
    snooze_memo,
)
from scheduler.jobs import reschedule

ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

router = Router()


def _is_allowed(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    await message.answer(
        "Commands:\n"
        "/review — show active memos\n"
        "/time HH:MM — set daily reminder time\n"
        "/help — show this list\n\n"
        "Send any message to capture it.\n\n"
        "@memo_cho_bot"
    )


@router.message(Command("review"))
async def review_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    memos = await get_active_memos()
    if not memos:
        await message.answer("Nothing pending. Inbox clear.")
        return
    count = len(memos)
    await message.answer(f"{count} memo{'s' if count != 1 else ''}:")
    for memo in memos:
        if memo.text.startswith("voice:") and memo.chat_id and memo.message_id:
            caption = f"(from {memo.source})" if memo.source else None
            await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=memo.chat_id,
                message_id=memo.message_id,
                caption=caption,
                reply_markup=memo_keyboard(memo.id),
            )
        else:
            header = f"[{memo.id}]"
            if memo.source:
                header += f" (from {memo.source})"
            await message.answer(f"{header}\n{memo.text}", reply_markup=memo_keyboard(memo.id))


@router.message(Command("time"))
async def time_handler(message: Message, _scheduler=None) -> None:
    if not _is_allowed(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not re.match(r"^\d{2}:\d{2}$", args[1]):
        await message.answer("Usage: /time HH:MM")
        return
    time_str = args[1]
    hour, minute = map(int, time_str.split(":"))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.answer("Invalid time. Use HH:MM (24h format).")
        return
    await set_setting("reminder_time", time_str)
    scheduler = message.bot.get("scheduler")
    if scheduler:
        reschedule(scheduler, hour, minute)
    await message.answer(f"Reminder set for {time_str}.")


@router.message(F.voice)
async def voice_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    file_id = message.voice.file_id
    saved = await save_memo(f"voice:{file_id}", message_id=message.message_id, chat_id=message.chat.id)
    await message.answer("Voice stored. I'll process it later.", reply_markup=memo_keyboard(saved.id))


@router.message(F.text | F.caption | F.forward_origin)
async def message_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    text = message.text or message.caption or ""
    if not text:
        return
    source: str | None = None
    if message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, "sender_user") and origin.sender_user:
            u = origin.sender_user
            source = f"{u.first_name} {u.last_name or ''}".strip()
        elif hasattr(origin, "sender_user_name") and origin.sender_user_name:
            source = origin.sender_user_name
        elif hasattr(origin, "chat") and origin.chat:
            source = origin.chat.title
    saved = await save_memo(text, source=source, message_id=message.message_id, chat_id=message.chat.id)
    await message.answer("Got it.", reply_markup=memo_keyboard(saved.id))


async def _edit_message(callback: CallbackQuery, text: str) -> None:
    # voice/media messages have no .text — must use edit_caption instead
    if callback.message.text is None:
        await callback.message.edit_caption(caption=text)
    else:
        await callback.message.edit_text(text)


@router.callback_query(F.data.startswith("done:"))
async def callback_done(callback: CallbackQuery) -> None:
    if not _is_allowed(callback.from_user.id):
        return
    memo_id = int(callback.data.split(":")[1])
    await set_status(memo_id, "done")
    await _edit_message(callback, "Done.")
    await callback.answer()


@router.callback_query(F.data.startswith("snooze:"))
async def callback_snooze(callback: CallbackQuery) -> None:
    if not _is_allowed(callback.from_user.id):
        return
    memo_id = int(callback.data.split(":")[1])
    tomorrow = date.today() + timedelta(days=1)
    await snooze_memo(memo_id, tomorrow)
    await _edit_message(callback, f"Snoozed until tomorrow ({tomorrow.strftime('%-d %b')}).")
    await callback.answer()


@router.callback_query(F.data.startswith("letgo:"))
async def callback_letgo(callback: CallbackQuery) -> None:
    if not _is_allowed(callback.from_user.id):
        return
    memo_id = int(callback.data.split(":")[1])
    await set_status(memo_id, "dropped")
    await _edit_message(callback, "Gone.")
    await callback.answer()


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)
