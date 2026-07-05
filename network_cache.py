"""Network cache: traffic netcache, omega retention, layer latch."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any

from .constants import NETCACHE_DIR, dexhash, load_lock_matrix, parse_world_net_ranges


class NetworkCache:
    """Lock runtime hash addresses into network cache; zone mem paths to cache paths."""

    def __init__(self) -> None:
        self.omega = NETCACHE_DIR / "omega"
        self.traffic = NETCACHE_DIR / "traffic"
        self.cache_index = NETCACHE_DIR / "cache_index.json"
        self.omega.mkdir(parents=True, exist_ok=True)
        self.traffic.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict[str, Any]:
        if self.cache_index.exists():
            with self.cache_index.open(encoding="utf-8") as f:
                return json.load(f)
        return {"hosts": {}, "zones": {}, "frozen": False}

    def _save_index(self, data: dict[str, Any]) -> None:
        with self.cache_index.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def node_id(self) -> str:
        hostname = socket.gethostname()
        return dexhash(f"{hostname}:{socket.getfqdn()}")

    def lock_runtime_hash(self, address: str, external_path: str) -> None:
        idx = self._load_index()
        idx["hosts"][address] = {
            "external_path": external_path,
            "node": self.node_id(),
            "locked_at": time.time(),
            "omega": True,
        }
        self._save_index(idx)
        omega_file = self.omega / f"{dexhash(address)[:16]}.json"
        with omega_file.open("w", encoding="utf-8") as f:
            json.dump(idx["hosts"][address], f, indent=2)

    def zone_internal_to_external(self) -> dict[str, str]:
        """Zone all internal mem paths to all external cache paths."""
        mapping: dict[str, str] = {}
        for entry in parse_world_net_ranges():
            zone = entry["zone"]
            role = entry["role"]
            ext = str(self.omega if "omega" in zone or "external" in zone else self.traffic)
            mapping[f"{entry['cidr']}:{role}"] = ext
        idx = self._load_index()
        idx["zones"] = mapping
        self._save_index(idx)
        return mapping

    def send_traffic(self, layer: str, static_hash: str, payload: dict[str, Any]) -> None:
        flow = {
            "layer": layer,
            "static_hash": static_hash,
            "payload": payload,
            "from_node": self.node_id(),
            "ts": time.time(),
        }
        path = self.traffic / f"{static_hash[:16]}_{int(time.time())}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(flow, f, indent=2)

    def freeze_shares_block_override(self, partition_header: str) -> bool:
        """Lock state freeze _shares data block_override."""
        matrix = load_lock_matrix()
        if not matrix["lock_matrix"].get("block_override_enabled"):
            return False
        idx = self._load_index()
        idx["frozen"] = True
        idx["block_override"] = {
            "partition_header": partition_header,
            "cons_hash_gas_set_0": matrix["lock_matrix"]["cons_hash_gas_set_0"],
        }
        self._save_index(idx)
        return True

    def merge_to_external_cache(self, mem_data: dict[str, Any]) -> None:
        merge_file = self.omega / f"merge_{int(time.time())}.json"
        with merge_file.open("w", encoding="utf-8") as f:
            json.dump({"mem_data": mem_data, "merged_at": time.time()}, f, indent=2)

    def layer_latch_phase(self, sender_id: int) -> dict[str, Any]:
        """set layer latch to match phase(brake---order-0) rule."""
        matrix = load_lock_matrix()
        genesis = matrix["genesis_byte"]
        phase = matrix["phase_rule"]
        latch = {
            "phase": phase,
            "genesis_byte": genesis,
            "sender": sender_id,
            "haxi_order": matrix["haxi_order_net"],
            "self_loop": matrix["senders"][str(sender_id)]["self_loop"],
        }
        latch_file = self.omega / f"latch_sender_{sender_id}.json"
        with latch_file.open("w", encoding="utf-8") as f:
            json.dump(latch, f, indent=2)
        return latch

    def ingest_genesis_sender(self, sender_id: int) -> dict[str, Any]:
        """find_byte genesis ingest into sender(0) or sender(1)."""
        matrix = load_lock_matrix()
        genesis = matrix["genesis_byte"]
        self.lock_runtime_hash(genesis, str(self.omega))
        latch = self.layer_latch_phase(sender_id)
        chain_file = self.omega / f"sender_chain_{sender_id}.json"
        chain = {"genesis": genesis, "sender": sender_id, "links": [genesis], "self_loop": True}
        with chain_file.open("w", encoding="utf-8") as f:
            json.dump(chain, f, indent=2)
        return {"latch": latch, "chain": chain}
