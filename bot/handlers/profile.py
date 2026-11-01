from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.storage import get_stats

router = Router()


@router.message(Command("globes"))
async def cmd_globes(message: Message) -> None:
    globes, correct, wrong = await get_stats(message.from_user.id)
    total = correct + wrong
    percent = round(correct / total * 100) if total else 0
    await message.answer(
        f"🌐 Твой баланс: {globes}\n"
        f"✅ Верных ответов: {correct}\n"
        f"❌ Ошибок: {wrong}\n"
        f"🎯 Точность: {percent}%"
    )