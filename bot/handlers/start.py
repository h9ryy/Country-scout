from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.game import CONTINENTS, LEVELS
from bot.handlers.quiz import start_series
from bot.keyboards import COMING_SOON, continents_kb, levels_kb, main_menu_kb
from bot.storage import get_progress

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
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(MENU_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "countries")
async def show_countries(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🌍 Выбери материк:", reply_markup=continents_kb()
    )
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

    await callback.message.edit_text(
        f"{CONTINENTS[continent]}. Выбери уровень:",
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