"""Retrieve and publish official nflverse snap_counts with exact GSIS identity."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen

from imports.import_nflverse_weekly_stats import load_weekly_stats
from services.snap_share_foundation import SNAP_COUNTS_REQUIRED_COLUMNS, normalize_snap_counts_batch
from services.snap_share_publication import publish_snap_share
from dotenv import load_dotenv

SNAP_COUNTS_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv"
SNAP_COUNTS_RELEASE_TIMESTAMP_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/timestamp.txt"
NFLVERSE_PLAYERS_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv.gz"
NFLVERSE_PLAYERS_RELEASE_TIMESTAMP_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/timestamp.txt"


def build_pfr_to_gsis_crosswalk(path: str | Path, *, include_lineage: bool = False, retrieved_at: str | None = None):
    """Build a deterministic pfr_id -> {gsis_id} map from the official nflverse players release.

    Each pfr_id maps to the set of distinct non-empty gsis_id values found for
    it. A set of size 1 is deterministic; size 0 or >1 fails closed downstream
    (unresolved or ambiguous, respectively) -- never guessed or curated.
    """
    rows, checksum = load_weekly_stats(path)
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
    if not include_lineage:
        return by_pfr
    is_remote = str(path).startswith(("http://", "https://"))
    source_recorded_at = urlopen(NFLVERSE_PLAYERS_RELEASE_TIMESTAMP_URL, timeout=30).read().decode("utf-8").strip() if is_remote else None
    lineage = {
        "source": str(path),
        "source_authority": "automated:nflverse" if is_remote else "UNVERIFIED",
        "artifact_id": "nflverse.players.csv",
        "version": source_recorded_at,
        "checksum": checksum,
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
        "schema_version": "nflverse-player-pfr-gsis-crosswalk.v1",
        "record_count": len(rows),
        "pfr_id_count": len(by_pfr),
        "ambiguous_pfr_id_count": sum(len(gsis_ids) > 1 for gsis_ids in by_pfr.values()),
    }
    return by_pfr, lineage


def build_snap_share_evidence(path: str | Path, *, season: int, retrieved_at: str | None = None, identity_crosswalk=None, identity_crosswalk_lineage=None, through_week: int | None = None, threshold_environment=None, now=None) -> dict:
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
    if not rows or not set(SNAP_COUNTS_REQUIRED_COLUMNS + ("offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps", "st_pct")).issubset(rows[0]):
        raise ValueError("SNAP_SHARE_SOURCE_SCHEMA_UNVERIFIED")
    selected = [row for row in rows if str(row.get("season")) == str(season)]
    if through_week is not None:
        selected = [row for row in selected if str(row.get("week") or "").isdigit() and int(row["week"]) <= through_week]
    retrieved = retrieved_at or datetime.now(timezone.utc).isoformat()
    evidence = normalize_snap_counts_batch(
        selected, season=season, source=source, source_recorded_at=source_recorded_at,
        retrieved_at=retrieved, checksum=checksum, version=f"snap_counts_{season}",
        identity_crosswalk=identity_crosswalk, threshold_environment=threshold_environment, now=now,
    )
    evidence["provenance"]["source_location"] = str(path)
    evidence["provenance"]["identity_crosswalk"] = dict(identity_crosswalk_lineage or {})
    evidence["provenance"]["source_artifact_record_count"] = len(rows)
    evidence["provenance"]["selected_row_count"] = len(selected)
    identity_reconciliation = evidence["reconciliation"]
    evidence["provenance"]["identity_crosswalk_completeness"] = "COMPLETE" if identity_reconciliation["unresolved_identity_count"] == 0 and identity_reconciliation["ambiguous_identity_count"] == 0 and identity_reconciliation["contradictory_identity_count"] == 0 else "PARTIAL"
    evidence["provenance"]["completeness_state"] = "COMPLETE" if evidence["reconciliation"]["resolved_row_count"] == evidence["reconciliation"]["normalized_row_count"] else "PARTIAL"
    return evidence


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--retrieved-at")
    parser.add_argument("--through-week", type=int)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if str(args.csv_path).startswith(("http://", "https://")):
        crosswalk, crosswalk_lineage = build_pfr_to_gsis_crosswalk(NFLVERSE_PLAYERS_RELEASE_URL, include_lineage=True)
    else:
        crosswalk, crosswalk_lineage = None, None
    evidence = build_snap_share_evidence(args.csv_path, season=args.season, retrieved_at=args.retrieved_at, identity_crosswalk=crosswalk, identity_crosswalk_lineage=crosswalk_lineage, through_week=args.through_week, threshold_environment=os.environ)
    if args.publish:
        import psycopg2
        with psycopg2.connect(host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT")), dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD")) as connection:
            publish_snap_share(connection, evidence)
    print(json.dumps(evidence, default=str, sort_keys=True))


if __name__ == "__main__":
    main()
