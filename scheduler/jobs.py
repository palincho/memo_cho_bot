import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from bot.utils import send_memo
from db.models import get_active_memos, get_setting

JOB_ID = "daily_review"


async def send_daily_review(bot: Bot, user_id: int) -> None:
    memos = await get_active_memos()
    if not memos:
        await bot.send_message(user_id, "All clear. Nothing pending.")
        return
    for memo in memos:
        await send_memo(bot, user_id, memo)


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
