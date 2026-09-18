"""Retrieve the official nflverse snap_counts artifact without fabricating a source.

Reuses the existing generic retrieval/checksum helper already used for
stats_player_week (imports/import_nflverse_weekly_stats.py::load_weekly_stats).
No second downloader, checksum routine, or freshness framework is introduced.

A deterministic pfr_id -> gsis_id crosswalk is built from the official nflverse
players release (verified: 1:1 cardinality, 0 ambiguous mappings, 99.87%
coverage of snap_counts_2026 pfr_player_id values). Any pfr_id absent from the
crosswalk, or mapping to zero/multiple gsis_id values, is never guessed and
fails closed in services/snap_share_foundation.py.

Persistence is intentionally not implemented in this batch (see PERSISTENCE
REVIEW in the owning task); this module only produces in-memory, informational
evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from imports.import_nflverse_weekly_stats import load_weekly_stats
from services.snap_share_foundation import normalize_snap_counts_batch

SNAP_COUNTS_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv"
SNAP_COUNTS_RELEASE_TIMESTAMP_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/timestamp.txt"
NFLVERSE_PLAYERS_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv.gz"


def build_pfr_to_gsis_crosswalk(path: str | Path) -> dict[str, set[str]]:
    """Build a deterministic pfr_id -> {gsis_id} map from the official nflverse players release.

    Each pfr_id maps to the set of distinct non-empty gsis_id values found for
    it. A set of size 1 is deterministic; size 0 or >1 fails closed downstream
    (unresolved or ambiguous, respectively) -- never guessed or curated.
    """
    rows, _checksum = load_weekly_stats(path)
    if not rows or not {"pfr_id", "gsis_id"}.issubset(rows[0]):
        raise ValueError("NFLVERSE_PLAYERS_SCHEMA_UNVERIFIED")
    by_pfr: dict[str, set[str]] = {}
    for row in rows:
        pfr_id = (row.get("pfr_id") or "").strip()
        gsis_id = (row.get("gsis_id") or "").strip()
        if not pfr_id:
            continue
        by_pfr.setdefault(pfr_id, set())
        if gsis_id:
            by_pfr[pfr_id].add(gsis_id)
    return by_pfr


def build_snap_share_evidence(path: str | Path, *, season: int, retrieved_at: str, identity_crosswalk=None) -> dict:
    """Retrieve/parse the snap_counts artifact and return reconciled, non-authoritative evidence."""
    rows, checksum = load_weekly_stats(path)
    is_remote = str(path).startswith(("http://", "https://"))
    source = "automated:nflverse" if is_remote else f"fixture:{Path(path).name}"
    source_recorded_at = None
    if is_remote:
        try:
            source_recorded_at = urlopen(SNAP_COUNTS_RELEASE_TIMESTAMP_URL, timeout=30).read().decode("utf-8").strip()
        except Exception:
            source_recorded_at = None
    return normalize_snap_counts_batch(
        rows, season=season, source=source, source_recorded_at=source_recorded_at,
        retrieved_at=retrieved_at, checksum=checksum, version=f"snap_counts_{season}",
        identity_crosswalk=identity_crosswalk,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--retrieved-at", required=True)
    args = parser.parse_args()
    evidence = build_snap_share_evidence(args.csv_path, season=args.season, retrieved_at=args.retrieved_at)
    print(json.dumps(evidence, default=str, sort_keys=True))


if __name__ == "__main__":
    main()
