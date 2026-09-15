"""Atomic, correction-aware publication of calculated matchup evidence."""
from __future__ import annotations

import json
from typing import Any, Mapping


def select_authoritative_matchups(current: Mapping[str, Any] | None, historical: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Use only fresh, authoritative current-season evidence; retain history as non-authoritative."""
    if current and current.get("authoritative") and not current.get("freshness", {}).get("blocker"):
        return dict(current)
    if historical:
        result = dict(historical)
        result["authoritative"] = False
        result["status"] = "HISTORICAL"
        result["blocker"] = "CURRENT_SEASON_AUTHORITY_UNAVAILABLE"
        return result
    return None


def publish_defense_matchups(conn: Any, evidence: Mapping[str, Any]) -> int:
    if not evidence.get("authoritative"):
        raise ValueError(evidence.get("blocker") or "MATCHUP_PUBLICATION_NOT_AUTHORIZED")
    provenance = evidence.get("provenance") or {}
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM defense_matchups WHERE season=%s AND source LIKE 'automated:nflverse%%'", (evidence["season"],))
        for row in evidence["rows"]:
            cursor.execute("""INSERT INTO defense_matchups(season,position,defense_team,defense_rank,fp_per_game_allowed,source,version,checksum,source_recorded_at,retrieved_at,completeness_state,blocker,lineage,attribution,completed_games)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'COMPLETE',NULL,%s::jsonb,%s,%s)
                ON CONFLICT(season,position,defense_team) DO UPDATE SET defense_rank=EXCLUDED.defense_rank,fp_per_game_allowed=EXCLUDED.fp_per_game_allowed,source=EXCLUDED.source,version=EXCLUDED.version,checksum=EXCLUDED.checksum,source_recorded_at=EXCLUDED.source_recorded_at,retrieved_at=EXCLUDED.retrieved_at,completeness_state=EXCLUDED.completeness_state,blocker=NULL,lineage=EXCLUDED.lineage,attribution=EXCLUDED.attribution,completed_games=EXCLUDED.completed_games""", (row["season"], row["position"], row["defense_team"], row["defense_rank"], row["fp_per_game_allowed"], provenance.get("source"), provenance.get("version"), provenance.get("checksum"), provenance.get("source_recorded_at"), provenance.get("retrieved_at"), json.dumps(provenance), provenance.get("attribution"), row.get("completed_games")))
        conn.commit()
        return len(evidence["rows"])
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()