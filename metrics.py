"""Log metrics JSON — Grafana correlation format."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .constants import METRICS_DIR


class MetricsLogger:
    def __init__(self) -> None:
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        self.log_file = METRICS_DIR / "log_metrics.json"

    def _load(self) -> dict[str, Any]:
        if self.log_file.exists():
            with self.log_file.open(encoding="utf-8") as f:
                return json.load(f)
        return {"metrics": [], "correlators": []}

    def _save(self, data: dict[str, Any]) -> None:
        with self.log_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def log_correlation(
        self,
        graph: dict[str, Any],
        decision: str,
        indice_state: dict[str, Any],
    ) -> None:
        data = self._load()
        metric = {
            "timestamp": time.time(),
            "grafana_correlation": {
                "shape": graph.get("shape"),
                "root_hash": graph.get("root_hash"),
                "node_count": len(graph.get("nodes", [])),
                "edge_count": len(graph.get("edges", [])),
            },
            "decision_data": {"action": decision, "indice_order": indice_state.get("order_index")},
            "correlators": {
                "latched_keys": list(indice_state.get("latched", {}).keys()),
                "rotation_block": indice_state.get("rotation_block"),
            },
        }
        data["metrics"].append(metric)
        data["correlators"].append({
            "ts": time.time(),
            "root_hash": graph.get("root_hash"),
        })
        self._save(data)

    def export_grafana_dashboard_stub(self) -> Path:
        """Minimal Grafana-compatible metric export."""
        stub = METRICS_DIR / "grafana_correlation_export.json"
        data = self._load()
        export = {
            "dashboard": "bitgenisis_x_correlation",
            "panels": [
                {"title": "Root Hash", "type": "stat", "targets": [m["grafana_correlation"] for m in data["metrics"][-10:]]},
            ],
        }
        with stub.open("w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)
        return stub
