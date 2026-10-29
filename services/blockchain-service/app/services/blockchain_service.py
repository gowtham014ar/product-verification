"""
BlockchainService — wraps web3.py calls to ProductRegistry.sol.

Write transactions that the service itself signs (manufacturer whitelist on the
custodial Anvil/admin path) run in a worker thread so wait_for_receipt cannot
freeze the event loop. The nonce is taken with "pending", and only one broadcast
per signer runs at a time.

Product registration and recall are signed in the user's wallet. This service
prepares calldata and checks the mined receipt. It does not accept private keys
from clients for those calls.
"""

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.middleware import ExtraDataToPOAMiddleware  # type: ignore

from app.core.config import settings
from common.crypto.hashing import keccak256_product, keccak256_id, bytes32_to_hex
from common.logging.logger import get_logger

log = get_logger("blockchain-service")

_ABI_PATH = Path(__file__).resolve().parents[2] / "contracts_abi" / "ProductRegistry.json"

# Well-known Anvil account 0. Fine for a local demo. Never use it on a public network.
ANVIL_DEMO_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _hex(value: Any) -> str:
    raw = value.hex() if hasattr(value, "hex") else str(value)
    return raw if raw.startswith("0x") else "0x" + raw


def _as_bytes32(value: Any) -> bytes:
    if isinstance(value, str):
        raw = value[2:] if value.startswith("0x") else value
        return bytes.fromhex(raw)
    return bytes(value)


def _calldata(fn) -> str:
    encoder = getattr(fn, "_encode_transaction_data", None) or getattr(fn, "encode_abi", None)
    if encoder is None:
        raise RuntimeError("This web3 version cannot encode contract calldata")
    data = encoder()
    return _hex(data) if not isinstance(data, str) else (data if data.startswith("0x") else "0x" + data)


class BlockchainService:
    """
    Singleton-style service initialised once at startup.
    Sync web3 calls are executed with asyncio.to_thread by the async helpers.
    """

    def __init__(self):
        self._w3: Web3 | None = None
        self._contract: Any | None = None
        # Re-entrant: a prepare() call may invoke get_product(), which also locks.
        self._rpc_lock = threading.RLock()
        self._nonce_guard = asyncio.Lock()
        self._nonce_locks: dict[str, asyncio.Lock] = {}

    def connect(self) -> None:
        """Establish web3 connection and load contract. Called in app lifespan."""
        self._w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))
        self._w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        owner_key = (settings.OWNER_PRIVATE_KEY or "").strip().lower()
        if owner_key in {ANVIL_DEMO_KEY, "0x" + ANVIL_DEMO_KEY[2:]}:
            log.warning(
                "OWNER_PRIVATE_KEY is the public Anvil demo key. Safe only on a local Anvil node.",
                extra={"event": "insecure_owner_key"},
            )

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
                "event": "web3_connected",
                "rpc": settings.ETH_RPC_URL,
                "chain_id": settings.CHAIN_ID,
                "contract": settings.CONTRACT_ADDRESS,
            },
        )

    async def call(self, func, *args, **kwargs):
        """Run a sync web3 helper off the event loop."""
        return await asyncio.to_thread(func, *args, **kwargs)

    async def submit(self, fn, signer_key: str) -> str:
        """
        Broadcast one transaction for this signer, then wait for the receipt
        without holding the event loop or the per-signer nonce lock.
        """
        address = Account.from_key(signer_key).address.lower()
        async with self._nonce_guard:
            lock = self._nonce_locks.get(address)
            if lock is None:
                lock = asyncio.Lock()
                self._nonce_locks[address] = lock
        async with lock:
            tx_hex = await asyncio.to_thread(self._broadcast, fn, signer_key)
        return await asyncio.to_thread(self._confirm, tx_hex, fn, signer_key)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _require_contract(self) -> None:
        if self._contract is None or self._w3 is None:
            raise RuntimeError("Contract not loaded — check RPC URL and CONTRACT_ADDRESS")

    def _revert_text(self, err: Exception) -> str:
        err_msg = str(err)
        if "execution reverted:" in err_msg:
            err_msg = err_msg.split("execution reverted:")[-1].strip().strip("'\"")
        return err_msg

    def _broadcast(self, fn, signer_key: str) -> str:
        """Simulate, assign a pending nonce, and submit. Does not wait."""
        self._require_contract()
        account = Account.from_key(signer_key)
        with self._rpc_lock:
            try:
                fn.call({"from": account.address})
            except Exception as sim_err:
                err_msg = self._revert_text(sim_err)
                log.error(
                    "contract transaction simulation reverted",
                    extra={
                        "event": "tx_simulation_failed",
                        "caller": account.address,
                        "contract": settings.CONTRACT_ADDRESS,
                        "function": getattr(fn, "fn_name", str(fn)),
                        "revert_reason": err_msg,
                    },
                )
                raise RuntimeError(f"Contract execution reverted: {err_msg}") from sim_err

            # "pending" includes txs already in the mempool. Combined with the
            # per-address lock around this broadcast, two overlapping sends
            # cannot both be given the same nonce.
            nonce = self._w3.eth.get_transaction_count(account.address, "pending")

            try:
                estimated_gas = fn.estimate_gas({"from": account.address})
                gas_limit = max(int(estimated_gas * 1.5), 500_000)
            except Exception as est_err:
                log.warning(
                    "gas estimation failed, using safe 500k fallback",
                    extra={"error": str(est_err)},
                )
                gas_limit = 500_000

            tx = fn.build_transaction({
                "from": account.address,
                "nonce": nonce,
                "chainId": settings.CHAIN_ID,
                "gas": gas_limit,
                "gasPrice": self._w3.eth.gas_price,
            })
            signed = Account.sign_transaction(tx, signer_key)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return _hex(tx_hash)

    def _confirm(self, tx_hex: str, fn, signer_key: str) -> str:
        """Poll for a receipt without holding the RPC lock between polls."""
        self._require_contract()
        account = Account.from_key(signer_key)
        deadline = time.time() + 120
        receipt = None
        while time.time() < deadline:
            with self._rpc_lock:
                try:
                    receipt = self._w3.eth.get_transaction_receipt(tx_hex)
                except TransactionNotFound:
                    receipt = None
            if receipt is not None:
                break
            time.sleep(2)

        if receipt is None:
            raise RuntimeError(f"Timed out waiting for transaction {tx_hex}")

        if receipt["status"] == 0:
            gas_used = receipt.get("gasUsed", 0)
            gas_limit = receipt.get("gasUsed", 0)
            revert_reason = "Transaction reverted on-chain"
            try:
                with self._rpc_lock:
                    fn.call({"from": account.address})
            except Exception as exc:
                revert_reason = self._revert_text(exc)
            log.error(
                "transaction reverted on-chain",
                extra={
                    "event": "tx_reverted",
                    "tx_hash": tx_hex,
                    "block": receipt["blockNumber"],
                    "gas_used": gas_used,
                    "gas_limit": gas_limit,
                    "caller": account.address,
                    "contract": settings.CONTRACT_ADDRESS,
                    "revert_reason": revert_reason,
                },
            )
            raise RuntimeError(f"Transaction reverted: {tx_hex} (Reason: {revert_reason})")

        log.info(
            "transaction confirmed",
            extra={
                "event": "tx_confirmed",
                "tx_hash": tx_hex,
                "block": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "status": receipt["status"],
                "caller": account.address,
            },
        )
        return tx_hex

    def _load_receipt(self, tx_hash: str):
        self._require_contract()
        tx_hash = tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash
        with self._rpc_lock:
            try:
                receipt = self._w3.eth.get_transaction_receipt(tx_hash)
                tx = self._w3.eth.get_transaction(tx_hash)
            except TransactionNotFound as exc:
                raise LookupError("Transaction not yet mined") from exc
        return tx_hash, receipt, tx

    def _require_success(self, receipt, tx_hash: str) -> None:
        if receipt["status"] != 1:
            raise ValueError(f"Transaction reverted: {tx_hash}")
        to_addr = receipt.get("to")
        if not to_addr or to_addr.lower() != settings.CONTRACT_ADDRESS.lower():
            raise ValueError("Transaction was not sent to ProductRegistry")

    # ── Calldata for wallet signing ───────────────────────────────────────────

    def prepare_registration(
        self,
        product_id: str,
        serial_number: str,
        model: str,
        batch: str,
        from_address: str | None = None,
    ) -> dict:
        self._require_contract()
        product_id_bytes32 = keccak256_id(product_id)
        product_hash = keccak256_product(product_id, serial_number, model, batch)
        fn = self._contract.functions.registerProduct(product_id_bytes32, product_hash)

        if from_address:
            signer = Web3.to_checksum_address(from_address)
            if not self.is_manufacturer(signer):
                raise ValueError(
                    f"Wallet '{signer}' is not an authorized manufacturer on-chain. "
                    "An admin must whitelist it before it can register products."
                )
            existing = self.get_product(product_id)
            if existing["registered_at"] != 0:
                raise ValueError(
                    f"Product '{product_id}' is already registered on-chain by {existing['manufacturer']}."
                )
            with self._rpc_lock:
                try:
                    fn.call({"from": signer})
                except Exception as sim_err:
                    raise ValueError(f"Contract execution reverted: {self._revert_text(sim_err)}") from sim_err

        return {
            "to": Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            "chain_id": settings.CHAIN_ID,
            "data": _calldata(fn),
            "value": "0x0",
            "product_id_bytes32": bytes32_to_hex(product_id_bytes32),
            "product_hash": bytes32_to_hex(product_hash),
        }

    def prepare_deactivation(self, product_id: str) -> dict:
        self._require_contract()
        product_id_bytes32 = keccak256_id(product_id)
        fn = self._contract.functions.deactivateProduct(product_id_bytes32)
        return {
            "to": Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            "chain_id": settings.CHAIN_ID,
            "data": _calldata(fn),
            "value": "0x0",
            "product_id_bytes32": bytes32_to_hex(product_id_bytes32),
        }

    def prepare_add_manufacturer(self, wallet_address: str, manufacturer_id: str, name: str) -> dict:
        self._require_contract()
        wallet_checksum = Web3.to_checksum_address(wallet_address)
        if self.is_manufacturer(wallet_checksum):
            raise ValueError(f"Wallet '{wallet_checksum}' is already an active manufacturer.")
        mfg_id_bytes32 = keccak256_id(manufacturer_id)
        fn = self._contract.functions.addManufacturer(wallet_checksum, mfg_id_bytes32, name)
        owner = None
        with self._rpc_lock:
            try:
                owner = self._contract.functions.owner().call()
            except Exception:
                owner = settings.CONTRACT_OWNER
        return {
            "to": Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            "chain_id": settings.CHAIN_ID,
            "data": _calldata(fn),
            "value": "0x0",
            "owner": owner,
            "wallet_address": wallet_checksum,
        }

    def registration_proof(self, tx_hash: str, product_id: str) -> dict:
        tx_hash, receipt, tx = self._load_receipt(tx_hash)
        self._require_success(receipt, tx_hash)
        expected_id = keccak256_id(product_id)
        events = self._contract.events.ProductRegistered().process_receipt(receipt)
        match = next(
            (ev for ev in events if _as_bytes32(ev["args"]["productId"]) == expected_id),
            None,
        )
        if match is None:
            raise ValueError("Receipt has no ProductRegistered event for this product id")
        try:
            _, params = self._contract.decode_function_input(tx["input"])
        except Exception as exc:
            raise ValueError("Transaction input is not a ProductRegistry call") from exc
        product_hash = params.get("productHash")
        if product_hash is None:
            raise ValueError("Transaction is not registerProduct")
        return {
            "tx_hash": tx_hash,
            "signer": tx["from"],
            "manufacturer": match["args"]["manufacturer"],
            "product_hash": bytes32_to_hex(_as_bytes32(product_hash)),
            "block_number": receipt["blockNumber"],
        }

    def deactivation_proof(self, tx_hash: str, product_id: str) -> dict:
        tx_hash, receipt, tx = self._load_receipt(tx_hash)
        self._require_success(receipt, tx_hash)
        expected_id = keccak256_id(product_id)
        events = self._contract.events.ProductDeactivated().process_receipt(receipt)
        match = next(
            (ev for ev in events if _as_bytes32(ev["args"]["productId"]) == expected_id),
            None,
        )
        if match is None:
            raise ValueError("Receipt has no ProductDeactivated event for this product id")
        on_chain = self.get_product(product_id)
        if on_chain["active"]:
            raise ValueError("Product is still active on-chain")
        return {
            "tx_hash": tx_hash,
            "signer": tx["from"],
            "deactivated_by": match["args"]["by"],
            "block_number": receipt["blockNumber"],
        }

    def manufacturer_added_proof(self, tx_hash: str, wallet_address: str) -> dict:
        tx_hash, receipt, tx = self._load_receipt(tx_hash)
        self._require_success(receipt, tx_hash)
        expected = Web3.to_checksum_address(wallet_address).lower()
        events = self._contract.events.ManufacturerAdded().process_receipt(receipt)
        match = next(
            (ev for ev in events if ev["args"]["wallet"].lower() == expected),
            None,
        )
        if match is None:
            raise ValueError("Receipt has no ManufacturerAdded event for this wallet")
        if not self.is_manufacturer(wallet_address):
            raise ValueError("Wallet is not an active manufacturer after this transaction")
        return {
            "tx_hash": tx_hash,
            "signer": tx["from"],
            "wallet": match["args"]["wallet"],
            "block_number": receipt["blockNumber"],
        }

    # ── Custodial admin writes (env key only, never a client-supplied key) ──

    def build_add_manufacturer(self, wallet_address: str, manufacturer_id: str, name: str):
        self._require_contract()
        wallet_checksum = Web3.to_checksum_address(wallet_address)
        if self.is_manufacturer(wallet_checksum):
            return None

        key = (settings.OWNER_PRIVATE_KEY or "").strip()
        if not key:
            raise ValueError("OWNER_PRIVATE_KEY is not set. The UI path signs addManufacturer in MetaMask instead.")

        account = Account.from_key(key)
        contract_owner = None
        with self._rpc_lock:
            try:
                contract_owner = self._contract.functions.owner().call()
            except Exception:
                contract_owner = settings.CONTRACT_OWNER
        if contract_owner and account.address.lower() != contract_owner.lower():
            raise ValueError(
                f"OWNER_PRIVATE_KEY address '{account.address}' is not the contract owner '{contract_owner}'."
            )

        return self._contract.functions.addManufacturer(
            wallet_checksum,
            keccak256_id(manufacturer_id),
            name,
        )

    def build_remove_manufacturer(self, wallet_address: str):
        self._require_contract()
        return self._contract.functions.removeManufacturer(Web3.to_checksum_address(wallet_address))

    # ── Read (view) functions ──────────────────────────────────────────────────

    def verify_product(self, product_id: str, serial_number: str, model: str, batch: str) -> dict:
        """Free view call. Recomputes the abi.encode hash and asks the contract."""
        self._require_contract()
        product_id_bytes32 = keccak256_id(product_id)
        product_hash_bytes = keccak256_product(product_id, serial_number, model, batch)
        with self._rpc_lock:
            is_authentic, manufacturer, registered_at, active = (
                self._contract.functions.verifyProduct(product_id_bytes32, product_hash_bytes).call()
            )
        result = {
            "is_authentic": is_authentic,
            "manufacturer": manufacturer,
            "registered_at": registered_at,
            "active": active,
            "product_hash": bytes32_to_hex(product_hash_bytes),
            # A copied label presents the same four strings, so a match is not
            # proof that this physical unit is unique.
            "record_match": bool(is_authentic),
        }
        log.info(
            "product verified",
            extra={"event": "product_verified", "product_id": product_id, "is_authentic": is_authentic},
        )
        return result

    def get_product(self, product_id: str) -> dict:
        self._require_contract()
        product_id_bytes32 = keccak256_id(product_id)
        with self._rpc_lock:
            product_hash, manufacturer, registered_at, active = (
                self._contract.functions.getProduct(product_id_bytes32).call()
            )
        return {
            "product_hash": bytes32_to_hex(product_hash),
            "manufacturer": manufacturer,
            "registered_at": registered_at,
            "active": active,
        }

    def is_manufacturer(self, wallet_address: str) -> bool:
        self._require_contract()
        with self._rpc_lock:
            return self._contract.functions.isManufacturer(
                Web3.to_checksum_address(wallet_address)
            ).call()

    def get_all_manufacturers(self) -> list[dict]:
        self._require_contract()
        with self._rpc_lock:
            raw = self._contract.functions.getAllManufacturers().call()
        return [
            {
                "id": bytes32_to_hex(m[0]),
                "name": m[1],
                "wallet": m[2],
                "added_at": m[3],
                "active": m[4],
            }
            for m in raw
        ]

    def network_info(self) -> dict:
        if self._w3 is None:
            return {"connected": False}
        try:
            with self._rpc_lock:
                owner_address = None
                connected = self._w3.is_connected()
                chain_id = self._w3.eth.chain_id if connected else None
                block_number = self._w3.eth.block_number if connected else None
                if self._contract and connected:
                    try:
                        owner_address = self._contract.functions.owner().call()
                    except Exception:
                        owner_address = None
            return {
                "connected": connected,
                "chain_id": chain_id,
                "block_number": block_number,
                "contract": settings.CONTRACT_ADDRESS,
                "contract_owner": owner_address or settings.CONTRACT_OWNER,
                "rpc": settings.ETH_RPC_URL,
            }
        except Exception as exc:
            return {"connected": False, "error": str(exc)}


blockchain = BlockchainService()
