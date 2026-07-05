"""Immutable constants loaded from lock_matrix and address registry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "lock_matrix.json"
WORLD_NET_RANGE = ROOT / "addresses" / "world_net_range.txt"
HASH_HOSTS = ROOT / "addresses" / "hash_hosts.md"
DATA_DIR = ROOT / "data"
HASHBANK_DIR = DATA_DIR / "hashbank"
NETCACHE_DIR = DATA_DIR / "netcache"
METRICS_DIR = DATA_DIR / "metrics"
STATE_FILE = DATA_DIR / "node_state.json"
INIT_FLAG = DATA_DIR / ".initialized"


def load_lock_matrix() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def dexhash(value: str) -> str:
    """Numerical DEXhash / index directional hash map."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def phrase_to_indice(phrase: str) -> int:
    """Enforce phrase-to-indice conversion from lock matrix."""
    h = dexhash(phrase)
    return int(h[:16], 16)


def parse_world_net_ranges() -> list[dict[str, str]]:
    ranges: list[dict[str, str]] = []
    if not WORLD_NET_RANGE.exists():
        return ranges
    for line in WORLD_NET_RANGE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            ranges.append({"cidr": parts[0], "role": parts[1], "zone": parts[2]})
    return ranges


def ensure_data_dirs() -> None:
    for d in (HASHBANK_DIR, NETCACHE_DIR / "omega", NETCACHE_DIR / "traffic",
              METRICS_DIR, HASHBANK_DIR / "swap_memuar"):
        d.mkdir(parents=True, exist_ok=True)
