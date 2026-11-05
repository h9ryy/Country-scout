"""Резервные копии базы игроков: раз в сутки присылаются админу в Telegram."""
import asyncio
import logging
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from config import DB_PATH, settings

BACKUP_EVERY_HOURS = 24


def _make_copy() -> Path:
    """Согласованная копия базы (безопасно, даже пока бот работает)."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    target = Path(tempfile.gettempdir()) / f"bot_{stamp}.db"
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    return target


async def send_backup(bot: Bot) -> bool:
    """Отправляет копию базы админу. Возвращает False, если слать нечего."""
    if not settings.admin_id or not DB_PATH.exists():
        return False
    target = await asyncio.to_thread(_make_copy)
    try:
        await bot.send_document(
            settings.admin_id,
            FSInputFile(target),
            caption="💾 Резервная копия базы игроков",
        )
    finally:
        target.unlink(missing_ok=True)
    return True


async def backup_loop(bot: Bot) -> None:
    """Присылает копию при запуске и затем раз в сутки."""
    while True:
        try:
            await send_backup(bot)
        except Exception:  # noqa: BLE001
            logging.exception("Не удалось отправить резервную копию")
        await asyncio.sleep(BACKUP_EVERY_HOURS * 3600)