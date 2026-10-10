# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Network ──────────────────────────────────────────────────────────────
    # Sepolia testnet via Infura/Alchemy — set your key in .env
    # For local dev, point to Anvil: http://anvil:8545
    ETH_RPC_URL: str  = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"

    # Contract deployed address on the chosen network
    CONTRACT_ADDRESS: str = "0x0000000000000000000000000000000000000000"

    # Contract owner wallet address (configured reference/fallback)
    CONTRACT_OWNER: str | None = None

    # ── Signing ───────────────────────────────────────────────────────────────
    # Private key of the deployer / admin wallet (for write transactions)
    # In production, use a secrets manager — never commit this!
    OWNER_PRIVATE_KEY: str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    # ── Service ───────────────────────────────────────────────────────────────
    SERVICE_NAME: str     = "blockchain-service"
    LOG_LEVEL: str        = "INFO"
    LOKI_URL: str | None  = None

    # Internal URL of product-service (to notify when tx is confirmed)
    PRODUCT_SERVICE_URL: str = "http://product-service:8002"

    # Chain ID: 11155111 = Sepolia, 1 = Ethereum mainnet, 31337 = Anvil local
    CHAIN_ID: int = 11155111


settings = Settings()
