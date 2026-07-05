"""Main orchestrator — first-run init, auto-apply const without host intervention."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .bitcoin_client import BitcoinPipelineClient
from .bit_engine import (
    alphabetic_to_numerical,
    build_x_variant_graph,
    byte_to_hex_list,
    hash_to_alphabetic_correlated,
    hex_list_to_bytes,
    numerical_to_hash_bank,
    odd_numeral_nonce,
)
from .consensus import NodeConsensus
from .constants import (
    DATA_DIR,
    HASHBANK_DIR,
    INIT_FLAG,
    ensure_data_dirs,
    load_lock_matrix,
    phrase_to_indice,
)
from .hashbank import HashBank
from .indices import IndiceLatch
from .metrics import MetricsLogger
from .network_cache import NetworkCache


class Orchestrator:
    """Runs full instruction pipeline; after init, applies const autonomously."""

    CYCLE_INTERVAL_SEC = 5

    def __init__(self) -> None:
        ensure_data_dirs()
        self.matrix = load_lock_matrix()
        self.hashbank = HashBank()
        self.latch = IndiceLatch(DATA_DIR / "indice_latch.json")
        self.netcache = NetworkCache()
        self.metrics = MetricsLogger()
        self.node_id = self.netcache.node_id()
        self.consensus = NodeConsensus(self.node_id)
        self.bitcoin = BitcoinPipelineClient()

    def _fetch_bitcoin_genesis(self) -> dict[str, Any]:
        genesis = self.matrix["genesis_byte"]
        intel = self.bitcoin.fetch_genesis_intel(genesis)
        self.hashbank.save("bitcoin_genesis", intel, meta={"source": "pipeline_credentials"})
        self.netcache.lock_runtime_hash(
            f"btc:{genesis}",
            str(self.netcache.omega),
        )
        return intel

    def _bit_intake_pipeline(self) -> dict[str, Any]:
        genesis = self.matrix["genesis_byte"]
        lock_block = self.matrix["rotation_lock_block"]
        hex_list = byte_to_hex_list(genesis.encode("utf-8"))
        hex_list.extend(byte_to_hex_list(lock_block.encode("utf-8")[:24]))
        graph = build_x_variant_graph(hex_list)
        internal_cache = hex_list_to_bytes(hex_list)
        return {"hex_list": hex_list, "graph": graph, "internal_cache": internal_cache.hex()}

    def _emergent_override_factors(self, order_index: int) -> dict[str, Any]:
        nums = alphabetic_to_numerical(self.matrix["target_phrase"])
        hash_bank = numerical_to_hash_bank(nums)
        alpha_corr = hash_to_alphabetic_correlated(hash_bank)
        nonce = odd_numeral_nonce(order_index)
        limit = self.latch.limit_order(order_index)
        return {
            "hash_bank": hash_bank,
            "alpha_correlated": alpha_corr,
            "nonce": nonce,
            "limit_order": limit,
        }

    def _apply_const_overrides(self, state: dict[str, Any]) -> dict[str, Any]:
        """Instruction influence over all space orders with latch override."""
        partition = self.matrix["lock_matrix"]["cons_hash_gas_set_0"]
        self.netcache.freeze_shares_block_override(partition)
        zones = self.netcache.zone_internal_to_external()
        self.netcache.merge_to_external_cache(state)
        state["zones"] = zones
        state["block_override"] = True
        return state

    def run_pipeline(self) -> dict[str, Any]:
        pipeline = self._bit_intake_pipeline()
        graph = pipeline["graph"]

        indice = self.latch.enforce_phrase_lock()
        rotation_hash = self.latch.apply_rotation_block()
        self.latch.push_to_all_indices(graph)

        order_index = phrase_to_indice(self.matrix["target_phrase"]) % 1000
        emergent = self._emergent_override_factors(order_index)

        for addr in (self.matrix["genesis_byte"], self.matrix["rotation_lock_block"]):
            self.netcache.lock_runtime_hash(addr, str(self.netcache.omega))

        sender_results = []
        for sender_id in (0, 1):
            result = self.netcache.ingest_genesis_sender(sender_id)
            sender_results.append(result)

        bitcoin_intel = self._fetch_bitcoin_genesis()

        self.netcache.send_traffic("layer_0", graph["root_hash"], {"graph": graph["shape"]})
        self.hashbank.save("x_graph", graph)
        self.hashbank.initialise_swap_memuar({"order_index": order_index, "root_hash": graph["root_hash"]})

        state: dict[str, Any] = {
            "node_id": self.node_id,
            "order_index": order_index,
            "indice": indice,
            "rotation_hash": rotation_hash,
            "root_hash": graph["root_hash"],
            "emergent": emergent,
            "senders": sender_results,
            "bitcoin": bitcoin_intel,
            "pipeline": pipeline,
            "auto_apply": self.matrix.get("auto_apply_after_init", True),
        }

        state = self._apply_const_overrides(state)
        self.metrics.log_correlation(graph, "apply_const", self.latch.state)
        self.metrics.export_grafana_dashboard_stub()

        proposal_id = self.consensus.propose(state)
        if self.consensus.all_nodes_agree(proposal_id):
            self.consensus.commit(state, proposal_id)

        return state

    def first_run_init(self) -> dict[str, Any]:
        result = self.run_pipeline()
        INIT_FLAG.write_text(json.dumps({"initialized_at": time.time(), "node_id": self.node_id}), encoding="utf-8")
        return result

    def is_initialized(self) -> bool:
        return INIT_FLAG.exists()

    def auto_run_loop(self, cycles: int = 3) -> list[dict[str, Any]]:
        """Apply const without host intervention after first init."""
        if not self.is_initialized():
            return [self.first_run_init()]

        results = []
        for _ in range(cycles):
            committed = self.consensus.load_committed_state()
            if committed:
                order_index = (committed.get("order_index", 0) + 1) % 10000
                state = self.run_pipeline()
                state["order_index"] = order_index
                proposal_id = self.consensus.propose(state)
                if self.consensus.all_nodes_agree(proposal_id):
                    self.consensus.commit(state, proposal_id)
                results.append(state)
            else:
                results.append(self.run_pipeline())
            time.sleep(self.CYCLE_INTERVAL_SEC)
        return results
