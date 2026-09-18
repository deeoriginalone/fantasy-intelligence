"""Read-only nflverse player metadata acquisition for identity resolution."""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.request import urlopen

PLAYERS_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
TIMESTAMP_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/timestamp.txt"
ARTIFACT_ID = "nflverse.players.csv"
SCHEMA_VERSION = "nflverse-player-metadata.v1"
_REQUIRED_COLUMNS = {"gsis_id"}


def acquire_nflverse_player_metadata(
    *,
    fetch_bytes: Callable[[str], bytes] | None = None,
    retrieved_at: Any = None,
) -> dict[str, Any]:
    """Acquire and validate provider-supplied player identity metadata in memory."""
    fetch = fetch_bytes or _fetch_bytes
    retrieved = retrieved_at or datetime.now(timezone.utc).isoformat()
    try:
        raw = fetch(PLAYERS_URL)
        checksum = hashlib.sha256(raw).hexdigest()
        source_recorded_at = fetch(TIMESTAMP_URL).decode("utf-8").strip()
        version = source_recorded_at
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except Exception:
        return _blocked("NFLVERSE_PLAYER_METADATA_RETRIEVAL_FAILED", retrieved)
    if not checksum:
        return _blocked("NFLVERSE_PLAYER_METADATA_CHECKSUM_UNAVAILABLE", retrieved)
    if not version:
        return _blocked("NFLVERSE_PLAYER_METADATA_VERSION_UNAVAILABLE", retrieved)
    if not rows or not _REQUIRED_COLUMNS.issubset(rows[0]):
        return _blocked("NFLVERSE_PLAYER_METADATA_SCHEMA_UNVERIFIED", retrieved)
    lineage = {
        "source": PLAYERS_URL,
        "source_authority": "automated:nflverse",
        "artifact_id": ARTIFACT_ID,
        "version": version,
        "checksum": checksum,
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved,
        "schema_version": SCHEMA_VERSION,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "AVAILABLE",
        "rows": rows,
        "lineage": lineage,
        "blockers": [],
        "decision_effect": "INFORMATIONAL_ONLY",
    }


def _fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def _blocked(blocker: str, retrieved_at: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "BLOCKED",
        "rows": [],
        "lineage": {"source": PLAYERS_URL, "artifact_id": ARTIFACT_ID, "retrieved_at": retrieved_at, "schema_version": SCHEMA_VERSION},
        "blockers": [blocker],
        "decision_effect": "INFORMATIONAL_ONLY",
    }
