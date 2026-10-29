"""
API Gateway router.

Routes incoming requests to the correct downstream service.
Validates JWT on protected routes and injects x-user-id / x-user-role headers
so downstream services don't need to re-verify tokens.

Route map:
  /api/auth/**        → auth-service:8001
  /api/products/**    → product-service:8002
  /api/blockchain/**  → blockchain-service:8003
"""

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt  # type: ignore

from app.core.config import settings
from common.logging.logger import get_logger

router = APIRouter()
log    = get_logger("api-gateway")
bearer = HTTPBearer(auto_error=False)

# Shared async client — reused across all requests
_client: httpx.AsyncClient | None = None

JWT_SECRET    = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM

# Routes that do NOT require a JWT
PUBLIC_PREFIXES = (
    "/api/auth/register",
    "/api/auth/login",
    "/api/blockchain/network",
    "/api/blockchain/products/verify",
    "/health",
)


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        # Custodial admin transactions can wait on a receipt. Product registration
        # no longer waits here: MetaMask signs, and the browser polls the receipt.
        _client = httpx.AsyncClient(timeout=150.0)
    return _client


def _decode_token_if_present(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def _upstream_url(request: Request) -> str:
    path = request.url.path  # e.g. /api/products/P10001

    if path.startswith("/api/auth"):
        base    = settings.AUTH_SERVICE_URL
        subpath = path.removeprefix("/api/auth")
        return f"{base}/auth{subpath}"

    if path.startswith("/api/products"):
        base    = settings.PRODUCT_SERVICE_URL
        subpath = path.removeprefix("/api/products")
        return f"{base}/products{subpath}"

    if path.startswith("/api/blockchain"):
        base    = settings.BLOCKCHAIN_SERVICE_URL
        subpath = path.removeprefix("/api/blockchain")
        return f"{base}/blockchain{subpath}"

    raise HTTPException(status_code=404, detail=f"No upstream for path: {path}")


async def _proxy(request: Request, token_payload: dict | None = None) -> Response:
    client  = get_client()
    url     = _upstream_url(request)
    qs      = str(request.url.query)
    full_url = f"{url}?{qs}" if qs else url

    # Drop client-supplied identity headers before injecting the JWT claims.
    # Otherwise a caller can set x-user-id and be recorded as someone else.
    hop_by_hop = {"host", "content-length", "transfer-encoding", "connection"}
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in hop_by_hop and not key.lower().startswith("x-user-")
    }

    if token_payload:
        headers["x-user-id"] = str(token_payload.get("sub") or "")
        headers["x-user-role"] = str(token_payload.get("role") or "customer")
        wallet = token_payload.get("wallet")
        if wallet:
            headers["x-user-wallet"] = str(wallet)

    body = await request.body()

    upstream_resp = await client.request(
        method=request.method,
        url=full_url,
        headers=headers,
        content=body,
    )

    log.info(
        "proxied request",
        extra={
            "event":   "proxy",
            "method":  request.method,
            "path":    request.url.path,
            "status":  upstream_resp.status_code,
            "upstream": full_url,
        },
    )

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=dict(upstream_resp.headers),
        media_type=upstream_resp.headers.get("content-type"),
    )


# ── Catch-all route ────────────────────────────────────────────────────────────

@router.api_route(
    "/api/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def gateway(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    path = request.url.path
    token_payload = None

    # Check if route requires auth
    is_public = any(path.startswith(p) for p in PUBLIC_PREFIXES)
    # GET product reads & manufacturer public views are public
    if request.method == "GET" and (
        path.startswith("/api/products")
        or path.startswith("/api/blockchain/manufacturers")
        or path.startswith("/api/blockchain/products")
    ):
        is_public = True

    if credentials:
        token_payload = _decode_token_if_present(credentials.credentials)

    if not is_public and token_payload is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    return await _proxy(request, token_payload)
