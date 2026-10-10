from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str         = "postgresql+asyncpg://postgres:postgres@postgres:5432/product_verification"
    JWT_SECRET_KEY: str       = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str        = "HS256"
    JWT_EXPIRE_MINUTES: int   = 60 * 24   # 24 hours
    SERVICE_NAME: str         = "auth-service"
    LOG_LEVEL: str            = "INFO"
    LOKI_URL: str | None      = None


settings = Settings()
