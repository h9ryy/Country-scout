from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.game import CONTINENTS, LEVELS
from bot.handlers.quiz import start_series
from bot.keyboards import continents_kb, levels_kb
from bot.storage import get_progress
from config import SCORES_BY_LEVEL

router = Router()

WELCOME = (
    "🌍 Привет! Угадывай страны по флагам и зарабатывай глобусы 🌐.\n"
    "Очки зависят от уровня: чем сложнее, тем дороже ошибка.\n\n"
    "Выбери материк:"
)


def _rules_text() -> str:
    """Блок «верно / ошибка» по уровням, берётся из config.py."""
    lines = []
    for level, name in LEVELS.items():
        reward, penalty = SCORES_BY_LEVEL[int(level)]
        lines.append(f"{name}: +{reward} / −{abs(penalty)} 🌐")
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=continents_kb())


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Выбери материк:", reply_markup=continents_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("cont:"))
async def choose_continent(callback: CallbackQuery, state: FSMContext) -> None:
    continent = callback.data.split(":", 1)[1]
    if continent not in CONTINENTS:
        await callback.answer("Такого материка нет", show_alert=True)
        return
    await state.update_data(continent=continent)

    user_id = callback.from_user.id
    progress = {
        int(level): await get_progress(user_id, continent, int(level))
        for level in LEVELS
    }

    await callback.message.edit_text(
        f"{CONTINENTS[continent]}. Выбери уровень:\n\n"
        f"За верный ответ / за ошибку:\n{_rules_text()}",
        reply_markup=levels_kb(continent, progress),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lvl:"))
async def choose_level(callback: CallbackQuery, state: FSMContext) -> None:
    level = callback.data.split(":", 1)[1]
    data = await state.get_data()
    continent = data.get("continent")

    # Состояние теряется, если бота перезапустили: начинаем заново
    if continent is None or level not in LEVELS:
        await callback.message.edit_text(
            "Начнём заново. Выбери материк:", reply_markup=continents_kb()
        )
        await callback.answer()
        return

    await state.update_data(level=int(level))
    await callback.message.edit_text(
        f"✅ {CONTINENTS[continent]} · {LEVELS[level]}\nПоехали! 🚀"
    )
    await callback.answer()
    await start_series(callback.message, state, callback.from_user.id)