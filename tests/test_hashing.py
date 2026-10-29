"""Hash preimage tests. These do not need a database or a chain."""

import sys
from pathlib import Path

from eth_abi import encode
from eth_abi.packed import encode_packed
from eth_utils import keccak

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))

from common.crypto.hashing import (  # noqa: E402
    build_canonical_string,
    bytes32_to_hex,
    keccak256_id,
    keccak256_product,
)


def test_product_hash_matches_abi_encode():
    digest = keccak256_product("P10001", "SN001928", "ABC-X1", "B2026-09")
    expected = keccak(encode(
        ["string", "string", "string", "string"],
        ["P10001", "SN001928", "ABC-X1", "B2026-09"],
    ))
    assert digest == expected
    assert len(digest) == 32
    assert bytes32_to_hex(digest).startswith("0x")
    assert len(bytes32_to_hex(digest)) == 66


def test_abi_encode_does_not_collide_when_encode_packed_does():
    """("ab","c") and ("a","bc") are different products. Packed encoding merges them."""
    fields = ["string", "string", "string", "string"]
    left = ["ab", "c", "m", "b"]
    right = ["a", "bc", "m", "b"]

    assert keccak(encode_packed(fields, left)) == keccak(encode_packed(fields, right))
    assert keccak256_product(*left) != keccak256_product(*right)
    assert keccak256_product(*left) == keccak(encode(fields, left))


def test_pipe_label_is_not_the_hash_preimage():
    label = build_canonical_string("P10001", "SN001928", "ABC-X1", "B2026-09")
    assert label == "P10001|SN001928|ABC-X1|B2026-09"
    assert keccak256_product("P10001", "SN001928", "ABC-X1", "B2026-09") != keccak(label.encode())


def test_id_is_right_padded_utf8():
    padded = keccak256_id("P10001")
    assert len(padded) == 32
    assert padded.startswith(b"P10001")
    assert padded.endswith(b"\x00" * 26)


def test_id_rejects_more_than_32_bytes():
    try:
        keccak256_id("x" * 33)
    except ValueError as exc:
        assert "32" in str(exc)
    else:
        raise AssertionError("expected ValueError")
