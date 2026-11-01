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


settings = Settings()

DB_PATH = BASE_DIR / settings.database_path
EUROPE_JSON = BASE_DIR / "data" / "europe.json"
FLAGS_DIR = BASE_DIR / "flags"

# Очки (глобусы 🌐)
SCORE_CORRECT = 3
SCORE_WRONG = -1