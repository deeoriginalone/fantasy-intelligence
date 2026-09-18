"""Atomic, correction-aware publication of calculated player-opportunity evidence."""
from __future__ import annotations

import json
from typing import Any, Mapping


def _publication_blocker(evidence: Mapping[str, Any]) -> str | None:
    """Return a blocker string, or None if the batch may publish."""
    provenance = evidence.get("provenance") or {}
    source = str(provenance.get("source") or "")
    if not source.startswith("automated:nflverse"):
        return "OPPORTUNITY_PUBLICATION_SOURCE_NOT_AUTOMATED"
    if not provenance.get("checksum"):
        return "OPPORTUNITY_PUBLICATION_CHECKSUM_UNAVAILABLE"
    if not provenance.get("retrieved_at"):
        return "OPPORTUNITY_PUBLICATION_RETRIEVED_AT_UNAVAILABLE"
    threshold = (evidence.get("publication_contracts") or {}).get("threshold") or {}
    if threshold.get("state") != "VERIFIED":
        return "OPPORTUNITY_PUBLICATION_THRESHOLD_UNVERIFIED"
    if evidence.get("freshness_state") not in {"FRESH", "AGING"}:
        return evidence.get("blocker") or "OPPORTUNITY_PUBLICATION_FRESHNESS_UNSUPPORTED"
    reconciliation = evidence.get("reconciliation") or {}
    if reconciliation.get("duplicate_player_week_count"):
        return "OPPORTUNITY_PUBLICATION_DUPLICATE_PLAYER_WEEK"
    if reconciliation.get("contradictory_player_week_count"):
        return "OPPORTUNITY_PUBLICATION_CONTRADICTORY_TEAM_IDENTITY"
    if not reconciliation.get("reconciled"):
        return "OPPORTUNITY_PUBLICATION_ACCOUNTING_UNRECONCILED"
    rows = evidence.get("rows") or []
    if not rows:
        return "OPPORTUNITY_PUBLICATION_NO_RESOLVED_ROWS"
    if not all(row.get("authoritative") for row in rows):
        return "OPPORTUNITY_PUBLICATION_ROW_NOT_AUTHORITATIVE"
    return None


def publish_player_opportunity(conn: Any, evidence: Mapping[str, Any]) -> int:
    """Publish only a fully-authoritative automated opportunity batch, atomically."""
    blocker = _publication_blocker(evidence)
    if blocker:
        raise ValueError(blocker)
    provenance = evidence.get("provenance") or {}
    source = provenance.get("source")
    source_authority = "automated" if str(source or "").startswith("automated:") else "UNVERIFIED"
    threshold_id = (evidence.get("publication_contracts") or {}).get("threshold", {}).get("identifier")
    artifact_id = f"stats_player_week_{evidence['season']}"
    cursor = conn.cursor()
    try:
        weeks = sorted({int(week) for week in (evidence.get("weeks") or [row["week"] for row in evidence["rows"]])})
        # Opportunity evidence is published per player-week; only the weeks in this
        # batch are replaced so refreshing one week never removes another week's rows.
        cursor.execute(
            "DELETE FROM player_opportunity_evidence WHERE season=%s AND week = ANY(%s) AND source LIKE 'automated:nflverse%%'",
            (evidence["season"], list(weeks)),
        )
        for row in evidence["rows"]:
            cursor.execute(
                """INSERT INTO player_opportunity_evidence(
                    season, week, player_id, team,
                    targets, carries, target_share, carry_share, touch_share,
                    snap_share, route_participation, red_zone_share, role_classification,
                    source, source_authority, source_recorded_at, retrieved_at,
                    artifact_id, version, checksum,
                    freshness_threshold_id, freshness_state, completeness_state,
                    lineage, publication_state
                ) VALUES (%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s::jsonb,%s)
                ON CONFLICT (season, week, player_id) DO UPDATE SET
                    team=EXCLUDED.team,
                    targets=EXCLUDED.targets, carries=EXCLUDED.carries,
                    target_share=EXCLUDED.target_share, carry_share=EXCLUDED.carry_share, touch_share=EXCLUDED.touch_share,
                    snap_share=EXCLUDED.snap_share, route_participation=EXCLUDED.route_participation,
                    red_zone_share=EXCLUDED.red_zone_share, role_classification=EXCLUDED.role_classification,
                    source=EXCLUDED.source, source_authority=EXCLUDED.source_authority,
                    source_recorded_at=EXCLUDED.source_recorded_at, retrieved_at=EXCLUDED.retrieved_at,
                    artifact_id=EXCLUDED.artifact_id, version=EXCLUDED.version, checksum=EXCLUDED.checksum,
                    freshness_threshold_id=EXCLUDED.freshness_threshold_id, freshness_state=EXCLUDED.freshness_state,
                    completeness_state=EXCLUDED.completeness_state, lineage=EXCLUDED.lineage, publication_state=EXCLUDED.publication_state""",
                (
                    row["season"], row["week"], row["player_id"], row.get("team"),
                    row.get("target_volume"), row.get("carry_volume"), row.get("target_share"), row.get("carry_share"), row.get("touch_share"),
                    row.get("snap_share"), row.get("route_participation"), row.get("red_zone_share"), row.get("role_classification"),
                    source, source_authority,
                    provenance.get("source_recorded_at"), provenance.get("retrieved_at"),
                    artifact_id, provenance.get("version"), provenance.get("checksum"),
                    threshold_id, row.get("freshness_state"), row.get("completeness_state"),
                    json.dumps(provenance), "PUBLISHED",
                ),
            )
        conn.commit()
        return len(evidence["rows"])
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
