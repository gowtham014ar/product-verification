"""
Hashing utilities shared across all services.

The on-chain fingerprint is:

    keccak256(abi.encode(productId, serialNumber, model, batch))

abi.encode length-prefixes each string. abi.encodePacked does not, so
("ab","c") and ("a","bc") produce the same packed digest. That collision
is a cloned-preimage bug, not a property of Keccak.

The pipe form productId|serial|model|batch is only a human-readable label.
It is not the hash preimage.
"""

from eth_abi import encode  # type: ignore
from eth_utils import keccak  # type: ignore


def build_canonical_string(product_id: str, serial: str, model: str, batch: str) -> str:
    """Human-readable label used in logs and on a printed QR. Not the hash preimage."""
    return f"{product_id}|{serial}|{model}|{batch}"


def keccak256_product(product_id: str, serial: str, model: str, batch: str) -> bytes:
    """
    Compute the on-chain product hash.

    Matches ProductRegistry.hashProduct:
        keccak256(abi.encode(productId, serial, model, batch))
    Returns the raw 32-byte digest.
    """
    encoded = encode(
        ["string", "string", "string", "string"],
        [product_id, serial, model, batch],
    )
    return keccak(encoded)


def keccak256_id(value: str) -> bytes:
    """
    Convert a string ID to bytes32 for productId / manufacturerId.
    Pads right with zeros to 32 bytes (matches Solidity bytes32 casting).
    """
    encoded = value.encode("utf-8")
    if len(encoded) > 32:
        raise ValueError(f"ID '{value}' exceeds 32 bytes when UTF-8 encoded")
    return encoded.ljust(32, b"\x00")


def bytes32_to_hex(b: bytes) -> str:
    """Return 0x-prefixed hex string from 32-byte value."""
    raw = b.hex()
    return raw if raw.startswith("0x") else "0x" + raw
