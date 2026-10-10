"""
product-service — manages product metadata in PostgreSQL.
The blockchain hash is stored here alongside full product details.
"""

import sys
sys.path.insert(0, "/app/common")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.routers import products
from common.logging.logger import get_logger

log = get_logger("product-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("product-service starting", extra={"event": "startup"})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database tables ready", extra={"event": "db_ready"})
    yield
    log.info("product-service shutting down", extra={"event": "shutdown"})


app = FastAPI(
    title="Product Service",
    description="CRUD for product metadata; pairs with blockchain-service for on-chain hashes",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(products.router, prefix="/products", tags=["products"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "product-service"}
