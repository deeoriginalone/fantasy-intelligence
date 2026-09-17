"""Fail-closed player-role evidence contract: snap share, route participation, and red-zone usage.

No repository-verified automated source currently supplies these fields.
services/player_opportunity_calculation.py already documents that the only
ingested nflverse artifact (stats_player_week_{season}.csv.gz, via
imports/import_nflverse_weekly_stats.py) contains box-score counting stats
only -- it has no snap counts, route/participation data, or red-zone splits.
No other retrieval owner in this repository ingests such a dataset either.

This module therefore never estimates, derives, or defaults these metrics
from targets, carries, or touchdowns. It exists so a future verified source
can be wired in through one reusable, already-tested evidence shape without
inventing a second contract.
"""
from __future__ import annotations

from typing import Any, Mapping

ROLE_EVIDENCE_SCHEMA_VERSION = "player-role-evidence.v1"
DECISION_EFFECT = "INFORMATIONAL_ONLY"
SUPPORTED_METRICS = ("snap_share", "route_participation", "red_zone_share")

# One state per requested metric, decided only from repository/provider evidence
# actually inspected for this batch. None qualifies as SUPPORTED_AUTOMATED_SOURCE.
SOURCE_DECISIONS = {
    "snap_share": "SOURCE_UNAVAILABLE",
    "route_participation": "SOURCE_UNAVAILABLE",
    "red_zone_share": "SOURCE_UNAVAILABLE",
}

METRIC_DEFINITIONS = {
    "snap_share": {
        "name": "Snap Share",
        "purpose": "Share of a team's offensive snaps a player was on the field for.",
        "unit": "ratio 0-1",
        "numerator": "player offensive snap count",
        "denominator": "team offensive snap count",
        "eligible_population": "offensive skill positions (QB, RB, WR, TE) for a given team-week",
        "source_fields": "not yet verified in any ingested repository source",
        "freshness_requirement": "opportunity.evidence.v1 threshold, shared with target/carry/touch share",
        "missing_data_behavior": "UNAVAILABLE; never derived from targets or carries",
        "owner": "services.player_role_evidence",
        "validation_tests": "tests/test_player_role_evidence.py",
        "decision_effect": DECISION_EFFECT,
    },
    "route_participation": {
        "name": "Route Participation",
        "purpose": "Share of a team's passing plays a player ran a route on.",
        "unit": "ratio 0-1",
        "numerator": "player routes run",
        "denominator": "team passing plays",
        "eligible_population": "pass-catching positions (WR, TE, RB) for a given team-week",
        "source_fields": "not yet verified in any ingested repository source",
        "freshness_requirement": "opportunity.evidence.v1 threshold, shared with target/carry/touch share",
        "missing_data_behavior": "UNAVAILABLE; never derived from target volume",
        "owner": "services.player_role_evidence",
        "validation_tests": "tests/test_player_role_evidence.py",
        "decision_effect": DECISION_EFFECT,
    },
    "red_zone_share": {
        "name": "Red-Zone Usage",
        "purpose": "Share of a team's red-zone touches (targets plus carries inside the 20) attributable to a player.",
        "unit": "ratio 0-1",
        "numerator": "player red-zone touches",
        "denominator": "team red-zone touches",
        "eligible_population": "offensive skill positions (RB, WR, TE) for a given team-week",
        "source_fields": "not yet verified in any ingested repository source",
        "freshness_requirement": "opportunity.evidence.v1 threshold, shared with target/carry/touch share",
        "missing_data_behavior": "UNAVAILABLE; never derived from touchdowns",
        "owner": "services.player_role_evidence",
        "validation_tests": "tests/test_player_role_evidence.py",
        "decision_effect": DECISION_EFFECT,
    },
}

ROLE_CLASSIFICATION_BLOCKER = "ROLE_CLASSIFICATION_CONTRACT_UNVERIFIED"


def build_role_evidence(
    *,
    player_id: Any,
    season: Any,
    week: Any,
    source: str | None = None,
    source_authority: str | None = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    freshness_threshold_id: str | None = None,
    freshness_state: str = "UNAVAILABLE",
    values: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a metric only when it has a verified automated source; always fail closed otherwise.

    role_classification is never populated: no repository-backed classification
    contract (inputs, thresholds, minimum sample, historical baseline) exists.
    """
    values = dict(values or {})
    blockers: list[str] = []
    if player_id in (None, ""):
        blockers.append("OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE")
    if season in (None, ""):
        blockers.append("OPPORTUNITY_SEASON_UNAVAILABLE")
    if week in (None, ""):
        blockers.append("OPPORTUNITY_WEEK_UNAVAILABLE")
    if not retrieved_at:
        blockers.append("OPPORTUNITY_RETRIEVAL_TIME_UNAVAILABLE")
    if not freshness_threshold_id:
        blockers.append("OPPORTUNITY_FRESHNESS_THRESHOLD_UNVERIFIED")
    if freshness_state not in {"FRESH", "AGING"}:
        blockers.append("OPPORTUNITY_EVIDENCE_NOT_CURRENT")

    metrics: dict[str, dict[str, Any]] = {}
    for metric in SUPPORTED_METRICS:
        decision = SOURCE_DECISIONS[metric]
        if decision == "SUPPORTED_AUTOMATED_SOURCE":
            # Reserved for a future verified source; unreachable today because no
            # metric above is marked SUPPORTED_AUTOMATED_SOURCE.
            value = values.get(metric)
            metrics[metric] = {
                "value": value, "state": "AVAILABLE" if value is not None else "UNAVAILABLE",
                "blocker": None if value is not None else "OPPORTUNITY_METRIC_SOURCE_UNAVAILABLE",
            }
        else:
            metrics[metric] = {"value": None, "state": decision, "blocker": "OPPORTUNITY_METRIC_SOURCE_UNAVAILABLE"}

    all_blockers = list(dict.fromkeys([*blockers, ROLE_CLASSIFICATION_BLOCKER]))
    authoritative = not blockers and all(item["state"] == "AVAILABLE" for item in metrics.values())
    return {
        "player_id": player_id, "season": season, "week": week,
        "metrics": metrics,
        "role_classification": None,
        "role_classification_blocker": ROLE_CLASSIFICATION_BLOCKER,
        "source": source or "UNVERIFIED",
        "source_authority": source_authority or "UNVERIFIED",
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "freshness_threshold_id": freshness_threshold_id,
        "freshness_state": freshness_state,
        "completeness_state": "INCOMPLETE" if blockers else "COMPLETE",
        "blockers": all_blockers,
        "lineage": {"source": source, "player_id": player_id, "season": season, "week": week},
        "schema_version": ROLE_EVIDENCE_SCHEMA_VERSION,
        "decision_effect": DECISION_EFFECT,
        "authoritative": authoritative,
    }
