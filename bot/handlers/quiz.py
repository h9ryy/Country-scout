import asyncio
import json

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.game import BY_CODE, is_correct, make_question, new_series
from bot.keyboards import after_series_kb, main_menu_kb, options_kb
from bot.storage import (
    add_answer,
    get_balance,
    get_progress,
    record_perfect_run,
    record_series,
    revert_points,
)
from config import BASE_DIR, PERFECT_RUNS_TO_MASTER

router = Router()

# Кэш: код страны -> file_id картинки в Telegram. Хранится в файле,
# поэтому флаги не загружаются заново после перезапуска бота.
CACHE_PATH = BASE_DIR / "cache" / "file_ids.json"


def _load_cache() -> dict[str, str]:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache() -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(_file_ids), encoding="utf-8")


_file_ids: dict[str, str] = _load_cache()


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

    caption = f"Вопрос {index + 1} из {total}\nЧей это флаг?"
    markup = options_kb(question.options)

    cached = _file_ids.get(code)
    try:
        sent = await message.answer_photo(
            cached or FSInputFile(question.flag_path),
            caption=caption,
            reply_markup=markup,
        )
    except TelegramBadRequest:
        if cached is None:
            raise
        # file_id устарел: загружаем файл заново
        sent = await message.answer_photo(
            FSInputFile(question.flag_path), caption=caption, reply_markup=markup
        )

    if sent.photo:
        new_id = sent.photo[-1].file_id
        if _file_ids.get(code) != new_id:
            _file_ids[code] = new_id
            _save_cache()


async def start_series(message: Message, state: FSMContext, user_id: int) -> None:
    """Запускает серию. Решение «начислять очки или нет» принимается здесь,
    один раз на всю серию."""
    data = await state.get_data()
    continent, level = data["continent"], data["level"]

    _, mastered = await get_progress(user_id, continent, level)

    series = new_series(continent, level)
    await state.update_data(
        series=series,
        index=0,
        correct=0,
        errors=0,
        series_delta=0,
        scored=not mastered,
        current=None,
    )

    if mastered:
        await message.answer(
            "🎓 Этот уровень уже освоен.\n"
            "Играй для тренировки: очки не начисляются и не списываются."
        )
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
    scored = data.get("scored", True)

    user = callback.from_user
    old_balance = await get_balance(user.id)
    balance = await add_answer(
        user.id, user.username, ok, data["level"], scored=scored
    )
    gained = balance - old_balance

    name = BY_CODE[current]["name"]
    index = data["index"]
    total = len(data["series"])
    correct = data["correct"] + (1 if ok else 0)
    errors = data.get("errors", 0) + (0 if ok else 1)
    series_delta = data.get("series_delta", 0) + gained

    if ok:
        result = f"✅ Верно! Это {name}."
        result += f"\n+{gained} 🌐" if scored else "\n🎓 Тренировка: очки не начисляются"
    else:
        chosen_name = BY_CODE.get(chosen, {}).get("name", "другая страна")
        result = f"❌ Неверно: это {name}, а не {chosen_name}."
        if not scored:
            result += "\n🎓 Тренировка: очки не списываются"
        elif gained:
            result += f"\n{gained} 🌐"
        else:
            result += "\nБаланс не меняется: ниже 0 не опускаемся"

    edit = callback.message.edit_caption(
        caption=f"Вопрос {index + 1} из {total}\n{result}\nБаланс: {balance} 🌐",
        reply_markup=None,
    )

    index += 1
    await state.update_data(
        index=index, correct=correct, errors=errors, series_delta=series_delta
    )

    if index < total:
        # Обновление подписи и отправка следующего флага идут одновременно
        await asyncio.gather(_await(edit), send_question(callback.message, state))
        return

    await edit

    # Серия дошла до конца: обновляем прогресс уровня
    continent, level = data["continent"], data["level"]
    await record_series(user.id, continent, level, correct, total)
    if scored and errors == 0:
        runs, mastered_now = await record_perfect_run(user.id, continent, level)
    else:
        runs, mastered_now = await get_progress(user.id, continent, level)

    if mastered_now and scored:
        note = "🎓 Уровень освоен! Очки за него больше не начисляются."
    elif mastered_now:
        note = "🎓 Уровень освоен: это была тренировка."
    else:
        note = f"⭐ Безошибочных серий: {runs} из {PERFECT_RUNS_TO_MASTER}"

    await callback.message.answer(
        f"🏁 Серия окончена!\n"
        f"Верных ответов: {correct} из {total}\n"
        f"Баланс: {balance} 🌐\n"
        f"{note}",
        reply_markup=after_series_kb(),
    )


@router.callback_query(F.data == "again")
async def play_again(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "continent" not in data or "level" not in data:
        await callback.message.answer("🏠 Главное меню\nВыбери раздел:", reply_markup=main_menu_kb())
    else:
        await start_series(callback.message, state, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "stop")
async def stop_test(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()

    # Вопрос уже закрыт, тест остановлен раньше или бота перезапускали
    if data.get("current") is None:
        await callback.answer(
            "Тест уже закончен. Начни заново: /start", show_alert=True
        )
        return
    await callback.answer()
    await state.update_data(current=None)

    answered = data["index"]
    total = len(data["series"])
    correct = data["correct"]
    delta = data.get("series_delta", 0)

    # Убираем кнопки у текущего вопроса и помечаем его
    await callback.message.edit_caption(
        caption=f"{callback.message.caption or ''}\n⏹ Остановлено",
        reply_markup=None,
    )

    # Возвращаем баланс к тому, каким он был до теста
    user_id = callback.from_user.id
    if delta:
        balance = await revert_points(user_id, delta)
    else:
        balance = await get_balance(user_id)

    if delta > 0:
        refund = f"↩️ Очки за этот тест отменены: −{delta} 🌐\n"
    elif delta < 0:
        refund = f"↩️ Потери за этот тест отменены: +{-delta} 🌐\n"
    else:
        refund = ""

    await callback.message.answer(
        f"⏹ Тест остановлен.\n"
        f"Отвечено: {answered} из {total}\n"
        f"Верных ответов: {correct}\n"
        f"{refund}"
        f"Баланс: {balance} 🌐",
        reply_markup=after_series_kb(),
    )