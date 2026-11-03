from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.game import LEVELS
from bot.keyboards import rules_kb
from config import PERFECT_RUNS_TO_MASTER, SCORES_BY_LEVEL

router = Router()


def build_rules_text() -> str:
    score_lines = []
    for level, name in LEVELS.items():
        reward, penalty = SCORES_BY_LEVEL[int(level)]
        score_lines.append(
            f"• {name}: +{reward} за верный ответ, −{abs(penalty)} за ошибку"
        )

    parts = [
        "📖 Система очков",
        "",
        "🌐 За что дают очки",
        *score_lines,
        "• Баланс не опускается ниже 0.",
        "",
        "↩️ Когда очки отменяются",
        "• Если остановить тест кнопкой «⏹», очки за этот тест отменяются: "
        "и заработанные, и потерянные. Баланс возвращается к тому, "
        "каким был до теста.",
        "• Тест, доведённый до последнего вопроса, остаётся в зачёте.",
        "",
        "🎓 Когда очки перестают начисляться",
        f"• Пройди серию без единой ошибки {PERFECT_RUNS_TO_MASTER} раза: "
        "уровень будет освоен.",
        "• На освоенном уровне очки не начисляются и не списываются: "
        "это тренировка.",
        "• Вторая безошибочная серия ещё приносит очки, освоение "
        "действует со следующей.",
        "• Освоение считается отдельно для каждого материка и уровня. "
        "Остановленные тесты в зачёт не идут.",
    ]
    return "\n".join(parts)


@router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery) -> None:
    await callback.message.edit_text(build_rules_text(), reply_markup=rules_kb())
    await callback.answer()


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(build_rules_text(), reply_markup=rules_kb())