"""Read-only JerryGM projection retrieval for exact Sleeper player IDs (team defenses by their documented GSIS ID)."""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.integrity.integrity_service import calculate_freshness
from services.team_codes import jerrygm_defense_id


API_ROOT = "https://api.jerrygm.com/api/ext/v1"
MAX_FREE_IDS_PER_REQUEST = 25
SUPPORTED_ID_TYPES = {"sleeper": "EXACT_SLEEPER_ID", "gsis": "EXACT_GSIS_ID"}
BREAKDOWN_FIELDS = ("paTierExpectedPPG", "pointsAllowedSd")
SUPPORTED_SCORING = {"ppr", "half", "standard"}
SCORING_LABELS = {"ppr": "Full-PPR", "half": "Half-PPR", "standard": "Standard"}
PRESET_BY_RECEPTION_POINTS = {1.0: "ppr", 0.5: "half", 0.0: "standard"}
LIMITATIONS = [
    "Provider preset scoring; custom league weights are not applied.",
    "Informational-only projection; it does not change lineup selection or confidence.",
]


class JerryGMProjectionError(RuntimeError):
    """A provider request or response could not support projection evidence."""


def _utc_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _unavailable(player_id, blocker, *, retrieved_at=None):
    return {
        "state": "BLOCKED" if blocker.endswith("BLOCKED") else "UNAVAILABLE",
        "evidence_level": "INSUFFICIENT",
        "recommendation_impact": "INFORMATIONAL_ONLY",
        "sleeper_id": player_id,
        "projected_ppg": None,
        "unit": "fantasy_points_per_game",
        "source": "JerryGM",
        "source_record_time": None,
        "retrieved_at": retrieved_at,
        "freshness_state": "UNAVAILABLE",
        "completeness_state": "UNAVAILABLE",
        "blockers": [blocker],
        "attribution": None,
        "limitations": list(LIMITATIONS),
    }


def build_projection_edge(recommended, current):
    """Compare two provider projections only when every context field agrees."""
    unavailable = {
        "state": "UNAVAILABLE",
        "comparison_edge": None,
        "unit": "fantasy_points_per_game",
        "evidence_level": "INSUFFICIENT",
        "recommendation_impact": "INFORMATIONAL_ONLY",
    }
    if not isinstance(recommended, dict) or not isinstance(current, dict):
        return {**unavailable, "blocker": "JERRYGM_COMPARISON_EVIDENCE_MISSING"}
    if not recommended.get("sleeper_id") or not current.get("sleeper_id") or recommended.get("sleeper_id") == current.get("sleeper_id"):
        return {**unavailable, "blocker": "JERRYGM_COMPARISON_IDENTITY_UNAVAILABLE"}
    shared_fields = ("source", "scoring_format", "metric_name", "season", "week", "unit", "attribution")
    if any(not recommended.get(field) or recommended.get(field) != current.get(field) for field in shared_fields):
        return {**unavailable, "blocker": "JERRYGM_COMPARISON_CONTEXT_MISMATCH"}
    if recommended.get("source_record_time") != current.get("source_record_time") or recommended.get("retrieved_at") != current.get("retrieved_at"):
        return {**unavailable, "blocker": "JERRYGM_COMPARISON_TIMESTAMP_MISMATCH"}
    for player in (recommended, current):
        if player.get("freshness_state") not in {"FRESH", "AGING"}:
            return {**unavailable, "blocker": "JERRYGM_COMPARISON_FRESHNESS_UNAVAILABLE"}
        if player.get("state") != "AVAILABLE" or player.get("completeness_state") != "COMPLETE":
            return {**unavailable, "blocker": "JERRYGM_COMPARISON_EVIDENCE_INCOMPLETE"}
        if not player.get("source_record_time") or not player.get("retrieved_at"):
            return {**unavailable, "blocker": "JERRYGM_COMPARISON_TIMESTAMP_UNAVAILABLE"}
    recommended_value = _number(recommended.get("projected_ppg"))
    current_value = _number(current.get("projected_ppg"))
    if recommended_value is None or current_value is None:
        return {**unavailable, "blocker": "JERRYGM_COMPARISON_VALUE_UNAVAILABLE"}
    return {
        "state": "AVAILABLE",
        "comparison_edge": recommended_value - current_value,
        "unit": "fantasy_points_per_game",
        "evidence_level": "PRELIMINARY",
        "recommendation_impact": "INFORMATIONAL_ONLY",
        "source": recommended["source"],
        "scoring_format": recommended["scoring_format"],
        "season": recommended["season"],
        "week": recommended["week"],
        "attribution": recommended["attribution"],
        "limitations": list(LIMITATIONS),
    }


def provider_scoring_preset(reception_points):
    """Return the provider preset whose reception value matches the league, or None when none matches."""
    if reception_points is None or isinstance(reception_points, bool):
        return None
    try:
        return PRESET_BY_RECEPTION_POINTS.get(float(reception_points))
    except (TypeError, ValueError):
        return None


def _is_team_defense(player):
    return str((player or {}).get("position") or "").strip().upper() in {"DEF", "DST"}


def _team_defense_projections(defenses, *, client, season, week, scoring):
    """Team defenses are requested by JerryGM's documented ``DST-<team>`` GSIS ID and returned under their Sleeper ID."""
    projections = {}
    provider_ids = {}
    for sleeper_id, provider_id in defenses.items():
        if provider_id is None:
            projections[sleeper_id] = _unavailable(sleeper_id, "JERRYGM_DEFENSE_IDENTITY_UNAVAILABLE")
        else:
            provider_ids.setdefault(provider_id, []).append(sleeper_id)
    for provider_id, sleeper_ids in list(provider_ids.items()):
        if len(sleeper_ids) > 1:
            projections.update({sleeper_id: _unavailable(sleeper_id, "JERRYGM_ROSTER_IDENTITY_AMBIGUOUS") for sleeper_id in sleeper_ids})
            del provider_ids[provider_id]
    if not provider_ids:
        return projections
    if len(provider_ids) > MAX_FREE_IDS_PER_REQUEST:
        fetched = {provider_id: _unavailable(provider_id, "JERRYGM_FREE_ID_LIMIT_EXCEEDED") for provider_id in provider_ids}
    else:
        fetched = client.fetch(list(provider_ids), season=season, week=week, scoring=scoring, id_type="gsis")
    for provider_id, (sleeper_id,) in provider_ids.items():
        evidence = dict(fetched.get(provider_id) or _unavailable(provider_id, "JERRYGM_PLAYER_NOT_RETURNED"))
        evidence.update(sleeper_id=sleeper_id, provider_id=provider_id, identity_method="TEAM_DEFENSE_GSIS_ID")
        projections[sleeper_id] = evidence
    return projections


def build_roster_projections(players, *, season, week, scoring, client=None):
    """Fetch informational provider values for uniquely identified Sleeper IDs (one request per identity type)."""
    rows = list(players or [])
    ids = [str((player or {}).get("source_player_id") or "").strip() for player in rows]
    counts = Counter(player_id for player_id in ids if player_id)
    unique = {player_id: player for player_id, player in zip(ids, rows) if player_id and counts[player_id] == 1}
    defenses = {player_id: jerrygm_defense_id((player or {}).get("nfl_team") or player_id) for player_id, player in unique.items() if _is_team_defense(player)}
    requested = [player_id for player_id in unique if player_id not in defenses]
    base = {"source": "JerryGM", "scoring": scoring, "season": season, "week": week, "recommendation_impact": "INFORMATIONAL_ONLY"}
    if scoring not in SUPPORTED_SCORING:
        return {**base, "state": "UNAVAILABLE", "players": {}, "blockers": ["JERRYGM_PRESET_SCORING_REQUIRED"]}
    if season is None or week is None:
        return {**base, "state": "UNAVAILABLE", "players": {}, "blockers": ["JERRYGM_SEASON_WEEK_UNAVAILABLE"]}
    if not requested and not defenses:
        return {**base, "state": "UNAVAILABLE", "players": {}, "blockers": ["JERRYGM_ROSTER_IDENTITY_UNAVAILABLE"]}
    client = client or JerryGMProjectionClient()
    if len(requested) > MAX_FREE_IDS_PER_REQUEST:
        projections = {player_id: _unavailable(player_id, "JERRYGM_FREE_ID_LIMIT_EXCEEDED") for player_id in requested}
    else:
        projections = dict(client.fetch(requested, season=season, week=week, scoring=scoring)) if requested else {}
    if defenses:
        projections.update(_team_defense_projections(defenses, client=client, season=season, week=week, scoring=scoring))
    for player_id, count in counts.items():
        if count > 1:
            projections[player_id] = _unavailable(player_id, "JERRYGM_ROSTER_IDENTITY_AMBIGUOUS")
    available = any(row.get("projected_ppg") is not None for row in projections.values())
    return {
        **base,
        "state": "AVAILABLE" if available else "UNAVAILABLE",
        "players": projections,
        "blockers": sorted({blocker for row in projections.values() for blocker in row.get("blockers") or []}),
    }


def build_changed_slot_projections(roster, changes, *, season, week, client=None):
    """Fetch provider values only for uniquely identified Sleeper players in changed slots."""
    roster_ids = {}
    for player in roster or []:
        sleeper_id = str(player.get("source_player_id") or "").strip()
        if sleeper_id:
            roster_ids.setdefault(sleeper_id, []).append(player)

    slot_ids = {}
    slot_identity_blockers = {}
    requested = []
    for change in changes or []:
        slot = change.get("slot")
        slot_ids[slot] = {}
        slot_identity_blockers[slot] = {}
        for side, key in (("recommended", "recommended_id"), ("current", "current_id")):
            sleeper_id = str(change.get(key) or "").strip()
            if sleeper_id and len(roster_ids.get(sleeper_id, [])) == 1:
                slot_ids[slot][side] = sleeper_id
                slot_identity_blockers[slot][side] = None
                if sleeper_id not in requested:
                    requested.append(sleeper_id)
            else:
                slot_ids[slot][side] = None
                suffix = "IDENTITY_MISSING" if not sleeper_id else "IDENTITY_AMBIGUOUS"
                slot_identity_blockers[slot][side] = f"JERRYGM_{side.upper()}_{suffix}"

    client = client or JerryGMProjectionClient()
    if requested and len(requested) <= MAX_FREE_IDS_PER_REQUEST:
        projections = client.fetch(requested, season=season, week=week, scoring="ppr")
    elif requested:
        projections = {sleeper_id: _unavailable(sleeper_id, "JERRYGM_FREE_ID_LIMIT_EXCEEDED") for sleeper_id in requested}
    else:
        projections = {}

    result = {}
    for slot, sides in slot_ids.items():
        recommended_id = sides.get("recommended")
        current_id = sides.get("current")
        recommended = projections.get(recommended_id) if recommended_id else _unavailable(None, slot_identity_blockers[slot]["recommended"])
        current = projections.get(current_id) if current_id else _unavailable(None, slot_identity_blockers[slot]["current"])
        result[slot] = {
            "recommended": recommended,
            "current": current,
            "comparison": build_projection_edge(recommended, current),
        }
    return result


def build_projection_evidence(
    response,
    requested_sleeper_ids,
    *,
    season,
    week,
    scoring,
    retrieved_at,
    freshness_max_age_seconds=None,
    freshness_threshold_id=None,
    now=None,
    id_type="sleeper",
):
    """Validate one named-player response without name-based joins or scoring inference."""
    requested = [str(player_id).strip() for player_id in requested_sleeper_ids or []]
    if not requested or any(not player_id for player_id in requested):
        raise ValueError("JERRYGM_SLEEper_IDS_REQUIRED")
    if len(requested) > MAX_FREE_IDS_PER_REQUEST:
        raise ValueError("JERRYGM_FREE_ID_LIMIT_EXCEEDED")
    if len(set(requested)) != len(requested):
        raise ValueError("JERRYGM_DUPLICATE_REQUEST_ID")
    if scoring not in SUPPORTED_SCORING:
        raise ValueError("JERRYGM_PRESET_SCORING_REQUIRED")
    if id_type not in SUPPORTED_ID_TYPES:
        raise ValueError("JERRYGM_ID_TYPE_UNSUPPORTED")

    if not isinstance(response, dict):
        return {player_id: _unavailable(player_id, "JERRYGM_RESPONSE_INVALID", retrieved_at=retrieved_at) for player_id in requested}

    response_season = _number(response.get("season"))
    response_week = _number(response.get("week"))
    expected_season = _number(season)
    expected_week = _number(week)
    if response_season != expected_season or response_week != expected_week:
        blocker = "JERRYGM_SEASON_WEEK_MISMATCH"
        return {player_id: _unavailable(player_id, blocker, retrieved_at=retrieved_at) for player_id in requested}
    if response.get("scoring") != scoring:
        blocker = "JERRYGM_SCORING_MISMATCH"
        return {player_id: _unavailable(player_id, blocker, retrieved_at=retrieved_at) for player_id in requested}
    if response.get("source") != "jgm_baseline":
        blocker = "JERRYGM_SOURCE_UNSUPPORTED"
        return {player_id: _unavailable(player_id, blocker, retrieved_at=retrieved_at) for player_id in requested}
    if response.get("degraded"):
        blocker = "JERRYGM_SOURCE_DEGRADED"
        return {player_id: _unavailable(player_id, blocker, retrieved_at=retrieved_at) for player_id in requested}
    attribution = response.get("attribution")
    if not isinstance(attribution, str) or not attribution.strip():
        blocker = "JERRYGM_ATTRIBUTION_UNAVAILABLE"
        return {player_id: _unavailable(player_id, blocker, retrieved_at=retrieved_at) for player_id in requested}

    generated = _utc_datetime(response.get("generatedAt"))
    retrieved = _utc_datetime(retrieved_at)
    if generated is None or retrieved is None:
        blocker = "JERRYGM_TIMESTAMP_UNAVAILABLE"
        return {player_id: _unavailable(player_id, blocker, retrieved_at=retrieved_at) for player_id in requested}

    rows_by_id = {player_id: [] for player_id in requested}
    for row in response.get("players") or []:
        ids = row.get("ids") if isinstance(row, dict) else None
        provider_ids = {str((ids or {}).get(id_type) or "").strip()}
        if id_type == "gsis":
            provider_ids.add(str(row.get("gsisId") or "").strip())
        for provider_id in provider_ids & set(rows_by_id):
            rows_by_id[provider_id].append(row)

    source_stamp = generated.isoformat()
    freshness_limit = _number(freshness_max_age_seconds)
    threshold_id = str(freshness_threshold_id or "").strip()
    freshness = None
    if freshness_limit is not None and freshness_limit > 0 and threshold_id and threshold_id != "UNVERIFIED":
        freshness = calculate_freshness(
            {"projection_retrieved_at": source_stamp, "projection_source": "JerryGM"},
            "projection",
            now=now or retrieved,
            max_age_seconds=int(freshness_limit),
        )
    freshness_state = (
        "UNAVAILABLE" if freshness is None
        else "STALE" if freshness["status"] == "EXPIRED"
        else freshness["status"]
    )
    result = {}
    for player_id in requested:
        matches = rows_by_id[player_id]
        if not matches:
            result[player_id] = _unavailable(player_id, "JERRYGM_PLAYER_NOT_RETURNED", retrieved_at=retrieved.isoformat())
            continue
        if len(matches) != 1:
            result[player_id] = _unavailable(player_id, "JERRYGM_PLAYER_ID_AMBIGUOUS", retrieved_at=retrieved.isoformat())
            continue
        row = matches[0]
        value = _number(row.get("projectedPPG"))
        if value is None:
            result[player_id] = _unavailable(player_id, "JERRYGM_PROJECTION_INVALID", retrieved_at=retrieved.isoformat())
            continue
        state = "PRELIMINARY" if freshness_state == "UNAVAILABLE" else "STALE" if freshness_state == "STALE" else "AVAILABLE"
        result[player_id] = {
            "state": state,
            "evidence_level": "PRELIMINARY" if freshness_state == "UNAVAILABLE" else "HISTORICAL_CONTEXT_ONLY" if freshness_state == "STALE" else "PRELIMINARY",
            "recommendation_impact": "INFORMATIONAL_ONLY",
            "sleeper_id": player_id,
            "player_name": row.get("name"),
            "projected_ppg": value,
            "metric_name": f"Provider {SCORING_LABELS[scoring]} Projection",
            "unit": "fantasy_points_per_game",
            "source": "JerryGM jgm_baseline",
            "scoring_format": scoring,
            "season": int(response_season),
            "week": int(response_week),
            "data_through_week": response.get("dataThroughWeek"),
            "source_record_time": source_stamp,
            "retrieved_at": retrieved.isoformat(),
            "age_seconds": freshness.get("age_seconds") if freshness else max(0, int((retrieved - generated).total_seconds())),
            "freshness_state": freshness_state,
            "freshness_threshold_id": threshold_id if freshness else "UNVERIFIED",
            "freshness_max_age_seconds": int(freshness_limit) if freshness else None,
            "completeness_state": "INCOMPLETE" if freshness_state == "UNAVAILABLE" else "COMPLETE",
            "blockers": ["JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED"] if freshness_state == "UNAVAILABLE" else ["JERRYGM_STALE_HISTORICAL_ONLY"] if state == "STALE" else [],
            "attribution": attribution,
            "limitations": list(LIMITATIONS),
            **_provider_detail(row, response, player_id, id_type),
        }
    return result


def _provider_detail(row, response, provider_id, id_type):
    """Stat line, identity cross-check fields, and display-only provider availability for league rescoring."""
    ids = row.get("ids") if isinstance(row.get("ids"), dict) else {}
    breakdown = row.get("breakdown") if isinstance(row.get("breakdown"), dict) else {}
    coverage = response.get("statLineCoverage")
    return {
        "provider_id": provider_id,
        "identity_method": SUPPORTED_ID_TYPES[id_type],
        "gsis_id": row.get("gsisId") or ids.get("gsis"),
        "provider_position": row.get("position"),
        "provider_team": row.get("team"),
        "roster_status": row.get("rosterStatus"),
        "stat_line": dict(row["statLine"]) if isinstance(row.get("statLine"), dict) else None,
        "stat_line_coverage": dict(coverage) if isinstance(coverage, dict) else None,
        "breakdown": {key: breakdown[key] for key in BREAKDOWN_FIELDS if key in breakdown},
        "provider_availability": {
            "injury_status": row.get("injuryStatus"),
            "practice_status": row.get("practiceStatus"),
            "injury_note": row.get("injuryNote"),
            "p_play": _number(row.get("pPlay")),
            "expected_ppg": _number(row.get("expectedPPG")),
        },
    }


class JerryGMProjectionClient:
    def __init__(self, *, api_key=None, opener=urlopen, clock=None):
        self.api_key = api_key if api_key is not None else (os.getenv("JERRYGM_API_KEY") or os.getenv("JERRYGM_TOKEN", ""))
        self.opener = opener
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def fetch(self, sleeper_ids, *, season, week, scoring, freshness_max_age_seconds=None, freshness_threshold_id=None, id_type="sleeper"):
        requested = [str(player_id).strip() for player_id in sleeper_ids or []]
        if not self.api_key:
            return {player_id: _unavailable(player_id, "JERRYGM_CONFIGURATION_BLOCKED") for player_id in requested}
        if not requested or any(not player_id for player_id in requested):
            raise ValueError("JERRYGM_SLEEPER_IDS_REQUIRED")
        if len(requested) > MAX_FREE_IDS_PER_REQUEST:
            raise ValueError("JERRYGM_FREE_ID_LIMIT_EXCEEDED")
        if len(set(requested)) != len(requested):
            raise ValueError("JERRYGM_DUPLICATE_REQUEST_ID")
        if scoring not in SUPPORTED_SCORING:
            raise ValueError("JERRYGM_PRESET_SCORING_REQUIRED")
        if id_type not in SUPPORTED_ID_TYPES:
            raise ValueError("JERRYGM_ID_TYPE_UNSUPPORTED")

        query = urlencode({
            "season": season,
            "week": week,
            "scoring": scoring,
            "ids": ",".join(requested),
            "idType": id_type,
        })
        request = Request(
            f"{API_ROOT}/projections?{query}",
            headers={"X-API-Key": self.api_key, "Accept": "application/json"},
        )
        retrieved_at = self.clock().astimezone(timezone.utc).isoformat()
        try:
            with self.opener(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError:
            return {player_id: _unavailable(player_id, "JERRYGM_REFRESH_FAILED", retrieved_at=retrieved_at) for player_id in requested}
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {player_id: _unavailable(player_id, "JERRYGM_REFRESH_FAILED", retrieved_at=retrieved_at) for player_id in requested}
        return build_projection_evidence(
            payload,
            requested,
            season=season,
            week=week,
            scoring=scoring,
            retrieved_at=retrieved_at,
            freshness_max_age_seconds=freshness_max_age_seconds,
            freshness_threshold_id=freshness_threshold_id,
            now=self.clock(),
            id_type=id_type,
        )