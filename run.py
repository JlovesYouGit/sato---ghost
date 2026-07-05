#!/usr/bin/env python3
"""BITGENISIS entry point — first-run init then autonomous const apply."""

from __future__ import annotations

import json
import sys

from src.orchestrator import Orchestrator


def main() -> int:
    orch = Orchestrator()
    if not orch.is_initialized():
        print("[INIT] First run — initializing swap memuar, hashbank, network cache...")
        result = orch.first_run_init()
        print("[INIT] Complete. Nodes agreed:", result.get("auto_apply"))
    else:
        print("[AUTO] Initialized — applying const without host intervention...")
        results = orch.auto_run_loop(cycles=1)
        result = results[-1] if results else {}

    btc = result.get("bitcoin", {})
    addr = btc.get("address", {})
    summary = {
        "node_id": result.get("node_id"),
        "order_index": result.get("order_index"),
        "root_hash": result.get("root_hash"),
        "rotation_hash": result.get("rotation_hash"),
        "indice": result.get("indice"),
        "block_override": result.get("block_override"),
        "zones_mapped": len(result.get("zones", {})),
        "senders_linked": len(result.get("senders", [])),
        "bitcoin_sources": btc.get("sources_used", []),
        "bitcoin_rpc_reachable": btc.get("rpc", {}).get("reachable", False),
        "bitcoin_api_reachable": btc.get("api", {}).get("reachable", False),
        "genesis_balance_btc": addr.get("balance_btc"),
        "genesis_tx_count": addr.get("tx_count"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
