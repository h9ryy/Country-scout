from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.backup import send_backup
from config import settings

router = Router()


@router.message(Command("backup"))
async def cmd_backup(message: Message) -> None:
    """Прислать копию базы прямо сейчас. Работает только для админа."""
    if not settings.admin_id or message.from_user.id != settings.admin_id:
        return  # чужим не отвечаем
    if not await send_backup(message.bot):
        await message.answer("Базы пока нет.")