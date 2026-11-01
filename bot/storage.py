import aiosqlite

from config import DB_PATH, SCORE_CORRECT, SCORE_WRONG


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
        await db.commit()


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT globes FROM players WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return row[0] if row else 0


async def add_answer(user_id: int, username: str | None, is_correct: bool) -> int:
    """Начисляет очки за ответ и возвращает новый баланс (не ниже 0)."""
    delta = SCORE_CORRECT if is_correct else SCORE_WRONG
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