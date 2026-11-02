from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.game import CONTINENTS, LEVELS
from bot.storage import get_mastered, get_stats

router = Router()


@router.message(Command("globes"))
async def cmd_globes(message: Message) -> None:
    user_id = message.from_user.id
    globes, correct, wrong = await get_stats(user_id)
    total = correct + wrong
    percent = round(correct / total * 100) if total else 0

    text = (
        f"🌐 Твой баланс: {globes}\n"
        f"✅ Верных ответов: {correct}\n"
        f"❌ Ошибок: {wrong}\n"
        f"🎯 Точность: {percent}%"
    )

    mastered = await get_mastered(user_id)
    if mastered:
        lines = [
            f"• {CONTINENTS.get(continent, continent)} · {LEVELS.get(str(level), level)}"
            for continent, level in mastered
        ]
        text += "\n\n🎓 Освоено:\n" + "\n".join(lines)

    await message.answer(text)