"""Hashbank storage and swap memuar initialization."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .constants import HASHBANK_DIR


class HashBank:
    def __init__(self) -> None:
        self.root = HASHBANK_DIR
        self.swap_memuar = self.root / "swap_memuar"
        self.bank_file = self.root / "hashbank.json"
        self.swap_memuar.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if self.bank_file.exists():
            with self.bank_file.open(encoding="utf-8") as f:
                return json.load(f)
        return {"entries": {}, "swap_chain": []}

    def _save(self, data: dict[str, Any]) -> None:
        with self.bank_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save(self, key: str, value: Any, meta: dict[str, Any] | None = None) -> str:
        data = self._load()
        entry = {"value": value, "meta": meta or {}, "ts": time.time()}
        data["entries"][key] = entry
        self._save(data)
        return key

    def initialise_swap_memuar(self, metric_order: dict[str, Any]) -> None:
        data = self._load()
        swap_entry = {
            "metric_order": metric_order,
            "ts": time.time(),
            "memuar_id": f"swap_{int(time.time())}",
        }
        data["swap_chain"].append(swap_entry)
        swap_file = self.swap_memuar / f"{swap_entry['memuar_id']}.json"
        with swap_file.open("w", encoding="utf-8") as f:
            json.dump(swap_entry, f, indent=2)
        self._save(data)

    def get(self, key: str) -> Any | None:
        data = self._load()
        entry = data["entries"].get(key)
        return entry["value"] if entry else None
