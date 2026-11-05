from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    database_path: str = "data/bot.db"
    cache_dir: str = "cache"


settings = Settings()

DB_PATH = BASE_DIR / settings.database_path
CACHE_DIR = BASE_DIR / settings.cache_dir
DATA_DIR = BASE_DIR / "data"
FLAGS_DIR = BASE_DIR / "flags"

# Очки (глобусы 🌐) по уровням: (за верный ответ, за ошибку)
SCORES_BY_LEVEL = {
    1: (3, -1),
    2: (3, -2),
    3: (3, -3),
}

# Сколько безошибочных серий нужно, чтобы уровень считался освоенным
PERFECT_RUNS_TO_MASTER = 2