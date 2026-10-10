"""
BlockchainService — wraps web3.py calls to ProductRegistry.sol.

Supports:
  - Sepolia testnet (MetaMask-compatible, default)
  - Ethereum mainnet (same interface, different chain ID + RPC URL)
  - Anvil local (http://anvil:8545, chain ID 31337) for development

Write transactions (registerProduct, addManufacturer, deactivateProduct):
  - Signed with OWNER_PRIVATE_KEY / manufacturer private key
  - Submitted on-chain; tx hash returned

Read calls (verifyProduct, getProduct, isManufacturer):
  - Free view calls, no signing needed
"""

import json
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware  # type: ignore

from app.core.config import settings
from common.crypto.hashing import keccak256_product, keccak256_id, bytes32_to_hex
from common.logging.logger import get_logger

log = get_logger("blockchain-service")

# ABI path relative to this file's service root
_ABI_PATH = Path(__file__).resolve().parents[2] / "contracts_abi" / "ProductRegistry.json"


class BlockchainService:
    """
    Singleton-style service initialised once at startup.
    All router functions call methods on this object.
    """

    def __init__(self):
        self._w3: Web3 | None     = None
        self._contract: Any | None = None

    def connect(self) -> None:
        """Establish web3 connection and load contract. Called in app lifespan."""
        self._w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))

        # POA middleware required for Sepolia / Polygon / testnets
        self._w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self._w3.is_connected():
            log.warning(
                "web3 not connected — blockchain calls will fail",
                extra={"event": "web3_connect_fail", "rpc": settings.ETH_RPC_URL},
            )
            return

        abi = json.loads(_ABI_PATH.read_text())
        self._contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            abi=abi,
        )
        log.info(
            "web3 connected",
            extra={
                "event":    "web3_connected",
                "rpc":      settings.ETH_RPC_URL,
                "chain_id": settings.CHAIN_ID,
                "contract": settings.CONTRACT_ADDRESS,
            },
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _require_contract(self) -> None:
        if self._contract is None:
            raise RuntimeError("Contract not loaded — check RPC URL and CONTRACT_ADDRESS")

    def _send_tx(self, fn, signer_key: str) -> str:
        """Build, sign, send a write transaction. Returns tx hash hex string."""
        account = self._w3.eth.account.from_key(signer_key)

        # 1. Dry-run simulation before broadcasting to capture exact revert reason and save gas
        try:
            fn.call({"from": account.address})
        except Exception as sim_err:
            err_msg = str(sim_err)
            log.error(
                "contract transaction simulation reverted",
                extra={
                    "event":         "tx_simulation_failed",
                    "caller":        account.address,
                    "contract":      settings.CONTRACT_ADDRESS,
                    "function":      getattr(fn, "fn_name", str(fn)),
                    "revert_reason": err_msg,
                },
            )
            # Clean up revert reason string if it contains RPC wrapper noise
            if "execution reverted:" in err_msg:
                err_msg = err_msg.split("execution reverted:")[-1].strip().strip("'\"")
            raise RuntimeError(f"Contract execution reverted: {err_msg}")

        nonce = self._w3.eth.get_transaction_count(account.address)

        # Estimate gas dynamically with a generous buffer (addManufacturer requires ~250k+ gas)
        try:
            estimated_gas = fn.estimate_gas({"from": account.address})
            gas_limit = max(int(estimated_gas * 1.5), 500_000)
        except Exception as est_err:
            log.warning("gas estimation failed, using safe 500k fallback", extra={"error": str(est_err)})
            gas_limit = 500_000

        tx = fn.build_transaction({
            "from":     account.address,
            "nonce":    nonce,
            "chainId":  settings.CHAIN_ID,
            "gas":      gas_limit,
            "gasPrice": self._w3.eth.gas_price,
        })
        signed  = self._w3.eth.account.sign_transaction(tx, signer_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        tx_hex = tx_hash.hex()
        if receipt["status"] == 0:
            # Revert occurred after mining
            gas_used = receipt.get("gasUsed", 0)
            if gas_used >= gas_limit - 5000:
                revert_reason = f"Out of Gas: transaction consumed all {gas_used} gas units. Gas limit was {gas_limit}."
            else:
                revert_reason = "Transaction reverted on-chain"
                try:
                    fn.call({"from": account.address})
                except Exception as e:
                    revert_reason = str(e)

            log.error(
                "transaction reverted on-chain",
                extra={
                    "event":         "tx_reverted",
                    "tx_hash":       tx_hex,
                    "block":         receipt["blockNumber"],
                    "gas_used":      gas_used,
                    "gas_limit":     gas_limit,
                    "caller":        account.address,
                    "contract":      settings.CONTRACT_ADDRESS,
                    "revert_reason": revert_reason,
                },
            )
            raise RuntimeError(f"Transaction reverted: {tx_hex} (Reason: {revert_reason})")

        log.info(
            "transaction confirmed",
            extra={
                "event":       "tx_confirmed",
                "tx_hash":     tx_hex,
                "block":       receipt["blockNumber"],
                "gas_used":    receipt["gasUsed"],
                "status":      receipt["status"],
                "caller":      account.address,
            },
        )
        return tx_hex

    # ── Write functions ────────────────────────────────────────────────────────

    def register_product(
        self,
        product_id: str,
        serial_number: str,
        model: str,
        batch: str,
        manufacturer_private_key: str,
    ) -> str:
        """
        Register a product on-chain.
        product_id is converted to bytes32; hash is recomputed here to match Python service.
        Returns tx hash.
        """
        self._require_contract()

        account = self._w3.eth.account.from_key(manufacturer_private_key)
        signer_address = account.address

        # Pre-check 1: Is this wallet an authorized active manufacturer on-chain?
        if not self.is_manufacturer(signer_address):
            log.warning(
                "unauthorized manufacturer registration attempt",
                extra={
                    "event":          "unauthorized_manufacturer",
                    "signer_address": signer_address,
                    "product_id":     product_id,
                    "contract":       settings.CONTRACT_ADDRESS,
                    "cause":          "Wallet address is not whitelisted in ProductRegistry smart contract",
                },
            )
            raise ValueError(
                f"Signing wallet '{signer_address}' is NOT an authorized manufacturer on-chain. "
                f"Please add this wallet on the Manufacturers tab (as Admin) before registering products."
            )

        product_id_bytes32 = keccak256_id(product_id)

        # Pre-check 2: Is this product ID already registered?
        existing = self.get_product(product_id)
        if existing["registered_at"] != 0:
            log.warning(
                "product already registered",
                extra={
                    "event":         "duplicate_product_registration",
                    "product_id":    product_id,
                    "registered_by": existing["manufacturer"],
                    "registered_at": existing["registered_at"],
                },
            )
            raise ValueError(
                f"Product '{product_id}' is already registered on-chain by wallet {existing['manufacturer']} "
                f"at timestamp {existing['registered_at']}."
            )

        product_hash_bytes = keccak256_product(product_id, serial_number, model, batch)
        fn = self._contract.functions.registerProduct(product_id_bytes32, product_hash_bytes)
        tx_hash = self._send_tx(fn, manufacturer_private_key)

        log.info(
            "product registered on-chain",
            extra={
                "event":        "product_registered_onchain",
                "product_id":   product_id,
                "hash":         bytes32_to_hex(product_hash_bytes),
                "tx_hash":      tx_hash,
                "manufacturer": signer_address,
            },
        )
        return tx_hash

    def add_manufacturer(
        self,
        wallet_address: str,
        manufacturer_id: str,
        name: str,
        owner_private_key: str | None = None,
    ) -> str:
        """Grant manufacturer role on-chain. Signed by owner."""
        self._require_contract()
        wallet_checksum = Web3.to_checksum_address(wallet_address)

        # Pre-check: if already active on-chain, skip duplicate transaction
        if self.is_manufacturer(wallet_checksum):
            log.info("manufacturer already active on-chain", extra={"wallet": wallet_address})
            return "already_whitelisted"

        key = owner_private_key or settings.OWNER_PRIVATE_KEY
        if not key or not key.strip():
            raise ValueError(
                "No owner private key provided. Please set OWNER_PRIVATE_KEY in .env or pass owner_private_key in the request body."
            )

        # Pre-check: Verify signing wallet is actually the contract owner
        account = self._w3.eth.account.from_key(key)
        try:
            contract_owner = None
            try:
                contract_owner = self._contract.functions.owner().call()
            except Exception:
                contract_owner = settings.CONTRACT_OWNER

            if contract_owner and account.address.lower() != contract_owner.lower():
                raise ValueError(
                    f"Signing wallet '{account.address}' is NOT the contract owner! "
                    f"The contract owner is '{contract_owner}'. "
                    f"Please provide the private key for '{contract_owner}', or deploy a new contract and set CONTRACT_ADDRESS in .env."
                )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            log.warning("Could not query contract owner on-chain", extra={"error": str(e)})

        mfg_id_bytes32 = keccak256_id(manufacturer_id)

        fn = self._contract.functions.addManufacturer(
            wallet_checksum,
            mfg_id_bytes32,
            name,
        )
        tx_hash = self._send_tx(fn, key)
        log.info(
            "manufacturer added on-chain",
            extra={"event": "manufacturer_added", "wallet": wallet_address, "mfg_name": name, "tx_hash": tx_hash},
        )
        return tx_hash

    def remove_manufacturer(self, wallet_address: str, owner_private_key: str | None = None) -> str:
        self._require_contract()
        key = owner_private_key or settings.OWNER_PRIVATE_KEY
        fn  = self._contract.functions.removeManufacturer(Web3.to_checksum_address(wallet_address))
        return self._send_tx(fn, key)

    def deactivate_product(self, product_id: str, signer_private_key: str) -> str:
        self._require_contract()
        product_id_bytes32 = keccak256_id(product_id)
        fn = self._contract.functions.deactivateProduct(product_id_bytes32)
        return self._send_tx(fn, signer_private_key)

    # ── Read (view) functions ──────────────────────────────────────────────────

    def verify_product(
        self,
        product_id: str,
        serial_number: str,
        model: str,
        batch: str,
    ) -> dict:
        """
        Free view call — no gas, no signing.
        Recomputes keccak256 hash from the given fields and asks the contract.
        """
        self._require_contract()

        product_id_bytes32 = keccak256_id(product_id)
        product_hash_bytes = keccak256_product(product_id, serial_number, model, batch)

        is_authentic, manufacturer, registered_at, active = (
            self._contract.functions.verifyProduct(product_id_bytes32, product_hash_bytes).call()
        )

        result = {
            "is_authentic":  is_authentic,
            "manufacturer":  manufacturer,
            "registered_at": registered_at,
            "active":        active,
            "product_hash":  bytes32_to_hex(product_hash_bytes),
        }
        log.info(
            "product verified",
            extra={"event": "product_verified", "product_id": product_id, "is_authentic": is_authentic},
        )
        return result

    def get_product(self, product_id: str) -> dict:
        self._require_contract()
        product_id_bytes32 = keccak256_id(product_id)
        product_hash, manufacturer, registered_at, active = (
            self._contract.functions.getProduct(product_id_bytes32).call()
        )
        return {
            "product_hash":  bytes32_to_hex(product_hash),
            "manufacturer":  manufacturer,
            "registered_at": registered_at,
            "active":        active,
        }

    def is_manufacturer(self, wallet_address: str) -> bool:
        self._require_contract()
        return self._contract.functions.isManufacturer(
            Web3.to_checksum_address(wallet_address)
        ).call()

    def get_all_manufacturers(self) -> list[dict]:
        self._require_contract()
        raw = self._contract.functions.getAllManufacturers().call()
        return [
            {
                "id":       bytes32_to_hex(m[0]),
                "name":     m[1],
                "wallet":   m[2],
                "added_at": m[3],
                "active":   m[4],
            }
            for m in raw
        ]

    def network_info(self) -> dict:
        if self._w3 is None:
            return {"connected": False}
        try:
            owner_address = None
            if self._contract:
                try:
                    owner_address = self._contract.functions.owner().call()
                except Exception:
                    pass
            return {
                "connected":       self._w3.is_connected(),
                "chain_id":        self._w3.eth.chain_id,
                "block_number":    self._w3.eth.block_number,
                "contract":        settings.CONTRACT_ADDRESS,
                "contract_owner":  owner_address or settings.CONTRACT_OWNER,
                "rpc":             settings.ETH_RPC_URL,
            }
        except Exception as exc:
            return {"connected": False, "error": str(exc)}


# Module-level singleton — imported and used by routers
blockchain = BlockchainService()
