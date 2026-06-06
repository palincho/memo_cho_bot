import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from bot.keyboards import memo_keyboard
from db.models import get_active_memos, get_setting

JOB_ID = "daily_review"


async def send_daily_review(bot: Bot, user_id: int) -> None:
    memos = await get_active_memos()
    if not memos:
        await bot.send_message(user_id, "All clear. Nothing pending.")
        return
    for memo in memos:
        if memo.text.startswith("voice:") and memo.chat_id and memo.message_id:
            caption = f"(from {memo.source})" if memo.source else None
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=memo.chat_id,
                message_id=memo.message_id,
                caption=caption,
                reply_markup=memo_keyboard(memo.id),
            )
        else:
            header = f"[{memo.id}]"
            if memo.source:
                header += f" (from {memo.source})"
            await bot.send_message(user_id, f"{header}\n{memo.text}", reply_markup=memo_keyboard(memo.id))


async def setup_scheduler(bot: Bot, user_id: int) -> AsyncIOScheduler:
    default_time = os.getenv("REMINDER_TIME", "08:00")
    stored = await get_setting("reminder_time")
    time_str = stored or default_time
    hour, minute = map(int, time_str.split(":"))

    scheduler = AsyncIOScheduler()
    _add_job(scheduler, bot, user_id, hour, minute)
    scheduler.start()
    return scheduler


def reschedule(scheduler: AsyncIOScheduler, hour: int, minute: int, bot: Bot | None = None, user_id: int | None = None) -> None:
    existing = scheduler.get_job(JOB_ID)
    if existing:
        existing_kwargs = existing.kwargs
        bot = bot or existing_kwargs.get("bot")
        user_id = user_id or existing_kwargs.get("user_id")
        scheduler.remove_job(JOB_ID)
    _add_job(scheduler, bot, user_id, hour, minute)


def _add_job(scheduler: AsyncIOScheduler, bot: Bot, user_id: int, hour: int, minute: int) -> None:
    scheduler.add_job(
        send_daily_review,
        trigger=CronTrigger(hour=hour, minute=minute),
        id=JOB_ID,
        kwargs={"bot": bot, "user_id": user_id},
    )
