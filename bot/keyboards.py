from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.game import CONTINENTS, LEVELS, SERIES_BY_LEVEL, get_pool
from config import PERFECT_RUNS_TO_MASTER

# Материки, которые готовятся: кнопка есть, игра пока недоступна.
# Когда появятся данные, материк убираем отсюда.
COMING_SOON = {"asia": "Азия"}


def _questions_word(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "вопрос"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "вопроса"
    return "вопросов"


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌍 Флаги", callback_data="countries")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="📖 Система очков", callback_data="rules")
    kb.adjust(1)
    return kb.as_markup()


def continents_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, name in CONTINENTS.items():
        icon = "🌏" if key == "asia" else "🌍"
        kb.button(text=f"{icon} {name}", callback_data=f"cont:{key}")
    for key, name in COMING_SOON.items():
        if key not in CONTINENTS:
            kb.button(text=f"🌏 {name} · скоро", callback_data=f"soon:{key}")
    kb.button(text="⬅️ Назад", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def levels_kb(
    continent: str, progress: dict[int, tuple[int, bool]]
) -> InlineKeyboardMarkup:
    """progress[уровень] = (безошибочных серий, освоен ли уровень)."""
    kb = InlineKeyboardBuilder()
    for level, name in LEVELS.items():
        pool = get_pool(continent, int(level))
        n = min(SERIES_BY_LEVEL[int(level)], len(pool))  # сколько реально вопросов
        text = f"{name} · {n} {_questions_word(n)}"

        runs, mastered = progress.get(int(level), (0, False))
        if mastered:
            text += " · ✅ освоено"
        elif runs > 0:
            text += f" · ⭐ {runs}/{PERFECT_RUNS_TO_MASTER}"

        kb.button(text=text, callback_data=f"lvl:{level}")
    kb.button(text="⬅️ Назад", callback_data="countries")
    kb.adjust(1)
    return kb.as_markup()


def options_kb(options: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки с названиями + кнопка остановки теста."""
    kb = InlineKeyboardBuilder()
    for country in options:
        kb.button(text=country["name"], callback_data=f"ans:{country['code']}")
    kb.button(text="⏹ Остановить тест", callback_data="stop")
    kb.adjust(1)
    return kb.as_markup()


def after_series_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Играть ещё", callback_data="again")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 В меню", callback_data="menu")
    return kb.as_markup()


def rules_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌍 Играть", callback_data="countries")
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()