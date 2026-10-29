from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, TxHashBody
from app.services import product_service
from app.services.product_service import CatalogError
from common.logging.logger import get_logger

router = APIRouter()
log = get_logger("product-service")


def require_role(*roles: str):
    """Inline role guard — reads x-user-role injected by the API gateway."""

    async def checker(x_user_role: str = Header(default="")):
        if x_user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return x_user_role

    return checker


def _http(exc: CatalogError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(require_role("admin", "manufacturer")),
    x_user_id: str = Header(default=""),
    x_user_wallet: str = Header(default=""),
):
    existing = await product_service.get_product_by_product_id(db, body.product_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Product '{body.product_id}' already exists")
    try:
        return await product_service.create_product(
            db,
            body,
            creator_user_id=x_user_id,
            role=role,
            caller_wallet=x_user_wallet or None,
        )
    except CatalogError as exc:
        raise _http(exc) from exc


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.list_products(db, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product_by_product_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(require_role("admin", "manufacturer")),
    x_user_id: str = Header(default=""),
):
    product = await product_service.get_product_by_product_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        return await product_service.update_product(db, product, body, user_id=x_user_id, role=role)
    except CatalogError as exc:
        raise _http(exc) from exc


@router.post("/{product_id}/mark-on-chain", response_model=ProductResponse)
async def mark_on_chain(
    product_id: str,
    body: TxHashBody,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(require_role("admin", "manufacturer")),
    x_user_id: str = Header(default=""),
):
    """Link the catalog row after MetaMask's registerProduct transaction is mined."""
    try:
        return await product_service.mark_on_chain(
            db, product_id, body.tx_hash, user_id=x_user_id, role=role
        )
    except CatalogError as exc:
        raise _http(exc) from exc


@router.post("/{product_id}/confirm-deactivation", response_model=ProductResponse)
async def confirm_deactivation(
    product_id: str,
    body: TxHashBody,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(require_role("admin", "manufacturer")),
    x_user_id: str = Header(default=""),
):
    """Set is_active false only after the chain receipt shows ProductDeactivated."""
    try:
        return await product_service.confirm_deactivation(
            db, product_id, body.tx_hash, user_id=x_user_id, role=role
        )
    except CatalogError as exc:
        raise _http(exc) from exc
