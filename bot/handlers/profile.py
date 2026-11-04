from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.game import CONTINENTS, LEVELS
from bot.keyboards import profile_kb
from bot.storage import get_mastered, get_series_stats, get_stats
from bot.ui import new_screen, replace_screen

router = Router()


def _mastered_text(mastered: list[tuple[str, int]]) -> str:
    """Европа · Лёгкий, Средний, Сложный (каждый материк в своей строке)."""
    by_continent: dict[str, list[str]] = {}
    for continent, level in mastered:
        by_continent.setdefault(continent, []).append(LEVELS.get(str(level), str(level)))

    lines = [
        f"{CONTINENTS.get(continent, continent)} · {', '.join(levels)}"
        for continent, levels in by_continent.items()
    ]
    if not lines:
        return "🎓 Освоено: пока ничего"
    if len(lines) == 1:
        return f"🎓 Освоено: {lines[0]}"
    return "🎓 Освоено:\n" + "\n".join(lines)


async def build_profile_text(user_id: int) -> str:
    globes, correct, wrong = await get_stats(user_id)
    tests, avg = await get_series_stats(user_id)
    mastered = await get_mastered(user_id)

    avg_text = f"{round(avg)}%" if tests else "—"
    return (
        "👤 Профиль\n"
        f"🌐 Глобусов: {globes}\n"
        f"📝 Тестов решено: {tests}\n"
        f"🎯 Средний результат: {avg_text}\n"
        f"✅ Верных ответов: {correct}\n"
        f"❌ Ошибок: {wrong}\n"
        f"{_mastered_text(mastered)}"
    )


@router.message(Command("profile", "globes"))
async def cmd_profile(message: Message) -> None:
    text = await build_profile_text(message.from_user.id)
    await new_screen(message, text, profile_kb(), delete_user_message=True)


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery) -> None:
    text = await build_profile_text(callback.from_user.id)
    await replace_screen(callback.message, text, profile_kb())
    await callback.answer()