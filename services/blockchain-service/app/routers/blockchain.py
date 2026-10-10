from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.blockchain_service import blockchain
from app.core.config import settings
from common.logging.logger import get_logger

router = APIRouter()
log    = get_logger("blockchain-service")


# ── Schemas ────────────────────────────────────────────────────────────────────

class RegisterProductRequest(BaseModel):
    product_id: str
    serial_number: str
    model: str
    batch: str
    manufacturer_private_key: str   # from MetaMask wallet export / env secret


class VerifyProductRequest(BaseModel):
    product_id: str
    serial_number: str
    model: str
    batch: str


class AddManufacturerRequest(BaseModel):
    wallet_address: str
    manufacturer_id: str
    name: str
    owner_private_key: str | None = None   # defaults to OWNER_PRIVATE_KEY from env


class DeactivateProductRequest(BaseModel):
    product_id: str
    signer_private_key: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/network")
async def network_info():
    """Current network status — chain ID, block number, connection."""
    return blockchain.network_info()


@router.post("/products/register")
async def register_product(body: RegisterProductRequest):
    """
    Register a product on-chain via the manufacturer's MetaMask wallet private key.
    Returns the transaction hash.
    """
    try:
        tx_hash = blockchain.register_product(
            product_id=body.product_id,
            serial_number=body.serial_number,
            model=body.model,
            batch=body.batch,
            manufacturer_private_key=body.manufacturer_private_key,
        )
        return {"tx_hash": tx_hash, "status": "confirmed"}
    except ValueError as exc:
        log.warning("register_product validation error", extra={"event": "register_validation_error", "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        log.error("register_product contract error", extra={"event": "register_contract_error", "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("register_product unexpected error", extra={"event": "register_unexpected_error", "error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/products/verify")
async def verify_product(body: VerifyProductRequest):
    """
    Verify a product against the blockchain — free view call, no gas.
    Returns is_authentic, manufacturer wallet, registration timestamp, active status.
    """
    try:
        return blockchain.verify_product(
            product_id=body.product_id,
            serial_number=body.serial_number,
            model=body.model,
            batch=body.batch,
        )
    except Exception as exc:
        log.error("verify_product failed", extra={"event": "verify_error", "error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    """Raw read of on-chain product data — no hash check."""
    try:
        return blockchain.get_product(product_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/products/deactivate")
async def deactivate_product(body: DeactivateProductRequest):
    try:
        tx_hash = blockchain.deactivate_product(body.product_id, body.signer_private_key)
        return {"tx_hash": tx_hash, "status": "deactivated"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/manufacturers")
async def add_manufacturer(body: AddManufacturerRequest):
    try:
        tx_hash = blockchain.add_manufacturer(
            wallet_address=body.wallet_address,
            manufacturer_id=body.manufacturer_id,
            name=body.name,
            owner_private_key=body.owner_private_key,
        )
        return {"tx_hash": tx_hash, "status": "added"}
    except ValueError as exc:
        log.error("add_manufacturer key error", extra={"event": "key_error", "error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        log.error("add_manufacturer tx revert", extra={"event": "tx_revert", "error": str(exc)})
        raise HTTPException(
            status_code=400,
            detail=f"On-chain transaction failed: {exc}. Ensure the signing private key matches the contract owner and the wallet is not already added."
        )
    except Exception as exc:
        log.error("add_manufacturer failed", extra={"event": "add_mfg_error", "error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/manufacturers/{wallet_address}")
async def remove_manufacturer(wallet_address: str):
    try:
        tx_hash = blockchain.remove_manufacturer(wallet_address)
        return {"tx_hash": tx_hash, "status": "removed"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/manufacturers")
async def list_manufacturers():
    try:
        return blockchain.get_all_manufacturers()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/manufacturers/{wallet_address}/is-authorized")
async def is_authorized_manufacturer(wallet_address: str):
    try:
        return {"wallet": wallet_address, "is_manufacturer": blockchain.is_manufacturer(wallet_address)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
