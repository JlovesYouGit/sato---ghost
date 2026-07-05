"""Index latch, phrase enforcement, rotation block limits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import dexhash, load_lock_matrix, phrase_to_indice


class IndiceLatch:
    """Find indice — latch indice mem with override factors."""

    def __init__(self, latch_path: Path) -> None:
        self.path = latch_path
        self._state: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                return json.load(f)
        return {"latched": {}, "order_index": 0}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def enforce_phrase_lock(self) -> int:
        matrix = load_lock_matrix()
        phrase = matrix["target_phrase"]
        idx = phrase_to_indice(phrase)
        self._state["latched"][phrase] = {
            "indice": idx,
            "dexhash": dexhash(phrase),
            "locked": True,
        }
        self._save()
        return idx

    def latch_mem(self, key: str, value: Any, override: bool = False) -> None:
        entry = self._state["latched"].get(key, {})
        if entry.get("locked") and not override:
            return
        self._state["latched"][key] = {
            "value": value,
            "dexhash": dexhash(str(value)),
            "locked": True,
            "override": override,
        }
        self._save()

    def apply_rotation_block(self) -> str:
        matrix = load_lock_matrix()
        block = matrix["rotation_lock_block"]
        directional = dexhash(block)
        self._state["rotation_block"] = {
            "block": block,
            "directional_hash": directional,
            "limit": "all",
        }
        self._save()
        return directional

    def limit_order(self, index_i: int) -> int:
        """cons^limitOrder(consoverallorder_index_i)."""
        self._state["order_index"] = index_i
        limit = (index_i ** 2) % (2 ** 32)
        self._state["limit_order"] = limit
        self._save()
        return limit

    def push_to_all_indices(self, payload: dict[str, Any]) -> None:
        for key in list(self._state["latched"].keys()):
            entry = self._state["latched"][key]
            if isinstance(entry, dict):
                entry["last_push"] = payload.get("root_hash", "")
        self._state["last_correlated_shape"] = payload
        self._save()

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._state)
