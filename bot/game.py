import json
import random
from dataclasses import dataclass
from pathlib import Path

from config import DATA_DIR, FLAGS_DIR

SERIES_BY_LEVEL = {1: 10, 2: 15, 3: 20}  # длина серии по умолчанию
OPTIONS_BY_LEVEL = {1: 3, 2: 4, 3: 5}    # сколько вариантов ответа на уровне

# Порядок материков в меню. Новый материк: положи data/<ключ>.json;
# если ключа нет в списке, материк встанет в конец меню.
CONTINENT_ORDER = [
    "europe", "asia", "africa", "north_america", "south_america", "oceania",
]


def _sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    idx = CONTINENT_ORDER.index(stem) if stem in CONTINENT_ORDER else len(CONTINENT_ORDER)
    return idx, stem


COUNTRIES: list[dict] = []
CONTINENTS: dict[str, str] = {}
LEVELS: dict[str, str] = {}
POOL_MODE: dict[str, object] = {}       # материк -> "exact"/"cumulative" или {"1": ..., ...}
SERIES_OVERRIDES: dict[str, dict] = {}  # материк -> {"1": 5, "3": "all", ...}

for _path in sorted(DATA_DIR.glob("*.json"), key=_sort_key):
    with open(_path, encoding="utf-8") as f:
        _data = json.load(f)
    _settings = _data.get("settings", {})
    for _key, _name in _data["continents"].items():
        CONTINENTS[_key] = _name
        POOL_MODE[_key] = _settings.get("pool_mode", "exact")
        SERIES_OVERRIDES[_key] = _settings.get("series", {})
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


def _pool_mode(continent: str, level: int) -> str:
    mode = POOL_MODE.get(continent, "exact")
    if isinstance(mode, dict):
        return mode.get(str(level), "exact")
    return mode


def get_pool(continent: str, level: int) -> list[dict]:
    """Страны материка для уровня.

    exact: только страны этого уровня.
    cumulative: страны этого и более лёгких уровней.
    """
    cumulative = _pool_mode(continent, level) == "cumulative"
    return [
        c for c in COUNTRIES
        if c["continent"] == continent
        and (c["level"] <= level if cumulative else c["level"] == level)
    ]


def series_length(continent: str, level: int) -> int:
    """Сколько вопросов в серии на этом материке и уровне."""
    pool_size = len(get_pool(continent, level))
    setting = SERIES_OVERRIDES.get(continent, {}).get(str(level))
    if setting == "all":
        return pool_size
    if isinstance(setting, int):
        return min(setting, pool_size)
    return min(SERIES_BY_LEVEL[level], pool_size)


def new_series(continent: str, level: int) -> list[str]:
    """Коды стран для одной серии: без повторов."""
    pool = get_pool(continent, level)
    chosen = random.sample(pool, series_length(continent, level))
    return [c["code"] for c in chosen]


def make_question(code: str, continent: str, level: int) -> Question:
    """Собирает вопрос: флаг + верный ответ + неверные варианты."""
    pool = get_pool(continent, level)
    correct = BY_CODE[code]
    need = OPTIONS_BY_LEVEL[level] - 1  # сколько нужно неверных вариантов

    others = [c for c in pool if c["code"] != code]
    if len(others) < need:
        # В пуле уровня мало стран: добираем из всего материка
        have = {c["code"] for c in others}
        extra = [
            c for c in COUNTRIES
            if c["continent"] == continent
            and c["code"] != code
            and c["code"] not in have
        ]
        random.shuffle(extra)
        others += extra[: need - len(others)]

    options = random.sample(others, min(need, len(others))) + [correct]
    random.shuffle(options)
    return Question(
        code=code,
        flag_path=FLAGS_DIR / correct["continent"] / f"{code}.png",
        options=options,
    )


def is_correct(question_code: str, chosen_code: str) -> bool:
    return question_code == chosen_code