from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.game import CONTINENTS, LEVELS
from bot.handlers.quiz import start_series
from bot.keyboards import COMING_SOON, continents_kb, levels_kb, main_menu_kb
from bot.storage import get_progress
from bot.ui import new_screen, replace_screen

router = Router()

WELCOME = (
    "🌍 Привет! Угадывай флаги мира и зарабатывай глобусы 🌐.\n"
    "Очки зависят от уровня: чем сложнее, тем дороже ошибка.\n\n"
    "Выбери раздел:"
)
MENU_TEXT = "🏠 Главное меню\nВыбери раздел:"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await new_screen(message, WELCOME, main_menu_kb(), delete_user_message=True)


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await replace_screen(callback.message, MENU_TEXT, main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "countries")
async def show_countries(callback: CallbackQuery) -> None:
    await replace_screen(callback.message, "🌍 Выбери материк:", continents_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("soon:"))
async def coming_soon(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    name = COMING_SOON.get(key, "Этот раздел")
    await callback.answer(
        f"🌏 {name} скоро появится: мы уже готовим флаги!", show_alert=True
    )


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

    await replace_screen(
        callback.message,
        f"{CONTINENTS[continent]}. Выбери уровень:",
        levels_kb(continent, progress),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lvl:"))
async def choose_level(callback: CallbackQuery, state: FSMContext) -> None:
    level = callback.data.split(":", 1)[1]
    data = await state.get_data()
    continent = data.get("continent")

    # Состояние теряется, если бота перезапустили: начинаем заново
    if continent is None or level not in LEVELS:
        await replace_screen(
            callback.message, "Начнём заново. Выбери материк:", continents_kb()
        )
        await callback.answer()
        return

    await state.update_data(level=int(level))
    await callback.answer()
    # Меню уровней заменяется первым флагом серии
    await start_series(callback.message, state, callback.from_user.id)