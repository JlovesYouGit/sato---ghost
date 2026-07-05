"""Load and resolve pipeline credentials (env-var substitution)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .constants import ROOT

CREDENTIALS_PATH = ROOT / "config" / "pipeline_credentials.json"
LOCAL_CREDENTIALS_PATH = ROOT / "config" / "pipeline_credentials.local.json"

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _resolve_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        var, default = match.group(1), match.group(2)
        env_val = os.environ.get(var)
        if env_val is not None and env_val != "":
            return env_val
        return default if default is not None else ""

    if not isinstance(value, str):
        return value
    return _ENV_PATTERN.sub(repl, value)


def _resolve_tree(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _resolve_tree(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_tree(v) for v in node]
    if isinstance(node, str):
        resolved = _resolve_env(node)
        if resolved.isdigit():
            return int(resolved)
        return resolved
    return node


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_pipeline_credentials() -> dict[str, Any]:
    with CREDENTIALS_PATH.open(encoding="utf-8") as f:
        creds = json.load(f)
    if LOCAL_CREDENTIALS_PATH.exists():
        with LOCAL_CREDENTIALS_PATH.open(encoding="utf-8") as f:
            creds = _deep_merge(creds, json.load(f))
    return _resolve_tree(creds)


def bitcoin_credentials() -> dict[str, Any]:
    return load_pipeline_credentials().get("bitcoin", {})
