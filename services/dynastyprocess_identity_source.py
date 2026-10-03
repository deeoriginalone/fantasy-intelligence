"""Acquire exact Sleeper-to-GSIS identities from the automated DynastyProcess artifact."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable
from urllib.request import Request, urlopen

COMMIT_API_URL = "https://api.github.com/repos/DynastyProcess/data/commits?path=files%2Fdb_playerids.csv&per_page=1"
RAW_FILE_URL = "https://raw.githubusercontent.com/DynastyProcess/data/{version}/files/db_playerids.csv"
ARTIFACT_ID = "DynastyProcess/files/db_playerids.csv"
SCHEMA_VERSION = "dynastyprocess-player-identities.v1"
LICENSE_ID = "GPL-3.0"
REQUIRED_COLUMNS = {"sleeper_id", "gsis_id"}


def acquire_dynastyprocess_identity_source(
    *,
    fetch_bytes: Callable[[str], bytes] | None = None,
    retrieved_at: Any = None,
) -> dict[str, Any]:
    """Fetch a file-versioned ID artifact and fail closed for duplicate Sleeper keys."""
    if fetch_bytes is None and retrieved_at is None:
        return _acquire_cached()
    return _acquire(fetch_bytes or _fetch_bytes, retrieved_at)


def refresh_dynastyprocess_identity_source() -> dict[str, Any]:
    """Clear process-local metadata and acquire the latest file release."""
    _acquire_cached.cache_clear()
    return _acquire_cached()


@lru_cache(maxsize=1)
def _acquire_cached() -> dict[str, Any]:
    return _acquire(_fetch_bytes, None)


def _acquire(fetch_bytes: Callable[[str], bytes], retrieved_at: Any) -> dict[str, Any]:
    retrieved = retrieved_at
    try:
        release_payload = json.loads(fetch_bytes(COMMIT_API_URL).decode("utf-8"))
        if not isinstance(release_payload, list) or not release_payload:
            return _blocked("DYNASTYPROCESS_RELEASE_UNAVAILABLE", retrieved)
        release = release_payload[0]
        version = str(release.get("sha") or "").strip()
        commit = release.get("commit") or {}
        source_recorded_at = str(
            (commit.get("committer") or {}).get("date")
            or (commit.get("author") or {}).get("date")
            or ""
        ).strip()
        if not re.fullmatch(r"[0-9a-fA-F]{40}", version) or not source_recorded_at:
            return _blocked("DYNASTYPROCESS_RELEASE_METADATA_UNVERIFIED", retrieved)
        source_url = RAW_FILE_URL.format(version=version)
        raw = fetch_bytes(source_url)
        checksum = hashlib.sha256(raw).hexdigest()
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except Exception:
        return _blocked("DYNASTYPROCESS_IDENTITY_RETRIEVAL_FAILED", retrieved)

    if not rows or not REQUIRED_COLUMNS.issubset(rows[0]):
        return _blocked("DYNASTYPROCESS_IDENTITY_SCHEMA_UNVERIFIED", retrieved)

    mapping_rows: dict[str, list[str]] = {}
    missing_sleeper_id_rows = 0
    missing_gsis_id_rows = 0
    for row in rows:
        sleeper_id = str(row.get("sleeper_id") or "").strip()
        gsis_id = str(row.get("gsis_id") or "").strip()
        if not sleeper_id:
            missing_sleeper_id_rows += 1
            continue
        mapping_rows.setdefault(sleeper_id, []).append(gsis_id)
        if not gsis_id:
            missing_gsis_id_rows += 1

    mappings = []
    duplicate_sleeper_id_count = 0
    contradictory_sleeper_id_count = 0
    resolved_mapping_count = 0
    unresolved_mapping_count = 0
    for sleeper_id, gsis_ids in mapping_rows.items():
        distinct_gsis_ids = sorted({value for value in gsis_ids if value})
        if len(gsis_ids) > 1:
            duplicate_sleeper_id_count += 1
            state = "CONTRADICTORY" if len(distinct_gsis_ids) > 1 else "AMBIGUOUS"
            blocker = "DYNASTYPROCESS_IDENTITY_CONTRADICTORY" if state == "CONTRADICTORY" else "DYNASTYPROCESS_IDENTITY_DUPLICATE"
            contradictory_sleeper_id_count += int(state == "CONTRADICTORY")
            gsis_id = None
        elif not distinct_gsis_ids:
            state = "UNRESOLVED"
            blocker = "DYNASTYPROCESS_GSIS_ID_UNAVAILABLE"
            gsis_id = None
            unresolved_mapping_count += 1
        else:
            state = "RESOLVED"
            blocker = None
            gsis_id = distinct_gsis_ids[0]
            resolved_mapping_count += 1
        mappings.append({
            "source_player_id": sleeper_id,
            "gsis_id": gsis_id,
            "state": state,
            "source_row_count": len(gsis_ids),
            "blocker": blocker,
        })

    mapped_source_row_count = sum(len(values) for values in mapping_rows.values())
    reconciliation = {
        "input_row_count": len(rows),
        "mapped_source_row_count": mapped_source_row_count,
        "missing_sleeper_id_row_count": missing_sleeper_id_rows,
        "reconciled": mapped_source_row_count + missing_sleeper_id_rows == len(rows),
        "resolved_mapping_count": resolved_mapping_count,
        "unresolved_mapping_count": unresolved_mapping_count,
        "duplicate_sleeper_id_count": duplicate_sleeper_id_count,
        "contradictory_sleeper_id_count": contradictory_sleeper_id_count,
        "missing_gsis_id_row_count": missing_gsis_id_rows,
    }
    if not reconciliation["reconciled"]:
        return _blocked("DYNASTYPROCESS_IDENTITY_RECONCILIATION_FAILED", retrieved)

    retrieved = retrieved or datetime.now(timezone.utc).isoformat()
    lineage = {
        "source": source_url,
        "source_authority": "automated:DynastyProcess",
        "artifact_id": ARTIFACT_ID,
        "version": version,
        "checksum": checksum,
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved,
        "schema_version": SCHEMA_VERSION,
        "license": LICENSE_ID,
        "license_url": f"https://github.com/DynastyProcess/data/blob/{version}/LICENSE",
        "delivery": "GitHub Actions automated player ID pipeline",
        "record_count": len(rows),
        "completeness_state": "COMPLETE",
        "reconciliation": reconciliation,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "AVAILABLE",
        "mappings": mappings,
        "lineage": lineage,
        "blockers": [],
        "decision_effect": "INFORMATIONAL_ONLY",
    }


def _fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "fantasy-intelligence-identity-source/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def _blocked(blocker: str, retrieved_at: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "BLOCKED",
        "mappings": [],
        "lineage": {
            "source": COMMIT_API_URL,
            "artifact_id": ARTIFACT_ID,
            "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
            "schema_version": SCHEMA_VERSION,
            "completeness_state": "UNAVAILABLE",
        },
        "blockers": [blocker],
        "decision_effect": "INFORMATIONAL_ONLY",
    }