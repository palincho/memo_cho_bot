import asyncio
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import register_handlers
from db.database import init_db
from scheduler.jobs import setup_scheduler


async def main() -> None:
    load_dotenv()

    bot_token = os.environ["BOT_TOKEN"]
    user_id = int(os.environ["ALLOWED_USER_ID"])

    await init_db()

    bot = Bot(token=bot_token)
    dp = Dispatcher()

    register_handlers(dp)

    scheduler = await setup_scheduler(bot, user_id)

    try:
        await dp.start_polling(bot, scheduler=scheduler)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
