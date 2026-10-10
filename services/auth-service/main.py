"""
auth-service — FastAPI application entry point.
Handles user registration, login, and JWT issuance.
"""

import sys
import os

# Make the shared common package importable
sys.path.insert(0, "/app/common")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.routers import auth
from common.logging.logger import get_logger

log = get_logger("auth-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("auth-service starting", extra={"event": "startup"})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database tables ready", extra={"event": "db_ready"})
    yield
    log.info("auth-service shutting down", extra={"event": "shutdown"})


app = FastAPI(
    title="Auth Service",
    description="JWT-based authentication for Product Verification System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}
