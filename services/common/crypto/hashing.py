"""
Hashing utilities shared across all services.

Mirrors exactly what ProductRegistry.sol expects:
  keccak256(abi.encodePacked(productId, serial, model, batch))
"""

from eth_abi.packed import encode_packed  # type: ignore
from eth_utils import keccak              # type: ignore


def build_canonical_string(product_id: str, serial: str, model: str, batch: str) -> str:
    """Human-readable canonical form used in logs / QR payload."""
    return f"{product_id}|{serial}|{model}|{batch}"


def keccak256_product(product_id: str, serial: str, model: str, batch: str) -> bytes:
    """
    Compute the on-chain product hash.

    Matches Solidity: keccak256(abi.encodePacked(productId, serial, model, batch))
    Returns raw 32-byte digest.
    """
    packed = encode_packed(
        ["string", "string", "string", "string"],
        [product_id, serial, model, batch],
    )
    return keccak(packed)


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
    return "0x" + b.hex()
