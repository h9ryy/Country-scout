import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.backup import backup_loop
from bot.handlers import admin, profile, quiz, rules, start
from bot.storage import init_db
from config import settings


async def main() -> None:
    # Логи в stdout: в панели Amvera они не будут красными
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(quiz.router)
    dp.include_router(profile.router)
    dp.include_router(rules.router)
    dp.include_router(admin.router)

    await init_db()
    backup_task = asyncio.create_task(backup_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        backup_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())