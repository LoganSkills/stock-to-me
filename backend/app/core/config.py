# Core application settings
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Stock To Me"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stocktome"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # SEC EDGAR
    EDGAR_BASE_URL: str = "https://www.sec.gov/cgi-bin/browse-edgar"
    EDGAR_ARCHIVE_URL: str = "https://www.sec.gov/Archives/edgar"

    # Market Data (placeholder — add your API key)
    MARKET_DATA_API_KEY: str = ""
    MARKET_DATA_BASE_URL: str = ""

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Universe defaults
    MIN_MARKET_CAP: int = 10_000_000
    MAX_MARKET_CAP: int = 750_000_000

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
