"""Полная проверка проекта. Запуск: python tools/verify_all.py"""
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
 
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
 
from PIL import Image
 
problems: list[str] = []
warnings: list[str] = []
 
 
def bad(msg: str) -> None:
    if msg not in problems:  # одинаковые сообщения показываем один раз
        problems.append(msg)
        print("❌", msg)
 
 
def warn(msg: str) -> None:
    if msg not in warnings:
        warnings.append(msg)
        print("⚠️ ", msg)
 
 
def good(msg: str) -> None:
    print("✅", msg)
 
 
# ---------- 1. Загрузка игры (внутри проверка повторов кодов) ----------
try:
    from bot import game
except Exception as e:  # noqa: BLE001
    print("❌ bot.game не загрузился:", repr(e))
    sys.exit(1)
good(f"bot.game загружен: материков {len(game.CONTINENTS)}, флагов {len(game.COUNTRIES)}")
 
DATA_DIR, FLAGS_DIR = game.DATA_DIR, game.FLAGS_DIR
CODE_RE = re.compile(r"^[a-z]{2}(-[a-z]{2,3})?$")
valid_modes = {"exact", "cumulative"}
 
# ---------- 2. Файлы данных ----------
print("\n--- Файлы данных ---")
for path in sorted(DATA_DIR.glob("*.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        bad(f"{path.name}: некорректный JSON ({e})")
        continue
 
    for key in ("continents", "levels", "countries"):
        if key not in data:
            bad(f"{path.name}: нет раздела '{key}'")
    if list(data.get("continents", {})) != [path.stem]:
        bad(f"{path.name}: ключ материка {list(data.get('continents', {}))} "
            f"не совпадает с именем файла '{path.stem}'")
 
    settings = data.get("settings", {})
    mode = settings.get("pool_mode", "exact")
    modes = mode.values() if isinstance(mode, dict) else [mode]
    if any(m not in valid_modes for m in modes):
        bad(f"{path.name}: неверный pool_mode {mode!r}")
    for lvl, val in settings.get("series", {}).items():
        if lvl not in data.get("levels", {}) or not (val == "all" or (isinstance(val, int) and val > 0)):
            bad(f"{path.name}: неверная настройка series {lvl!r}: {val!r}")
 
    names = Counter()
    for c in data.get("countries", []):
        code = c.get("code", "")
        if not CODE_RE.match(code):
            bad(f"{path.name}: странный код {code!r}")
        if not str(c.get("name", "")).strip():
            bad(f"{path.name}: пустое название у {code!r}")
        if c.get("continent") != path.stem:
            bad(f"{path.name}: у {code!r} continent={c.get('continent')!r}")
        if str(c.get("level")) not in game.LEVELS:
            bad(f"{path.name}: у {code!r} неизвестный уровень {c.get('level')!r}")
        names[c.get("name")] += 1
    for name, n in names.items():
        if n > 1:
            warn(f"{path.name}: название «{name}» встречается {n} раза")
    levels = Counter(c["level"] for c in data.get("countries", []))
    good(f"{path.name}: {len(data.get('countries', []))} флагов, по уровням {dict(sorted(levels.items()))}")
 
# ---------- 3. Размеры пулов и серий ----------
print("\n--- Пулы и серии (уровень: пул / вопросов / вариантов) ---")
for cont in game.CONTINENTS:
    total = sum(1 for c in game.COUNTRIES if c["continent"] == cont)
    row = []
    for lv in (1, 2, 3):
        pool = len(game.get_pool(cont, lv))
        n = game.series_length(cont, lv)
        opts = min(game.OPTIONS_BY_LEVEL[lv], total)
        row.append(f"{lv}: {pool}/{n}/{opts}")
        if pool == 0:
            bad(f"{cont}, уровень {lv}: пустой пул")
        elif n < 5:
            warn(f"{cont}, уровень {lv}: серия всего {n} вопросов")
        if total < game.OPTIONS_BY_LEVEL[lv]:
            warn(f"{cont}: флагов меньше, чем вариантов ответа на уровне {lv}")
    print(f"  {cont:14} " + "   ".join(row))
 
# ---------- 4. Файлы флагов ----------
print("\n--- Флаги ---")
expected: set[Path] = set()
checked = 0
for c in game.COUNTRIES:
    p = FLAGS_DIR / c["continent"] / f'{c["code"]}.png'
    expected.add(p)
    if not p.exists():
        bad(f"нет файла флага: {p.relative_to(FLAGS_DIR)}")
        continue
    try:
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            fmt, (w, h) = im.format, im.size
    except Exception as e:  # noqa: BLE001
        bad(f"повреждена картинка {p.relative_to(FLAGS_DIR)}: {e!r}")
        continue
    checked += 1
    if fmt != "PNG":
        bad(f"{p.relative_to(FLAGS_DIR)}: формат {fmt}, а не PNG")
    if w < 200:
        warn(f"{p.relative_to(FLAGS_DIR)}: маленькая картинка {w}×{h}")
    ratio = w / h
    if not 0.6 <= ratio <= 3.0:
        warn(f"{p.relative_to(FLAGS_DIR)}: странные пропорции {w}×{h}")
    kb = p.stat().st_size // 1024
    if kb > 500:
        warn(f"{p.relative_to(FLAGS_DIR)}: тяжёлый файл {kb} КБ")
good(f"флагов проверено и открыто: {checked} из {len(expected)}")
 
orphans = [
    f for f in FLAGS_DIR.rglob("*")
    if f.is_file() and f not in expected and f.name != ".gitkeep"
]
for f in sorted(orphans):
    warn(f"лишний файл (не нужен ни одной стране): {f.relative_to(FLAGS_DIR)}")
if not orphans:
    good("лишних файлов во flags/ нет")
 
# ---------- 5. Имитация игры ----------
print("\n--- Имитация игры ---")
errors_before = len(problems)
for cont in game.CONTINENTS:
    for lv in (1, 2, 3):
        total = sum(1 for c in game.COUNTRIES if c["continent"] == cont)
        want = min(game.OPTIONS_BY_LEVEL[lv], total)
        for _ in range(30):
            series = game.new_series(cont, lv)
            if len(series) != game.series_length(cont, lv) or len(series) != len(set(series)):
                bad(f"{cont}/{lv}: неправильная серия {series}")
                break
            for code in series:
                q = game.make_question(code, cont, lv)
                codes = [o["code"] for o in q.options]
                if code not in codes:
                    bad(f"{cont}/{lv}/{code}: верного ответа нет среди вариантов")
                if len(codes) != len(set(codes)):
                    bad(f"{cont}/{lv}/{code}: повтор вариантов {codes}")
                if len(codes) != want:
                    bad(f"{cont}/{lv}/{code}: вариантов {len(codes)}, нужно {want}")
                if not q.flag_path.exists():
                    bad(f"{cont}/{lv}/{code}: нет файла {q.flag_path}")
if len(problems) == errors_before:
    good(f"{len(game.CONTINENTS) * 3 * 30} серий (по 30 на каждый материк и уровень) собрались без ошибок")
 
# ---------- 6. Git и секреты ----------
print("\n--- Git и секреты ---")
gi = BASE / ".gitignore"
text = gi.read_text(encoding="utf-8") if gi.exists() else ""
lines = {l.strip() for l in text.splitlines()}
for need, alts in {
    ".env": {".env"},
    "базы данных": {"*.db"},
    "окружения": {"venv/", ".venv/", "venv"},
    "кэша": {"cache/"},
}.items():
    if lines & alts:
        good(f".gitignore защищает {need}")
    else:
        warn(f".gitignore: нет записи для {need} (нужна одна из {sorted(alts)})")
 
try:
    out = subprocess.run(
        ["git", "ls-files"], cwd=BASE, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    leaked = [f for f in out if f == ".env" or f.endswith(".db") or f.startswith(("venv/", ".venv/", "cache/"))]
    if leaked:
        bad(f"в Git попали файлы, которых там быть не должно: {leaked}")
    else:
        good("в Git нет .env, баз данных, venv и кэша")
except (subprocess.CalledProcessError, FileNotFoundError):
    warn("не удалось проверить Git (не репозиторий или git не установлен)")
 
# ---------- Итог ----------
print("\n" + "=" * 50)
print(f"Ошибок: {len(problems)}   Предупреждений: {len(warnings)}")
if problems:
    print("Есть ошибки, их нужно исправить до запуска.")
    sys.exit(1)
print("Критических проблем нет ✅" + ("" if not warnings else " (проверь предупреждения выше)"))
 