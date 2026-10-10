"""
api-gateway — single entry point for all client requests.
Validates JWT and reverse-proxies to downstream services.
"""

import sys
sys.path.insert(0, "/app/common")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.gateway import router, get_client
from common.logging.logger import get_logger

log = get_logger("api-gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("api-gateway starting", extra={"event": "startup"})
    get_client()   # pre-warm the httpx client
    yield
    log.info("api-gateway shutting down", extra={"event": "shutdown"})


app = FastAPI(
    title="Product Verification API Gateway",
    description="Single entry point — routes to auth, product, and blockchain services",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}
