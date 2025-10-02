import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = bool(int(os.getenv("CHAT_DEBUG", "1")))
    database_url: str = os.getenv("CHAT_DB_URL", "sqlite+aiosqlite:///./chat_history.db")
    allow_origins: list[str] = [o for o in os.getenv("CHAT_CORS_ORIGINS", "*").split(",") if o]


settings = Settings()


