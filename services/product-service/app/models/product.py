import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str]         = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Human-readable product ID, e.g. "P10001" — also the on-chain bytes32 key
    product_id: Mapped[str]      = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str]            = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str]   = mapped_column(String(128), nullable=False)
    model: Mapped[str]           = mapped_column(String(128), nullable=False)
    batch: Mapped[str]           = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hex string of keccak256 hash stored on-chain (0x...)
    product_hash: Mapped[str | None]  = mapped_column(String(66), nullable=True)
    # Wallet address of the manufacturer who registered on-chain
    manufacturer_wallet: Mapped[str | None] = mapped_column(String(42), nullable=True)
    # Tracks on-chain status; updated by blockchain-service events
    is_on_chain: Mapped[bool]    = mapped_column(Boolean, default=False)
    is_active: Mapped[bool]      = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
