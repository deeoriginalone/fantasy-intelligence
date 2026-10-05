"""Read-only JerryGM projection retrieval for exact Sleeper player IDs."""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.integrity.integrity_service import calculate_freshness


API_ROOT = "https://api.jerrygm.com/api/ext/v1"
MAX_FREE_IDS_PER_REQUEST = 25
SUPPORTED_SCORING = {"ppr", "half", "standard"}
SCORING_LABELS = {"ppr": "Full-PPR", "half": "Half-PPR", "standard": "Standard"}
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
        sleeper_id = str((ids or {}).get("sleeper") or "").strip()
        if sleeper_id in rows_by_id:
            rows_by_id[sleeper_id].append(row)

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
        }
    return result


class JerryGMProjectionClient:
    def __init__(self, *, api_key=None, opener=urlopen, clock=None):
        self.api_key = api_key if api_key is not None else (os.getenv("JERRYGM_API_KEY") or os.getenv("JERRYGM_TOKEN", ""))
        self.opener = opener
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def fetch(self, sleeper_ids, *, season, week, scoring, freshness_max_age_seconds=None, freshness_threshold_id=None):
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

        query = urlencode({
            "season": season,
            "week": week,
            "scoring": scoring,
            "ids": ",".join(requested),
            "idType": "sleeper",
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
        )