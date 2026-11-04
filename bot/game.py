import json
import random
from dataclasses import dataclass
from pathlib import Path

from config import DATA_DIR, FLAGS_DIR

SERIES_BY_LEVEL = {1: 10, 2: 15, 3: 20}  # вопросов в одной серии
OPTIONS_BY_LEVEL = {1: 3, 2: 4, 3: 5}    # сколько вариантов ответа на уровне

# Файлы материков в том порядке, в каком они идут в меню
DATA_FILES = ["europe.json", "asia.json"]

COUNTRIES: list[dict] = []
CONTINENTS: dict[str, str] = {}
LEVELS: dict[str, str] = {}

for _filename in DATA_FILES:
    _path = DATA_DIR / _filename
    if not _path.exists():
        continue
    with open(_path, encoding="utf-8") as f:
        _data = json.load(f)
    CONTINENTS.update(_data["continents"])
    LEVELS.update(_data["levels"])
    COUNTRIES.extend(_data["countries"])

# Защита от повторов: один код может быть только в одном файле
_seen: set[str] = set()
for _c in COUNTRIES:
    if _c["code"] in _seen:
        raise ValueError(f"Повтор кода страны в данных: {_c['code']}")
    _seen.add(_c["code"])

BY_CODE: dict[str, dict] = {c["code"]: c for c in COUNTRIES}


@dataclass
class Question:
    code: str            # код верной страны
    flag_path: Path      # путь к картинке флага
    options: list[dict]  # перемешанные варианты


def get_pool(continent: str, level: int) -> list[dict]:
    """Страны материка именно этого уровня."""
    return [
        c for c in COUNTRIES
        if c["continent"] == continent and c["level"] == level
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
    return Question(
        code=code,
        flag_path=FLAGS_DIR / correct["continent"] / f"{code}.png",
        options=options,
    )


def is_correct(question_code: str, chosen_code: str) -> bool:
    return question_code == chosen_code