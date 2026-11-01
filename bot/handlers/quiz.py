import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.game import BY_CODE, is_correct, make_question, new_series
from bot.keyboards import after_series_kb, continents_kb, options_kb
from bot.storage import add_answer, get_balance

router = Router()

# Кэш: код страны -> file_id картинки в Telegram (флаг грузится один раз)
_file_ids: dict[str, str] = {}


async def _await(method) -> None:
    """Обёртка: asyncio.gather не принимает методы aiogram напрямую."""
    await method


async def send_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    index = data["index"]
    total = len(data["series"])
    code = data["series"][index]

    question = make_question(code, data["continent"], data["level"])
    await state.update_data(current=code)

    photo = _file_ids.get(code) or FSInputFile(question.flag_path)
    sent = await message.answer_photo(
        photo,
        caption=f"Вопрос {index + 1} из {total}\nКакая это страна?",
        reply_markup=options_kb(question.options),
    )
    if code not in _file_ids:
        _file_ids[code] = sent.photo[-1].file_id


async def start_series(message: Message, state: FSMContext) -> None:
    """Запускает новую серию с материком и уровнем из состояния."""
    data = await state.get_data()
    series = new_series(data["continent"], data["level"])
    await state.update_data(series=series, index=0, correct=0, current=None)
    await send_question(message, state)


@router.callback_query(F.data.startswith("ans:"))
async def answer(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    current = data.get("current")

    # Вопрос уже закрыт (двойное нажатие) или бота перезапускали
    if current is None:
        await callback.answer(
            "Этот вопрос уже закрыт. Начни заново: /start", show_alert=True
        )
        return
    await callback.answer()  # сразу гасим индикатор загрузки на кнопке
    await state.update_data(current=None)

    chosen = callback.data.split(":", 1)[1]
    ok = is_correct(current, chosen)

    user = callback.from_user
    old_balance = await get_balance(user.id)
    balance = await add_answer(user.id, user.username, ok)
    gained = balance - old_balance

    name = BY_CODE[current]["name"]
    index = data["index"]
    total = len(data["series"])
    correct = data["correct"] + (1 if ok else 0)

    if ok:
        result = f"✅ Верно! Это {name}.\n+{gained} 🌐"
    else:
        chosen_name = BY_CODE.get(chosen, {}).get("name", "другая страна")
        change = f"{gained} 🌐" if gained else "Баланс не меняется: ниже 0 не опускаемся"
        result = f"❌ Неверно: это {name}, а не {chosen_name}.\n{change}"

    edit = callback.message.edit_caption(
        caption=f"Вопрос {index + 1} из {total}\n{result}\nБаланс: {balance} 🌐",
        reply_markup=None,
    )

    index += 1
    await state.update_data(index=index, correct=correct)

    if index < total:
        # Обновление подписи и отправка следующего флага идут одновременно
        await asyncio.gather(_await(edit), send_question(callback.message, state))
    else:
        await edit
        await callback.message.answer(
            f"🏁 Серия окончена!\n"
            f"Верных ответов: {correct} из {total}\n"
            f"Баланс: {balance} 🌐",
            reply_markup=after_series_kb(),
        )


@router.callback_query(F.data == "again")
async def play_again(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "continent" not in data or "level" not in data:
        await callback.message.answer("Выбери материк:", reply_markup=continents_kb())
    else:
        await start_series(callback.message, state)
    await callback.answer()