"""Node consensus — all nodes must agree before const apply."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .constants import DATA_DIR, STATE_FILE, dexhash


class NodeConsensus:
    """Multi-node agreement on order index and state hash."""

    VOTES_DIR = DATA_DIR / "consensus_votes"

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.VOTES_DIR.mkdir(parents=True, exist_ok=True)

    def propose(self, state: dict[str, Any]) -> str:
        proposal_id = dexhash(json.dumps(state, sort_keys=True))[:16]
        vote = {
            "proposal_id": proposal_id,
            "node_id": self.node_id,
            "state_hash": dexhash(json.dumps(state, sort_keys=True)),
            "order_index": state.get("order_index", 0),
            "ts": time.time(),
            "agree": True,
        }
        vote_file = self.VOTES_DIR / f"{proposal_id}_{self.node_id}.json"
        with vote_file.open("w", encoding="utf-8") as f:
            json.dump(vote, f, indent=2)
        return proposal_id

    def collect_votes(self, proposal_id: str) -> list[dict[str, Any]]:
        votes = []
        for vf in self.VOTES_DIR.glob(f"{proposal_id}_*.json"):
            with vf.open(encoding="utf-8") as f:
                votes.append(json.load(f))
        return votes

    def all_nodes_agree(self, proposal_id: str, min_nodes: int = 1) -> bool:
        """After first run, local node votes; multi-instance votes converge."""
        votes = self.collect_votes(proposal_id)
        if len(votes) < min_nodes:
            return False
        state_hashes = {v["state_hash"] for v in votes if v.get("agree")}
        order_indices = {v["order_index"] for v in votes if v.get("agree")}
        return len(state_hashes) == 1 and len(order_indices) == 1

    def commit(self, state: dict[str, Any], proposal_id: str) -> bool:
        if not self.all_nodes_agree(proposal_id):
            return False
        committed = {
            "proposal_id": proposal_id,
            "state": state,
            "committed_at": time.time(),
            "nodes_agreed": True,
        }
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(committed, f, indent=2)
        return True

    def load_committed_state(self) -> dict[str, Any] | None:
        if not STATE_FILE.exists():
            return None
        with STATE_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
        return data.get("state")
