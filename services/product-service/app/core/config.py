from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str     = "postgresql+asyncpg://postgres:postgres@postgres:5432/product_verification"
    JWT_SECRET_KEY: str   = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str    = "HS256"
    SERVICE_NAME: str     = "product-service"
    LOG_LEVEL: str        = "INFO"
    LOKI_URL: str | None  = None
    # Internal URL of blockchain-service for triggering on-chain registration
    BLOCKCHAIN_SERVICE_URL: str = "http://blockchain-service:8003"


settings = Settings()
