"""
ProductService — business logic layer.
Separates DB operations from router concerns.
"""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.core.config import settings
from common.crypto.hashing import keccak256_product, bytes32_to_hex
from common.logging.logger import get_logger

log = get_logger("product-service")


async def create_product(db: AsyncSession, data: ProductCreate, creator_user_id: str) -> Product:
    # Compute the hash that will be stored on-chain
    product_hash_bytes = keccak256_product(
        data.product_id, data.serial_number, data.model, data.batch
    )
    product_hash_hex = bytes32_to_hex(product_hash_bytes)

    product = Product(
        product_id=data.product_id,
        name=data.name,
        serial_number=data.serial_number,
        model=data.model,
        batch=data.batch,
        description=data.description,
        product_hash=product_hash_hex,
        manufacturer_wallet=data.manufacturer_wallet,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    log.info(
        "product created in database",
        extra={
            "event": "product_created",
            "product_id": data.product_id,
            "product_hash": product_hash_hex,
            "creator": creator_user_id,
        },
    )
    return product


async def get_product_by_product_id(db: AsyncSession, product_id: str) -> Product | None:
    return await db.scalar(select(Product).where(Product.product_id == product_id))


async def list_products(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Product]:
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_product(db: AsyncSession, product: Product, data: ProductUpdate) -> Product:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    log.info("product updated", extra={"event": "product_updated", "product_id": product.product_id})
    return product


async def mark_on_chain(db: AsyncSession, product_id: str, tx_hash: str) -> None:
    """Called after blockchain-service confirms on-chain registration."""
    product = await get_product_by_product_id(db, product_id)
    if product:
        product.is_on_chain = True
        await db.commit()
        log.info(
            "product marked on-chain",
            extra={"event": "product_on_chain", "product_id": product_id, "tx_hash": tx_hash},
        )
