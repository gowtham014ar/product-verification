"""
blockchain-service — FastAPI app for on-chain product registry operations.
Connects to Sepolia testnet (MetaMask-compatible) via web3.py.
"""

import sys
sys.path.insert(0, "/app/common")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import blockchain
from app.services.blockchain_service import blockchain as bc_service
from common.logging.logger import get_logger

log = get_logger("blockchain-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("blockchain-service starting", extra={"event": "startup"})
    bc_service.connect()
    yield
    log.info("blockchain-service shutting down", extra={"event": "shutdown"})


app = FastAPI(
    title="Blockchain Service",
    description="On-chain product registry via ProductRegistry.sol on Sepolia / Ethereum",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])


@app.get("/health")
async def health():
    net = bc_service.network_info()
    return {"status": "ok", "service": "blockchain-service", "network": net}
