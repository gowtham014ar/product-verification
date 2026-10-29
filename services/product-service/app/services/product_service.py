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


class CatalogError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def _normalize_wallet(value: str) -> str:
    wallet = (value or "").strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        raise CatalogError("manufacturer_wallet must be a 42-character Ethereum address", 400)
    return wallet


def assert_can_mutate(product: Product, user_id: str, role: str) -> None:
    """Manufacturers may change only rows they created. Admins may change any row."""
    if role == "admin":
        return
    if role != "manufacturer" or not user_id or product.created_by != user_id:
        raise CatalogError("You can only change products you created", 403)


async def create_product(
    db: AsyncSession,
    data: ProductCreate,
    creator_user_id: str,
    role: str,
    caller_wallet: str | None,
) -> Product:
    if not creator_user_id:
        raise CatalogError("Missing trusted user identity", 401)

    wallet = _normalize_wallet(data.manufacturer_wallet)
    if role == "manufacturer" and caller_wallet and wallet.lower() != caller_wallet.strip().lower():
        raise CatalogError(
            "manufacturer_wallet must be the wallet address on your account",
            403,
        )

    product_hash_hex = bytes32_to_hex(keccak256_product(
        data.product_id, data.serial_number, data.model, data.batch
    ))

    product = Product(
        product_id=data.product_id,
        name=data.name,
        serial_number=data.serial_number,
        model=data.model,
        batch=data.batch,
        description=data.description,
        product_hash=product_hash_hex,
        manufacturer_wallet=wallet,
        created_by=creator_user_id,
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


async def update_product(
    db: AsyncSession,
    product: Product,
    data: ProductUpdate,
    user_id: str,
    role: str,
) -> Product:
    assert_can_mutate(product, user_id, role)
    changes = data.model_dump(exclude_none=True)
    if "is_active" in changes and product.is_on_chain:
        raise CatalogError(
            "This product is on-chain. Recall it with MetaMask, then confirm that transaction. "
            "Changing is_active here would leave the database and the chain disagreeing.",
            409,
        )
    for field, value in changes.items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    log.info("product updated", extra={"event": "product_updated", "product_id": product.product_id})
    return product


async def _proof(path: str, payload: dict) -> dict:
    url = f"{settings.BLOCKCHAIN_SERVICE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        raise CatalogError(f"Blockchain service is unreachable: {exc}", 502) from exc

    try:
        body = resp.json()
    except Exception:
        body = {}
    detail = body.get("detail", resp.text) if isinstance(body, dict) else resp.text
    if not isinstance(detail, str):
        detail = str(detail)

    if resp.status_code == 409:
        raise CatalogError(detail or "Transaction not yet mined", 409)
    if resp.status_code >= 400:
        raise CatalogError(detail or "Blockchain proof was rejected", 400)
    return body


async def mark_on_chain(
    db: AsyncSession,
    product_id: str,
    tx_hash: str,
    user_id: str,
    role: str,
) -> Product:
    """
    Set is_on_chain only after the receipt shows registerProduct for this id
    and the hash matches the catalog row.
    """
    product = await get_product_by_product_id(db, product_id)
    if not product:
        raise CatalogError("Product not found", 404)
    assert_can_mutate(product, user_id, role)

    if product.is_on_chain and product.chain_tx_hash and product.chain_tx_hash.lower() == tx_hash.lower():
        return product
    if product.is_on_chain:
        raise CatalogError("Product is already linked to a different transaction", 409)

    proof = await _proof(
        "/blockchain/products/registration-proof",
        {"tx_hash": tx_hash, "product_id": product_id},
    )
    signer = str(proof.get("signer", ""))
    manufacturer = str(proof.get("manufacturer", ""))
    if product.manufacturer_wallet and signer.lower() != product.manufacturer_wallet.lower():
        raise CatalogError(
            "The wallet that sent this transaction is not the wallet stored on the product",
            400,
        )
    if manufacturer and signer and manufacturer.lower() != signer.lower():
        raise CatalogError("Transaction signer does not match the manufacturer in the event", 400)
    on_chain_hash = str(proof.get("product_hash", ""))
    if product.product_hash and on_chain_hash.lower() != product.product_hash.lower():
        raise CatalogError(
            "On-chain hash does not match the catalog record. The registered fields differ.",
            400,
        )

    product.is_on_chain = True
    product.chain_tx_hash = proof.get("tx_hash", tx_hash)
    product.manufacturer_wallet = manufacturer or product.manufacturer_wallet
    await db.commit()
    await db.refresh(product)
    log.info(
        "product marked on-chain",
        extra={"event": "product_on_chain", "product_id": product_id, "tx_hash": product.chain_tx_hash},
    )
    return product


async def confirm_deactivation(
    db: AsyncSession,
    product_id: str,
    tx_hash: str,
    user_id: str,
    role: str,
) -> Product:
    """Set is_active false only after ProductDeactivated is in a successful receipt."""
    product = await get_product_by_product_id(db, product_id)
    if not product:
        raise CatalogError("Product not found", 404)
    assert_can_mutate(product, user_id, role)
    if not product.is_on_chain:
        raise CatalogError(
            "This product is not on-chain. Update is_active with PATCH instead of a chain transaction.",
            409,
        )

    proof = await _proof(
        "/blockchain/products/deactivation-proof",
        {"tx_hash": tx_hash, "product_id": product_id},
    )
    product.is_active = False
    product.chain_tx_hash = proof.get("tx_hash", tx_hash)
    await db.commit()
    await db.refresh(product)
    log.info(
        "product deactivated on-chain and in the catalog",
        extra={"event": "product_deactivated", "product_id": product_id, "tx_hash": product.chain_tx_hash},
    )
    return product
