from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.game import CONTINENTS, LEVELS, get_pool


def continents_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, name in CONTINENTS.items():
        kb.button(text=f"🌍 {name}", callback_data=f"cont:{key}")
    kb.adjust(1)
    return kb.as_markup()


def levels_kb(continent: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for level, name in LEVELS.items():
        count = len(get_pool(continent, int(level)))
        kb.button(text=f"{name} · {count} стран", callback_data=f"lvl:{level}")
    kb.button(text="⬅️ Назад", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def options_kb(options: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки с названиями стран для вопроса (понадобятся в quiz.py)."""
    kb = InlineKeyboardBuilder()
    for country in options:
        kb.button(text=country["name"], callback_data=f"ans:{country['code']}")
    kb.adjust(1)
    return kb.as_markup()


def after_series_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Играть ещё", callback_data="again")
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()