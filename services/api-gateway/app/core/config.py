# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    AUTH_SERVICE_URL:       str = "http://auth-service:8001"
    PRODUCT_SERVICE_URL:    str = "http://product-service:8002"
    BLOCKCHAIN_SERVICE_URL: str = "http://blockchain-service:8003"

    JWT_SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM:  str = "HS256"

    SERVICE_NAME: str    = "api-gateway"
    LOG_LEVEL:    str    = "INFO"
    LOKI_URL: str | None = None


settings = Settings()
