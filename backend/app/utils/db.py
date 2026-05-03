from __future__ import annotations

from typing import Dict, Any

# Pure in-memory store — no file persistence needed.
# Each /generate-latest/ call fetches live RSS so old data is irrelevant.
_store: Dict[str, Dict[str, Any]] = {}


def save_store() -> None:
    """No-op — store is intentionally ephemeral."""
    pass


def get_store() -> Dict[str, Dict[str, Any]]:
    return _store




