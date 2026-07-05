"""Bitcoin RPC and REST API integration using pipeline credentials."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any

from .pipeline_credentials import bitcoin_credentials


class BitcoinPipelineClient:
    """Query bitcoind RPC and/or public REST API for genesis and address data."""

    def __init__(self) -> None:
        self.creds = bitcoin_credentials()
        self.rpc_cfg = self.creds.get("rpc", {})
        self.api_cfg = self.creds.get("api", {})

    @property
    def rpc_enabled(self) -> bool:
        return bool(self.rpc_cfg.get("enabled"))

    @property
    def api_enabled(self) -> bool:
        return bool(self.api_cfg.get("enabled"))

    @property
    def rpc_configured(self) -> bool:
        return bool(self.rpc_cfg.get("user") and self.rpc_cfg.get("password"))

    def _rpc_url(self) -> str:
        host = self.rpc_cfg.get("host", "127.0.0.1")
        port = self.rpc_cfg.get("port", 8332)
        return f"http://{host}:{port}/"

    def _rpc_call(self, method: str, params: list[Any] | None = None) -> Any:
        if not self.rpc_enabled or not self.rpc_configured:
            raise RuntimeError("bitcoin_rpc_not_configured")
        payload = json.dumps({"jsonrpc": "1.0", "id": "bitgenisis", "method": method, "params": params or []}).encode()
        auth = base64.b64encode(f"{self.rpc_cfg['user']}:{self.rpc_cfg['password']}".encode()).decode()
        req = urllib.request.Request(
            self._rpc_url(),
            data=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            method="POST",
        )
        timeout = int(self.rpc_cfg.get("timeout_sec", 30))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
        if body.get("error"):
            raise RuntimeError(body["error"])
        return body.get("result")

    def _api_get(self, path: str) -> Any:
        if not self.api_enabled:
            raise RuntimeError("bitcoin_api_disabled")
        base = str(self.api_cfg.get("base_url", "")).rstrip("/")
        url = f"{base}{path}"
        headers: dict[str, str] = {"Accept": "application/json"}
        api_key = self.api_cfg.get("api_key")
        if api_key:
            header = self.api_cfg.get("api_key_header", "Authorization")
            headers[header] = f"Bearer {api_key}" if header.lower() != "x-api-key" else api_key
        req = urllib.request.Request(url, headers=headers, method="GET")
        timeout = int(self.api_cfg.get("timeout_sec", self.rpc_cfg.get("timeout_sec", 30)))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None

    def _api_get_optional(self, path: str) -> Any | None:
        try:
            return self._api_get(path)
        except (RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def get_blockchain_info_rpc(self) -> dict[str, Any] | None:
        try:
            result = self._rpc_call("getblockchaininfo")
            return result if isinstance(result, dict) else None
        except (RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def get_block_rpc(self, block_hash: str, verbosity: int = 1) -> dict[str, Any] | None:
        try:
            result = self._rpc_call("getblock", [block_hash, verbosity])
            return result if isinstance(result, dict) else None
        except (RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def get_block_hash_rpc(self, height: int = 0) -> str | None:
        try:
            result = self._rpc_call("getblockhash", [height])
            return str(result) if result else None
        except (RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def get_genesis_block_api(self) -> dict[str, Any] | None:
        try:
            block_hash = self._api_get("/block-height/0")
            if not block_hash:
                return None
            block = self._api_get(f"/block/{block_hash}")
            return block if isinstance(block, dict) else None
        except (RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def get_address_api(self, address: str) -> dict[str, Any] | None:
        try:
            summary = self._api_get(f"/address/{address}")
            if not isinstance(summary, dict):
                return None
            stats = summary.get("chain_stats", {})
            funded = int(stats.get("funded_txo_sum", 0))
            spent = int(stats.get("spent_txo_sum", 0))
            balance_sat = funded - spent
            utxos = self._api_get_optional(f"/address/{address}/utxo")
            txs = self._api_get_optional(f"/address/{address}/txs/chain")
            return {
                "address": address,
                "balance_sat": balance_sat,
                "balance_btc": balance_sat / 1e8,
                "tx_count": stats.get("tx_count", 0),
                "funded_txo_count": stats.get("funded_txo_count", 0),
                "spent_txo_count": stats.get("spent_txo_count", 0),
                "utxo_count": len(utxos) if isinstance(utxos, list) else stats.get("funded_txo_count", 0),
                "recent_txids": [t.get("txid") for t in txs[:3]] if isinstance(txs, list) else [],
                "source": "api",
            }
        except (RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def fetch_genesis_intel(self, genesis_address: str) -> dict[str, Any]:
        """Aggregate RPC + API data for genesis block and genesis address."""
        intel: dict[str, Any] = {
            "genesis_address": genesis_address,
            "rpc": {"configured": self.rpc_configured, "reachable": False},
            "api": {"enabled": self.api_enabled, "reachable": False},
        }

        if self.rpc_configured:
            chain = self.get_blockchain_info_rpc()
            if chain:
                intel["rpc"]["reachable"] = True
                intel["rpc"]["blockchain"] = {
                    "chain": chain.get("chain"),
                    "blocks": chain.get("blocks"),
                    "bestblockhash": chain.get("bestblockhash"),
                    "difficulty": chain.get("difficulty"),
                }
            block_hash = self.get_block_hash_rpc(0)
            if block_hash:
                block = self.get_block_rpc(block_hash, verbosity=1)
                if block:
                    intel["rpc"]["genesis_block"] = {
                        "hash": block.get("hash", block_hash),
                        "height": block.get("height", 0),
                        "time": block.get("time"),
                        "merkleroot": block.get("merkleroot"),
                        "nonce": block.get("nonce"),
                    }

        address_info = self.get_address_api(genesis_address)
        if address_info:
            intel["api"]["reachable"] = True
            intel["address"] = address_info

        genesis_api = self.get_genesis_block_api()
        if genesis_api:
            intel["api"]["reachable"] = True
            intel["api"]["genesis_block"] = {
                "id": genesis_api.get("id"),
                "height": genesis_api.get("height", 0),
                "timestamp": genesis_api.get("timestamp"),
                "merkle_root": genesis_api.get("merkle_root"),
                "nonce": genesis_api.get("nonce"),
                "size": genesis_api.get("size"),
            }

        intel["sources_used"] = []
        if intel["rpc"].get("reachable"):
            intel["sources_used"].append("rpc")
        if intel["api"].get("reachable"):
            intel["sources_used"].append("api")

        return intel
