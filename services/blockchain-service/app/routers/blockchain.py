from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.services.blockchain_service import blockchain
from app.core.config import settings
from common.logging.logger import get_logger

router = APIRouter()
log = get_logger("blockchain-service")


def require_roles(*roles: str):
    """Trust x-user-role only after the API gateway has replaced client-supplied values."""

    async def checker(x_user_role: str = Header(default="")):
        if x_user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return x_user_role

    return checker


class PrepareProductRequest(BaseModel):
    product_id: str
    serial_number: str
    model: str
    batch: str
    from_address: str | None = None


class DeactivatePrepareRequest(BaseModel):
    product_id: str


class TxProofRequest(BaseModel):
    tx_hash: str
    product_id: str


class AddManufacturerRequest(BaseModel):
    wallet_address: str
    manufacturer_id: str
    name: str


class ManufacturerProofRequest(BaseModel):
    tx_hash: str
    wallet_address: str


class VerifyProductRequest(BaseModel):
    product_id: str
    serial_number: str
    model: str
    batch: str


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=400, detail=str(exc))
    log.error("blockchain call failed", extra={"event": "blockchain_error", "error": str(exc)})
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/network")
async def network_info():
    """Current network status — chain ID, block number, connection."""
    return await blockchain.call(blockchain.network_info)


@router.post("/products/prepare")
async def prepare_registration(
    body: PrepareProductRequest,
    _role: str = Depends(require_roles("admin", "manufacturer")),
):
    """
    Return unsigned registerProduct calldata.
    The manufacturer signs and broadcasts it in MetaMask. This service never sees the key.
    """
    try:
        return await blockchain.call(
            blockchain.prepare_registration,
            body.product_id,
            body.serial_number,
            body.model,
            body.batch,
            body.from_address,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/products/registration-proof")
async def registration_proof(body: TxProofRequest):
    """Read a mined registerProduct receipt. Does not change the database."""
    try:
        return await blockchain.call(blockchain.registration_proof, body.tx_hash, body.product_id)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/products/deactivate-calldata")
async def prepare_deactivation(
    body: DeactivatePrepareRequest,
    _role: str = Depends(require_roles("admin", "manufacturer")),
):
    try:
        return await blockchain.call(blockchain.prepare_deactivation, body.product_id)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/products/deactivation-proof")
async def deactivation_proof(body: TxProofRequest):
    try:
        return await blockchain.call(blockchain.deactivation_proof, body.tx_hash, body.product_id)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/products/verify")
async def verify_product(body: VerifyProductRequest):
    """
    Check whether the submitted details match an active registration.
    A match is not proof that the physical item is unique.
    """
    try:
        return await blockchain.call(
            blockchain.verify_product,
            body.product_id,
            body.serial_number,
            body.model,
            body.batch,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    try:
        return await blockchain.call(blockchain.get_product, product_id)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/manufacturers/prepare")
async def prepare_add_manufacturer(
    body: AddManufacturerRequest,
    _role: str = Depends(require_roles("admin")),
):
    """Unsigned addManufacturer calldata. The contract owner signs it in MetaMask."""
    try:
        return await blockchain.call(
            blockchain.prepare_add_manufacturer,
            body.wallet_address,
            body.manufacturer_id,
            body.name,
        )
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/manufacturers/confirm")
async def confirm_add_manufacturer(
    body: ManufacturerProofRequest,
    _role: str = Depends(require_roles("admin")),
):
    try:
        proof = await blockchain.call(
            blockchain.manufacturer_added_proof,
            body.tx_hash,
            body.wallet_address,
        )
        return {"tx_hash": proof["tx_hash"], "status": "added", "wallet": proof["wallet"]}
    except Exception as exc:
        raise _map_error(exc) from exc


@router.post("/manufacturers")
async def add_manufacturer(
    body: AddManufacturerRequest,
    _role: str = Depends(require_roles("admin")),
):
    """
    Custodial whitelist using OWNER_PRIVATE_KEY from the environment.
    Local Anvil only, unless you replace that key. The UI uses /manufacturers/prepare.
    """
    key = (settings.OWNER_PRIVATE_KEY or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="OWNER_PRIVATE_KEY is not set")
    try:
        fn = await blockchain.call(
            blockchain.build_add_manufacturer,
            body.wallet_address,
            body.manufacturer_id,
            body.name,
        )
        if fn is None:
            return {"tx_hash": None, "status": "already_whitelisted"}
        tx_hash = await blockchain.submit(fn, key)
        return {"tx_hash": tx_hash, "status": "added"}
    except Exception as exc:
        raise _map_error(exc) from exc


@router.delete("/manufacturers/{wallet_address}")
async def remove_manufacturer(
    wallet_address: str,
    _role: str = Depends(require_roles("admin")),
):
    key = (settings.OWNER_PRIVATE_KEY or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="OWNER_PRIVATE_KEY is not set")
    try:
        fn = await blockchain.call(blockchain.build_remove_manufacturer, wallet_address)
        tx_hash = await blockchain.submit(fn, key)
        return {"tx_hash": tx_hash, "status": "removed"}
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get("/manufacturers")
async def list_manufacturers():
    try:
        return await blockchain.call(blockchain.get_all_manufacturers)
    except Exception as exc:
        raise _map_error(exc) from exc


@router.get("/manufacturers/{wallet_address}/is-authorized")
async def is_authorized_manufacturer(wallet_address: str):
    try:
        authorized = await blockchain.call(blockchain.is_manufacturer, wallet_address)
        return {"wallet": wallet_address, "is_manufacturer": authorized}
    except Exception as exc:
        raise _map_error(exc) from exc
