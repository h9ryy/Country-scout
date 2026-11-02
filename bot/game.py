import json
import random
from dataclasses import dataclass
from pathlib import Path

from config import EUROPE_JSON, FLAGS_DIR

SERIES_BY_LEVEL = {1: 10, 2: 15, 3: 20}   # вопросов в одной серии
OPTIONS_BY_LEVEL = {1: 3, 2: 4, 3: 5}  # сколько вариантов ответа на уровне

with open(EUROPE_JSON, encoding="utf-8") as f:
    _DATA = json.load(f)

COUNTRIES: list[dict] = _DATA["countries"]
CONTINENTS: dict[str, str] = _DATA["continents"]
LEVELS: dict[str, str] = _DATA["levels"]
BY_CODE: dict[str, dict] = {c["code"]: c for c in COUNTRIES}


@dataclass
class Question:
    code: str            # код верной страны
    flag_path: Path      # путь к картинке флага
    options: list[dict]  # перемешанные варианты (страны)


def get_pool(continent: str, level: int) -> list[dict]:
    """Страны материка, доступные на этом уровне (уровни накопительные)."""
    return [
        c for c in COUNTRIES
        if c["continent"] == continent and c["level"] <= level
    ]


def new_series(continent: str, level: int) -> list[str]:
    """Коды стран для одной серии: без повторов, длина зависит от уровня."""
    pool = get_pool(continent, level)
    length = SERIES_BY_LEVEL[level]
    chosen = random.sample(pool, min(length, len(pool)))
    return [c["code"] for c in chosen]


def make_question(code: str, continent: str, level: int) -> Question:
    """Собирает вопрос: флаг + верный ответ + неверные варианты."""
    pool = get_pool(continent, level)
    correct = BY_CODE[code]
    total = min(OPTIONS_BY_LEVEL[level], len(pool))
    others = [c for c in pool if c["code"] != code]
    options = random.sample(others, total - 1) + [correct]
    random.shuffle(options)
    return Question(code=code, flag_path=FLAGS_DIR / f"{code}.png", options=options)


def is_correct(question_code: str, chosen_code: str) -> bool:
    return question_code == chosen_code