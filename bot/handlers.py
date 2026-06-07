import os
import re
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import memo_keyboard, undo_keyboard
from db.models import (
    add_trusted_user,
    get_active_memos,
    get_setting,
    is_trusted_user,
    list_trusted_users,
    remove_trusted_user,
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
    if await is_trusted_user(message.from_user.id):
        await message.answer("Send me any message and I'll add it to the task list.")
        return
    if not _is_allowed(message.from_user.id):
        return
    await message.answer(
        "Commands:\n"
        "/review — show active memos\n"
        "/time HH:MM — set daily reminder time\n"
        "/setsecret <word> — set passphrase to self-register\n"
        "/adduser <id> [name] — manually allow someone\n"
        "/removeuser <id> — revoke access\n"
        "/listusers — show trusted senders\n"
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
            caption = f"(from {memo.sender_name})" if memo.sender_name else None
            await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=memo.chat_id,
                message_id=memo.message_id,
                caption=caption,
                reply_markup=memo_keyboard(memo.id),
            )
        else:
            header = f"[{memo.id}]"
            if memo.sender_name:
                header += f" (from {memo.sender_name})"
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


@router.message(Command("adduser"))
async def adduser_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Usage: /adduser <user_id> [name]")
        return
    user_id = int(parts[1])
    name = parts[2] if len(parts) > 2 else str(user_id)
    await add_trusted_user(user_id, name)
    await message.answer(f"Added {name} ({user_id}).")


@router.message(Command("removeuser"))
async def removeuser_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Usage: /removeuser <user_id>")
        return
    user_id = int(parts[1])
    await remove_trusted_user(user_id)
    await message.answer(f"Removed {user_id}.")


@router.message(Command("listusers"))
async def listusers_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    users = await list_trusted_users()
    if not users:
        await message.answer("No trusted senders yet.")
        return
    lines = "\n".join(f"• {name} ({uid})" for uid, name in users)
    await message.answer(f"Trusted senders:\n{lines}")


@router.message(Command("setsecret"))
async def setsecret_handler(message: Message) -> None:
    if not _is_allowed(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /setsecret <word>")
        return
    word = parts[1].strip()
    await set_setting("secret_word", word)
    await message.answer(f"Secret word set. Share it with anyone you want to allow.")


@router.message(F.voice)
async def voice_handler(message: Message) -> None:
    if await is_trusted_user(message.from_user.id):
        file_id = message.voice.file_id
        saved = await save_memo(f"voice:{file_id}", sender_name=message.from_user.first_name, message_id=message.message_id, chat_id=message.chat.id, sender_id=message.from_user.id)
        await message.answer("Task sent.", reply_markup=undo_keyboard(saved.id))
        return
    if not _is_allowed(message.from_user.id):
        return
    file_id = message.voice.file_id
    saved = await save_memo(f"voice:{file_id}", message_id=message.message_id, chat_id=message.chat.id, sender_id=message.from_user.id)
    await message.answer("Voice stored. I'll process it later.", reply_markup=memo_keyboard(saved.id))


@router.message(F.text | F.caption | F.forward_origin)
async def message_handler(message: Message) -> None:
    is_owner = _is_allowed(message.from_user.id)
    is_trusted = await is_trusted_user(message.from_user.id)

    if not is_owner and not is_trusted:
        await _try_secret_word(message)
        return

    text = message.text or message.caption or ""
    if not text:
        return
    sender_name: str | None = None
    if is_trusted:
        sender_name = message.from_user.first_name
    elif message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, "sender_user") and origin.sender_user:
            u = origin.sender_user
            sender_name = f"{u.first_name} {u.last_name or ''}".strip()
        elif hasattr(origin, "sender_user_name") and origin.sender_user_name:
            sender_name = origin.sender_user_name
        elif hasattr(origin, "chat") and origin.chat:
            sender_name = origin.chat.title
    saved = await save_memo(text, sender_name=sender_name, message_id=message.message_id, chat_id=message.chat.id, sender_id=message.from_user.id)
    if is_trusted:
        await message.answer("Task sent.", reply_markup=undo_keyboard(saved.id))
    else:
        await message.answer("Got it.", reply_markup=memo_keyboard(saved.id))


async def _try_secret_word(message: Message) -> None:
    secret = await get_setting("secret_word")
    if not secret:
        return
    text = (message.text or "").strip()
    if text.lower() != secret.lower():
        return
    user = message.from_user
    name = f"{user.first_name} {user.last_name or ''}".strip()
    await add_trusted_user(user.id, name)
    await message.answer("Access granted. You can now send tasks.")


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


@router.callback_query(F.data.startswith("undo:"))
async def callback_undo(callback: CallbackQuery) -> None:
    if not await is_trusted_user(callback.from_user.id):
        return
    memo_id = int(callback.data.split(":")[1])
    await set_status(memo_id, "dropped")
    await callback.message.edit_text("Cancelled.")
    await callback.answer()


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)
