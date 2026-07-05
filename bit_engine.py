"""Bit intake, byte mirror, X-variant graph correlation."""

from __future__ import annotations

import hashlib
from typing import Any


def hex_list_to_bytes(hex_list: list[str]) -> bytes:
    """Convert hexadecimal list log to byte mirror."""
    out = bytearray()
    for h in hex_list:
        h = h.strip().replace("0x", "")
        if len(h) % 2:
            h = "0" + h
        out.extend(bytes.fromhex(h))
    return bytes(out)


def bit_to_byte(bits: str) -> bytes:
    """Intake byte from bit string."""
    bits = bits.replace(" ", "")
    pad = (8 - len(bits) % 8) % 8
    bits = bits + "0" * pad
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))


def byte_to_bit(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


def byte_to_hex_list(data: bytes) -> list[str]:
    return [f"{b:02x}" for b in data]


def build_x_variant_graph(hex_list: list[str]) -> dict[str, Any]:
    """Correlated shape X — graph nodes from bit/byte pipeline."""
    raw = hex_list_to_bytes(hex_list)
    bit_str = byte_to_bit(raw)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for i, hx in enumerate(hex_list):
        nid = f"n_{i}"
        nodes.append({"id": nid, "hex": hx, "bit": byte_to_bit(bytes.fromhex(hx.zfill(2)[-2:]))})
        if i > 0:
            edges.append({"from": f"n_{i-1}", "to": nid, "type": "byte_chain"})
    digest = hashlib.sha256(raw).hexdigest()
    nodes.append({"id": "x_root", "hash": digest, "variant": "X"})
    for n in nodes[:-1]:
        edges.append({"from": n["id"], "to": "x_root", "type": "correlate"})
    return {"shape": "X", "nodes": nodes, "edges": edges, "root_hash": digest}


def odd_numeral_nonce(value: int) -> int:
    """Odd numeral convert to num^equal nonce digits."""
    if value % 2 == 0:
        value += 1
    digits = len(str(value))
    return value ** digits


def alphabetic_to_numerical(text: str) -> list[int]:
    return [ord(c) for c in text]


def numerical_to_hash_bank(nums: list[int]) -> str:
    payload = ",".join(str(n) for n in nums)
    return hashlib.sha256(payload.encode()).hexdigest()


def hash_to_alphabetic_correlated(hex_hash: str, length: int = 16) -> str:
    """Map hash back to alphabetic correlated representation."""
    chars = []
    for i in range(0, min(len(hex_hash), length * 2), 2):
        code = int(hex_hash[i : i + 2], 16)
        chars.append(chr(65 + (code % 26)))
    return "".join(chars)
