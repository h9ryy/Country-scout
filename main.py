import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.handlers import profile, quiz, start
from bot.storage import init_db
from config import settings


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(quiz.router)
    dp.include_router(profile.router)

    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())