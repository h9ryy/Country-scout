import aiosqlite

from config import DB_PATH, PERFECT_RUNS_TO_MASTER, SCORES_BY_LEVEL


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                user_id  INTEGER PRIMARY KEY,
                username TEXT,
                globes   INTEGER NOT NULL DEFAULT 0,
                correct  INTEGER NOT NULL DEFAULT 0,
                wrong    INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS level_progress (
                user_id      INTEGER NOT NULL,
                continent    TEXT    NOT NULL,
                level        INTEGER NOT NULL,
                perfect_runs INTEGER NOT NULL DEFAULT 0,
                mastered     INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, continent, level)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS series_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                continent   TEXT    NOT NULL,
                level       INTEGER NOT NULL,
                correct     INTEGER NOT NULL,
                total       INTEGER NOT NULL,
                finished_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT globes FROM players WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return row[0] if row else 0


async def add_answer(
    user_id: int,
    username: str | None,
    is_correct: bool,
    level: int,
    scored: bool = True,
) -> int:
    """Записывает ответ и возвращает новый баланс (не ниже 0).

    Очки зависят от уровня (см. SCORES_BY_LEVEL в config.py).
    scored=False: глобусы не меняются ни в плюс, ни в минус
    (освоенный уровень), но счётчики верных/неверных растут.
    """
    delta = 0
    if scored:
        reward, penalty = SCORES_BY_LEVEL[level]
        delta = reward if is_correct else penalty
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO players (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        await db.execute(
            """
            UPDATE players
            SET globes   = MAX(0, globes + ?),
                correct  = correct + ?,
                wrong    = wrong + ?,
                username = ?
            WHERE user_id = ?
            """,
            (delta, int(is_correct), int(not is_correct), username, user_id),
        )
        await db.commit()
        cur = await db.execute(
            "SELECT globes FROM players WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return row[0]


async def get_stats(user_id: int) -> tuple[int, int, int]:
    """Возвращает (глобусы, верных, ошибок) игрока."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT globes, correct, wrong FROM players WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
    return tuple(row) if row else (0, 0, 0)


async def get_progress(user_id: int, continent: str, level: int) -> tuple[int, bool]:
    """Возвращает (безошибочных серий, освоен ли уровень)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT perfect_runs, mastered FROM level_progress
            WHERE user_id = ? AND continent = ? AND level = ?
            """,
            (user_id, continent, level),
        )
        row = await cur.fetchone()
    return (row[0], bool(row[1])) if row else (0, False)


async def record_perfect_run(
    user_id: int, continent: str, level: int
) -> tuple[int, bool]:
    """Засчитывает безошибочную серию. Возвращает (серий, освоен ли уровень).

    На уже освоенном уровне счётчик не растёт.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO level_progress (user_id, continent, level)
            VALUES (?, ?, ?)
            """,
            (user_id, continent, level),
        )
        await db.execute(
            """
            UPDATE level_progress
            SET perfect_runs = perfect_runs + 1,
                mastered = CASE WHEN perfect_runs + 1 >= ? THEN 1 ELSE 0 END
            WHERE user_id = ? AND continent = ? AND level = ? AND mastered = 0
            """,
            (PERFECT_RUNS_TO_MASTER, user_id, continent, level),
        )
        await db.commit()
        cur = await db.execute(
            """
            SELECT perfect_runs, mastered FROM level_progress
            WHERE user_id = ? AND continent = ? AND level = ?
            """,
            (user_id, continent, level),
        )
        row = await cur.fetchone()
    return row[0], bool(row[1])


async def get_mastered(user_id: int) -> list[tuple[str, int]]:
    """Список освоенных уровней игрока: [(материк, уровень), ...]."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT continent, level FROM level_progress
            WHERE user_id = ? AND mastered = 1
            ORDER BY continent, level
            """,
            (user_id,),
        )
        rows = await cur.fetchall()
    return [(r[0], r[1]) for r in rows]

async def record_series(
    user_id: int, continent: str, level: int, correct: int, total: int
) -> None:
    """Записывает завершённую серию в историю."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO series_history (user_id, continent, level, correct, total)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, continent, level, correct, total),
        )
        await db.commit()


async def get_series_stats(user_id: int) -> tuple[int, float]:
    """Возвращает (число тестов, средний процент верных ответов за тест)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT COUNT(*), AVG(correct * 100.0 / total)
            FROM series_history
            WHERE user_id = ? AND total > 0
            """,
            (user_id,),
        )
        row = await cur.fetchone()
    return row[0], row[1] or 0.0

async def revert_points(user_id: int, delta: int) -> int:
    """Отменяет очки серии: вычитает сумму реальных изменений баланса."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET globes = MAX(0, globes - ?) WHERE user_id = ?",
            (delta, user_id),
        )
        await db.commit()
        cur = await db.execute(
            "SELECT globes FROM players WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return row[0] if row else 0