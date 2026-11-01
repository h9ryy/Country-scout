from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.quiz import start_series
from bot.game import CONTINENTS, LEVELS
from bot.keyboards import continents_kb, levels_kb

router = Router()

WELCOME = (
    "🌍 Привет! Угадывай страны по флагам.\n"
    "Верный ответ: +3 🌐, ошибка: −1 🌐.\n\n"
    "Выбери материк:"
)


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
    await callback.message.edit_text(
        f"{CONTINENTS[continent]}. Выбери уровень:",
        reply_markup=levels_kb(continent),
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
    await start_series(callback.message, state)