"""Pure current-season defense-versus-position calculation for full PPR."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from services.integrity.integrity_service import calculate_freshness, matchup_sample_threshold

POSITIONS = ("QB", "RB", "WR", "TE")
ALL_DEFENSES = 32
NOT_APPLICABLE_POSITIONS = {"K", "DEF", "DST"}
TEAM_ALIASES = {"LA": "LAR"}


def full_ppr_points(row: Mapping[str, Any]) -> float:
    number = lambda *names: sum(_float(row.get(name)) for name in names)
    return (number("passing_yards") * .04 + number("passing_tds") * 4 - number("interceptions", "passing_interceptions") * 2 + number("rushing_yards", "receiving_yards") * .1 + number("rushing_tds", "receiving_tds") * 6 + number("receptions") + number("two_point_conversions", "passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions") * 2 - number("fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost") * 2)


def calculate_defense_matchups(weekly_stats: Sequence[Mapping[str, Any]], *, season: int, sample_threshold: int | None = None, threshold_environment: Mapping[str, str] | None = None, source: str = "automated:nflverse", version: str | None = None, checksum: str | None = None, source_recorded_at: Any = None, retrieved_at: Any = None) -> dict[str, Any]:
    threshold = sample_threshold if sample_threshold is not None else matchup_sample_threshold(threshold_environment).get("completed_games")
    games: dict[tuple[str, str], set[Any]] = defaultdict(set)
    totals: dict[tuple[str, str], float] = defaultdict(float)
    unresolved: list[dict[str, Any]] = []
    for row in weekly_stats:
        position = str(row.get("position") or row.get("position_group") or "").upper().replace("DST", "DEF")
        if position in NOT_APPLICABLE_POSITIONS or position not in POSITIONS or not _completed(row):
            continue
        defense = TEAM_ALIASES.get(str(row.get("defense_team") or row.get("opponent_team") or row.get("defteam") or "").upper().strip(), str(row.get("defense_team") or row.get("opponent_team") or row.get("defteam") or "").upper().strip())
        game = row.get("game_id") or row.get("week")
        if not defense or game is None:
            unresolved.append({"row": dict(row), "reason": "INCOMPLETE_MATCHUP_IDENTITY"})
            continue
        if row.get("identity_resolved") is False:
            unresolved.append({"row": dict(row), "reason": row.get("identity_reason") or "UNRESOLVED_IDENTITY"})
            continue
        key = (position, defense)
        games[key].add(game)
        totals[key] += full_ppr_points(row)
    defenses_by_position = {position: {defense for pos, defense in games if pos == position} for position in POSITIONS}
    complete = all(len(defenses_by_position[position]) == ALL_DEFENSES for position in POSITIONS)
    rows = []
    for position in POSITIONS:
        values = [(defense, totals[(position, defense)] / len(games[(position, defense)])) for defense in defenses_by_position[position] if games[(position, defense)]]
        values.sort(key=lambda item: (item[1], item[0]))
        for rank, (defense, average) in enumerate(values, 1):
            rows.append({"season": season, "position": position, "defense_team": defense, "defense_rank": rank, "fp_per_game_allowed": round(average, 4), "completed_games": len(games[(position, defense)])})
    counts = [row["completed_games"] for row in rows]
    sufficient = threshold is not None and bool(counts) and min(counts) >= threshold
    freshness = calculate_freshness({"matchup_retrieved_at": retrieved_at, "matchup_source": source}, "matchup")
    if not rows:
        status, blocker = "UNAVAILABLE", "NO_COMPLETED_MATCHUP_EVIDENCE"
    elif not complete:
        status, blocker = "BLOCKED", "CURRENT_SEASON_DEFENSE_COMPLETENESS_REQUIRED"
    elif threshold is None:
        status, blocker = "BLOCKED", "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED"
    elif not sufficient:
        status, blocker = "INSUFFICIENT_SAMPLE", "MATCHUP_SAMPLE_BELOW_THRESHOLD"
    elif freshness["blocker"]:
        status, blocker = "BLOCKED", freshness["blocker"]
    else:
        status, blocker = "AUTHORITATIVE", None
    return {"season": season, "positions": list(POSITIONS), "rows": rows, "status": status, "authoritative": status == "AUTHORITATIVE", "directionality": "LOWER_IS_HARDER", "completeness": {"defense_count": max((len(value) for value in defenses_by_position.values()), default=0), "required_defenses": ALL_DEFENSES, "complete": complete}, "blocker": blocker, "unresolved_identities": unresolved, "freshness": freshness, "provenance": {"source": source, "version": version, "checksum": checksum, "source_recorded_at": source_recorded_at, "retrieved_at": retrieved_at, "attribution": "NFLverse data, licensed under CC BY 4.0."}}


def _completed(row: Mapping[str, Any]) -> bool:
    value = row.get("game_completed", row.get("completed"))
    if value is not None:
        return value is True or str(value).strip().lower() in {"1", "true", "yes", "completed"}
    if str(row.get("season_type") or "").lower() in {"reg", "regular", "regular_season"}:
        return True
    return str(row.get("game_status") or row.get("status") or "").lower() in {"final", "completed"}


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0