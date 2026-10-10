import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str]             = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str]   = mapped_column(String(255), nullable=False)
    full_name: Mapped[str]         = mapped_column(String(255), nullable=False)
    # role: "admin" | "manufacturer" | "customer"
    role: Mapped[str]              = mapped_column(String(50), nullable=False, default="customer")
    # wallet address linked to MetaMask / Sepolia
    wallet_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    is_active: Mapped[bool]        = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]   = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
