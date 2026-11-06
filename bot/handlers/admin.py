import asyncio
import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.backup import send_backup
from bot.handlers.quiz import warm_cache
from bot.storage import get_admin_stats
from config import settings

router = Router()

# Ссылки на фоновые задачи, чтобы их не удалил сборщик мусора
_tasks: set[asyncio.Task] = set()


def _is_admin(message: Message) -> bool:
    return bool(settings.admin_id) and message.from_user.id == settings.admin_id


@router.message(Command("backup"))
async def cmd_backup(message: Message) -> None:
    """Прислать копию базы прямо сейчас."""
    if not _is_admin(message):
        return  # чужим не отвечаем
    if not await send_backup(message.bot):
        await message.answer("Базы пока нет.")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Сводка по базе: сколько игроков, серий и ответов."""
    if not _is_admin(message):
        return
    s = await get_admin_stats()
    await message.answer(
        f"📊 Игроков: {s['players']}\n"
        f"📝 Завершённых серий: {s['series']}\n"
        f"🔢 Всего ответов: {s['answers']}\n"
        f"🌐 Глобусов у всех: {s['globes']}"
    )


async def _run_warmup(bot: Bot, chat_id: int) -> None:
    try:
        n = await warm_cache(bot, chat_id)
        await bot.send_message(chat_id, f"✅ Кэш флагов готов. Загружено новых: {n}")
    except Exception:  # noqa: BLE001
        logging.exception("Прогрев кэша флагов не удался")
        await bot.send_message(chat_id, "❌ Прогрев не удался, смотри логи.")


@router.message(Command("warmup"))
async def cmd_warmup(message: Message) -> None:
    """Загрузить все флаги в Telegram заранее, чтобы игра работала быстрее."""
    if not _is_admin(message):
        return
    await message.answer(
        "⏳ Загружаю флаги в Telegram, это займёт несколько минут. "
        "Игра в это время работает как обычно."
    )
    task = asyncio.create_task(_run_warmup(message.bot, message.chat.id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)