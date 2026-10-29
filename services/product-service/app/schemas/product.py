from datetime import datetime
from pydantic import BaseModel


class ProductCreate(BaseModel):
    product_id: str
    name: str
    serial_number: str
    model: str
    batch: str
    description: str | None = None
    manufacturer_wallet: str


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    product_id: str
    name: str
    serial_number: str
    model: str
    batch: str
    description: str | None
    product_hash: str | None
    manufacturer_wallet: str | None
    created_by: str | None
    chain_tx_hash: str | None = None
    is_on_chain: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TxHashBody(BaseModel):
    tx_hash: str


class VerifyRequest(BaseModel):
    product_id: str
    serial_number: str
    model: str
    batch: str
