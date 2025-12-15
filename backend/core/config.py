from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lingua:lingua_dev@localhost:5432/lingua"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Backend
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    APP_DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False  # True for production (structured JSON), False for dev (colored)
    LOG_SQL: bool = False   # Enable SQLAlchemy query logging
    
    @property
    def is_production(self) -> bool:
        return not self.APP_DEBUG
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

