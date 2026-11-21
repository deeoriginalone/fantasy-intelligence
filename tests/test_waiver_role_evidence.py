"""W6: observed role and opportunity evidence (waiver.opportunity_trend.v1) - pure layer, batch readers and the explicit refresh."""
from __future__ import annotations

import inspect
import json
import math
import re
from datetime import datetime, timedelta, timezone

import pytest

import services.waiver_role_evidence as role_module
from services.waiver_role_evidence import (DIRECTION_RULE, DURATION_REASON, METRIC_DEFINITIONS, POSITION_METRICS, RECOMMENDATION_IMPACT, build_role_index,
                                           completed_week_boundary, role_coverage_summary, role_evidence)

NOW = datetime.now(timezone.utc)
RETRIEVED = NOW - timedelta(hours=1)
SCHEDULE_SOURCE = "automated:nflverse-schedules:games.csv.gz"
GAMES = (("KC", "DEN"), ("BUF", "MIA"))
OPPONENT = {"KC": "DEN", "DEN": "KC", "BUF": "MIA", "MIA": "BUF"}
BYES = [{"team": "KC", "bye_week": 3}, {"team": "DEN", "bye_week": 3}, {"team": "BUF", "bye_week": 9}, {"team": "MIA", "bye_week": 9}]
PROHIBITED = re.compile(r"opportunity score|role score|upside|usage grade|breakout|regression|buy low|sell high|league winner|sleeper pick|must add|"
                        r"\$\d|recommended bid|winning bid|maximum bid|probability|will continue|rest-of-season role|secure|next week|projected|"
                        r"caused|because of|surge|significant|big increase", re.I)


def schedule(*, completed=4, current=5, final_current=("KC",), source=SCHEDULE_SOURCE):
    """Weeks 1..current; KC and DEN are on bye in Week 3; in the current week only the listed home teams' games are final."""
    rows = []
    for week in range(1, current + 1):
        for home, away in GAMES:
            if week == 3 and home == "KC":
                continue
            final = week <= completed or (week == current and home in final_current)
            rows.append({"week": week, "home_team": home, "away_team": away, "game_time_utc": NOW - timedelta(days=7 * (current - week)),
                         "result": "3" if final else None, "source": source, "source_recorded_at": RETRIEVED, "retrieved_at": RETRIEVED})
    return rows


def coverage(*, through=4, skip=(), freshness="FRESH", retrieved=RETRIEVED):
    return [{"week": row["week"], "team": team, "rows": 4, "retrieved_at": retrieved, "source_recorded_at": retrieved, "freshness_state": freshness}
            for row in schedule() if row["week"] <= through for team in (row["home_team"], row["away_team"]) if (row["week"], team) not in skip]


def stats(player, week, team, *, targets=None, carries=None, points=5.0, freshness="FRESH", **extra):
    return {"season": 2026, "week": week, "player_id": player, "team": team, "position": "WR", "opponent_team": OPPONENT[team], "targets": targets,
            "carries": carries, "fantasy_points_ppr": points, "scoring_format": "FULL_PPR", "freshness_state": freshness, "retrieved_at": RETRIEVED,
            "provenance_blockers": [], **extra}


def snap(player, week, team, share, *, snaps=None, domain="OFFENSE", freshness="FRESH", **extra):
    return {"season": 2026, "week": week, "player_id": player, "team": team, "opponent_team": OPPONENT[team], "snap_share": share,
            "participation_domain": domain, "source_snap_count": None if snaps is None else str(snaps), "freshness_state": freshness,
            "retrieved_at": RETRIEVED, "provenance_blockers": [], **extra}


def reads(stats_rows=(), snap_rows=(), *, opp_coverage=None, snap_coverage=None, schedule_rows=None, threshold=86400):
    return {"opportunity": {"state": "READ", "rows": list(stats_rows), "coverage": coverage() if opp_coverage is None else opp_coverage,
                            "threshold": {"id": "opportunity.evidence.v1", "seconds": threshold}},
            "snaps": {"state": "READ", "rows": list(snap_rows), "coverage": coverage() if snap_coverage is None else snap_coverage,
                      "threshold": {"id": "snap_share.evidence.v1", "seconds": threshold}},
            "schedule": schedule() if schedule_rows is None else schedule_rows}


def index(data, *, week=5, verified=True, mode="LIVE"):
    return build_role_index(season=2026, week=week, week_verified=verified, reads=data, bye_rows=BYES, mode=mode)


def evidence(data_or_index, player="g-1", *, position="WR", team="BUF", identity="RESOLVED", method="gsis_id"):
    idx = data_or_index if "players" in data_or_index else index(data_or_index)
    return role_evidence(idx, player_id="s-1", opportunity_player_id=player, identity_state=identity, identity_method=method, position=position, team=team,
                         player="Test Player")


def wr_weeks(values, *, team="BUF", player="g-1", snaps_too=True):
    """values: {week: (snap_share, targets)}; None leaves that source's row absent."""
    stat_rows, snap_rows = [], []
    for week, (share, targets) in values.items():
        if targets is not None:
            stat_rows.append(stats(player, week, team, targets=targets, carries=0))
        if share is not None and snaps_too:
            snap_rows.append(snap(player, week, team, share))
    return reads(stat_rows, snap_rows)


def all_text(value):
    if isinstance(value, dict):
        return " ".join(all_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(all_text(item) for item in value)
    return str(value) if isinstance(value, str) else ""


# Source, completed games and pipeline currency.

def test_current_completed_games_give_a_current_role_with_exact_weeks_and_values():
    result = evidence(wr_weeks({1: (0.30, 1), 2: (0.44, 3), 3: (0.61, 6), 4: (0.76, 9)}))
    assert (result["state"], result["direction"], result["sample_state"], result["sample_size"], result["weeks"]) == (
        "CURRENT", "DIRECTION_UP", "MULTI_GAME_HISTORY", 3, [2, 3, 4])
    assert result["metrics"]["snap_share"]["display"] == "44% → 61% → 76%" and result["metrics"]["targets"]["display"] == "3 → 6 → 9"
    assert result["text"]["role"] == ("DIRECTION UP — snap share 44% → 61% → 76% (up); targets 3 → 6 → 9 (up) (Weeks 2, 3, 4; 3 supported completed "
                                      "games).")
    assert (result["through_week"], result["completed_through_week"], result["recommendation_impact"], result["decision_effect"]) == (4, 4, RECOMMENDATION_IMPACT, "NONE")


def test_rows_from_another_season_or_a_future_week_are_rejected_not_used():
    data = wr_weeks({2: (0.40, 2), 3: (0.50, 4), 4: (0.60, 6)})
    data["opportunity"]["rows"] += [stats("g-1", 6, "BUF", targets=20, carries=0), {**stats("g-1", 1, "BUF", targets=20, carries=0), "season": 2025}]
    idx = index(data)
    result = evidence(idx)
    assert idx["rejected_rows"] == {"stats:future_week": 1, "stats:season_or_week_invalid": 1}
    assert result["weeks"] == [2, 3, 4] and result["metrics"]["targets"]["display"] == "2 → 4 → 6"


def test_a_game_that_is_not_final_is_excluded_and_a_final_current_week_game_counts():
    data = wr_weeks({2: (0.40, 2), 3: (0.50, 4), 4: (0.60, 6), 5: (0.10, 0)})
    result = evidence(data)  # BUF's Week 5 game has no published result
    assert result["weeks"] == [2, 3, 4] and "Week 5: stored, but the game result is not verified as final, so it is not counted." in result["notes"]
    kc = wr_weeks({2: (0.40, 2), 4: (0.60, 6), 5: (0.70, 7)}, team="KC")
    kc_result = evidence(kc, team="KC")  # KC's Week 5 game is final
    assert kc_result["weeks"] == [2, 4, 5] and kc_result["direction"] == "DIRECTION_UP"


def test_a_bye_is_excluded_and_never_becomes_a_zero_or_a_decline():
    result = evidence(wr_weeks({1: (0.50, 5), 2: (0.55, 6), 4: (0.60, 7)}, team="KC"), team="KC")
    assert result["weeks"] == [1, 2, 4] and result["direction"] == "DIRECTION_UP"
    assert {"week": 3, "state": "BYE"} in result["gaps"] and "Week 3: bye, not counted." in result["text"]["role"]
    assert result["metrics"]["snap_share"]["values"] == [(1, 0.50), (2, 0.55), (4, 0.60)] and result["metrics"]["targets"]["values"] == [(1, 5), (2, 6), (4, 7)]
    assert result["metrics"]["snap_share"]["display"] == "50% → 55% → 60%" and result["metrics"]["targets"]["display"] == "5 → 6 → 7"


def test_verified_through_week_requires_every_completed_game_to_be_stored():
    data = wr_weeks({1: (0.30, 1), 2: (0.44, 3), 3: (0.61, 6), 4: (0.76, 9)})
    data["opportunity"]["coverage"] = coverage(skip={(3, "MIA")})
    idx = index(data)
    source = idx["sources"]["stats_player_week"]
    assert (source["verified_through_week"], source["completeness"], source["currency"]) == (2, "PARTIAL", "NOT_CURRENT")
    assert source["reason"] == "Stored through Week 2; completed Weeks 3–4 are not stored."
    result = evidence(idx)
    # Snap share is still current; targets are not used and the reason is disclosed.
    assert result["state"] == "CURRENT" and result["metric_order"] == ["snap_share"] and "targets" not in result["metrics"]
    assert any(note.startswith("Targets not used: nflverse stats_player_week") for note in result["notes"])


def test_an_incomplete_or_stale_pipeline_never_claims_a_current_role_and_history_stays_history():
    data = wr_weeks({1: (0.30, 1), 2: (0.44, 3), 3: (0.61, 6), 4: (0.76, 9)})
    data["opportunity"]["coverage"] = coverage(through=2)
    data["snaps"]["coverage"] = coverage(freshness="STALE", retrieved=NOW - timedelta(days=3))
    result = evidence(data)
    assert (result["state"], result["direction"], result["persistence"]["state"], result["future_duration"]["state"]) == (
        "HISTORICAL_ONLY", "INSUFFICIENT_EVIDENCE", "DURATION_UNVERIFIED", "UNVERIFIED")
    assert result["weeks"] == [2, 3, 4] and [item["week"] for item in result["observations"]] == [2, 3, 4]
    assert result["text"]["role"].startswith("HISTORICAL ONLY — Stored role evidence for this player ends at Week 4 and the stored sources are not verified as current")
    assert "older than the 24-hour snap_share.evidence.v1 limit" in result["text"]["role"] and "python refresh_opportunity_evidence.py" in result["text"]["role"]
    assert "DIRECTION UP" not in result["text"]["role"]


def test_source_lineage_identity_method_and_attribution_are_kept():
    result = evidence(wr_weeks({3: (0.50, 4), 4: (0.60, 6)}), method="dynastyprocess_gsis_id")
    assert result["identity_method"] == "dynastyprocess_gsis_id" and result["attribution"] == "nflverse data (CC BY 4.0)"
    assert [(source["source"], source["threshold_id"], source["currency"]) for source in result["sources"]] == [
        ("snap_counts", "snap_share.evidence.v1", "CURRENT"), ("stats_player_week", "opportunity.evidence.v1", "CURRENT")]
    assert result["observations"][0]["retrieved_at"] == RETRIEVED


def test_unverified_week_unread_evidence_missing_threshold_and_sandbox_never_produce_role_evidence():
    data = wr_weeks({3: (0.50, 4), 4: (0.60, 6)})
    assert evidence(index(data, verified=False))["state"] == "BLOCKED"
    assert evidence(index({"state": "READ_FAILED"}))["state"] == "BLOCKED"
    assert evidence(index(data, mode="SANDBOX"))["state"] == "NOT_APPLICABLE" and index(data, mode="SANDBOX")["state"] == "NOT_APPLICABLE"
    unverified = index(reads(data["opportunity"]["rows"], data["snaps"]["rows"], threshold=None))
    blocked = evidence(unverified)
    assert {source["currency"] for source in unverified["sources"].values()} == {"BLOCKED"} and (blocked["state"], blocked["observations"]) == ("BLOCKED", [])
    assert "freshness limit is not configured" in blocked["text"]["role"] and "SNAP_COUNTS_FRESHNESS_THRESHOLD_UNVERIFIED" in blocked["blockers"]


def test_completed_week_boundary_is_contiguous_and_automated_only():
    assert completed_week_boundary(schedule()) == 4 and completed_week_boundary(schedule(), through_week=2) == 2
    assert completed_week_boundary(schedule(completed=2)) == 2
    assert completed_week_boundary(schedule(source="csv:nfl-2026-UTC.csv")) == 0 and completed_week_boundary([]) == 0


# Identity.

def test_identity_must_be_an_exact_resolved_gsis_id_and_names_never_join():
    data = wr_weeks({3: (0.50, 4), 4: (0.60, 6)}, player="g-1")
    assert evidence(data, player="g-1")["state"] == "CURRENT"
    unresolved = evidence(data, player=None, identity="UNRESOLVED")
    assert (unresolved["state"], unresolved["observations"], unresolved["label"]) == ("IDENTITY_UNRESOLVED", [], "UNAVAILABLE")
    # Rows stored under a different exact ID (or a name) are never consumed, even for a similarly named player.
    assert evidence(data, player="Test Player")["state"] == "NO_EVIDENCE" and evidence(data, player="g-2")["state"] == "NO_EVIDENCE"
    for state in ("AMBIGUOUS", "CONTRADICTORY", "CONFLICTING"):
        assert evidence(data, identity=state)["state"] == "CONTRADICTORY"
    # The ranking-only name/position/team exception is not an opportunity identity.
    ranking_only = evidence(data, player=None, identity=None, method="OWNER_APPROVED_UNIQUE_NAME_POSITION_TEAM")
    assert ranking_only["state"] == "IDENTITY_UNRESOLVED"
    assert "OWNER_APPROVED" not in inspect.getsource(role_module) and "normalize_player_name" not in inspect.getsource(role_module)


def test_a_team_conflict_between_sources_is_contradictory_and_never_remapped():
    data = reads([stats("g-1", 3, "BUF", targets=4, carries=0), stats("g-1", 4, "BUF", targets=6, carries=0)],
                 [snap("g-1", 3, "BUF", 0.5), snap("g-1", 4, "MIA", 0.6)])
    result = evidence(data)
    assert (result["state"], result["direction"], result["persistence"]["state"]) == ("CONTRADICTORY", "CONTRADICTORY", "CONTRADICTORY")
    assert "OBSERVATION_TEAM_CONFLICT" in result["blockers"] and result["observations"] == []


def test_kickers_and_defenses_are_not_applicable_even_when_rows_exist():
    data = wr_weeks({3: (0.50, 4), 4: (0.60, 6)})
    for position, reason in (("K", "No individual offensive-role contract exists for kickers."), ("DEF", "Team defenses have no individual offensive-role evidence."),
                             ("DST", "Team defenses have no individual offensive-role evidence.")):
        result = evidence(data, position=position)
        assert (result["state"], result["direction"], result["persistence"]["state"], result["future_duration"]["state"]) == (
            "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE")
        assert result["text"]["role"] == f"NOT APPLICABLE — {reason}" and result["observations"] == []


# Metric validity.

def test_a_verified_zero_stays_zero_and_a_missing_value_is_never_zero():
    data = reads([stats("g-1", 2, "BUF", targets=0, carries=0), stats("g-1", 4, "BUF", targets=3, carries=0)],
                 [snap("g-1", 2, "BUF", 0.0, snaps=0), snap("g-1", 3, "BUF", 0.35, snaps=20), snap("g-1", 4, "BUF", 0.5, snaps=31)])
    result = evidence(data)
    assert result["weeks"] == [2, 3, 4]
    assert result["metrics"]["snap_share"]["display"] == "0% → 35% → 50%" and result["metrics"]["targets"]["display"] == "0 → n/a → 3"
    assert result["metrics"]["targets"]["values"] == [(2, 0), (4, 3)]
    assert result["observations"][1]["text"] == "35% snaps (20 offensive snaps) · targets n/a"


@pytest.mark.parametrize("field,value", [("targets", math.nan), ("targets", math.inf), ("targets", -1), ("targets", 2.5), ("targets", "3"), ("targets", True),
                                         ("snap_share", -0.01), ("snap_share", 1.01), ("snap_share", math.nan), ("snap_share", "0.5")])
def test_invalid_values_are_rejected_and_never_become_zero(field, value):
    stat_rows = [stats("g-1", 3, "BUF", targets=4, carries=0), stats("g-1", 4, "BUF", targets=value if field == "targets" else 6, carries=0)]
    snap_rows = [snap("g-1", 3, "BUF", 0.5), snap("g-1", 4, "BUF", value if field == "snap_share" else 0.6)]
    result = evidence(reads(stat_rows, snap_rows))
    observation = index(reads(stat_rows, snap_rows))["players"]["g-1"][1]
    assert observation["metrics"][field]["state"] == "INVALID" and observation["metrics"][field]["value"] is None
    assert result["metrics"][field]["values"] == [(3, 0.5 if field == "snap_share" else 4)]
    assert result["metrics"][field]["display"].endswith("→ n/a")


def test_snap_share_is_the_stored_0_1_ratio_and_only_offensive_participation_counts():
    result = evidence(reads([], [snap("g-1", 3, "BUF", 0.76), snap("g-1", 4, "BUF", 0.765)]))
    assert result["metrics"]["snap_share"]["display"] == "76.0% → 76.5%" and result["metrics"]["snap_share"]["values"] == [(3, 0.76), (4, 0.765)]
    defense = index(reads([], [snap("g-1", 4, "BUF", 0.8, domain="DEFENSE")]))["players"]["g-1"][0]["metrics"]["snap_share"]
    assert (defense["state"], defense["reason"], defense["value"]) == ("INVALID", "SNAP_SHARE_NOT_OFFENSIVE", None)
    blocked = index(reads([], [snap("g-1", 4, "BUF", 0.8, provenance_blockers=["SNAP_SHARE_SOURCE_UNSUPPORTED"])]))["players"]["g-1"][0]["metrics"]["snap_share"]
    assert (blocked["state"], blocked["usable"]) == ("BLOCKED", False)


def test_exact_duplicates_collapse_and_conflicting_duplicates_are_contradictory():
    row = stats("g-1", 4, "BUF", targets=6, carries=0)
    same = evidence(reads([stats("g-1", 3, "BUF", targets=4, carries=0), row, dict(row)], [snap("g-1", 3, "BUF", 0.5), snap("g-1", 4, "BUF", 0.6)]))
    assert same["state"] == "CURRENT" and same["metrics"]["targets"]["display"] == "4 → 6"
    conflict = evidence(reads([stats("g-1", 3, "BUF", targets=4, carries=0), row, {**row, "targets": 9}], [snap("g-1", 3, "BUF", 0.5), snap("g-1", 4, "BUF", 0.6)]))
    assert conflict["state"] == "CONTRADICTORY" and "OPPORTUNITY_DUPLICATE_CONFLICT" in conflict["blockers"]


# Observation and sample states.

def test_a_missing_row_is_unknown_not_a_dnp_an_inactive_or_a_bye():
    result = evidence(wr_weeks({1: (0.40, 3), 2: (0.45, 4), 4: (0.50, 5)}))  # BUF played in Week 3
    assert {"week": 3, "state": "MISSING_SOURCE_ROW"} in result["gaps"]
    assert ("Week 3: no stored snap or stats row (did not play, inactive or not recorded; the source does not say which), not counted as zero."
            in result["text"]["role"])
    assert not re.search(r"\bDNP\b|inactive in Week|was inactive", result["text"]["role"])


@pytest.mark.parametrize("weeks,sample_state,direction", [({4: (0.5, 4)}, "CURRENT_ROLE_ONLY", "CURRENT_ROLE_ONLY"),
                                                           ({3: (0.4, 3), 4: (0.5, 4)}, "LIMITED_HISTORY", "DIRECTION_UP"),
                                                           ({1: (0.1, 1), 2: (0.2, 2), 3: (0.4, 3), 4: (0.5, 4)}, "MULTI_GAME_HISTORY", "DIRECTION_UP")])
def test_sample_states_follow_the_number_of_supported_completed_games(weeks, sample_state, direction):
    result = evidence(wr_weeks(weeks))
    assert (result["sample_state"], result["direction"], result["weeks"]) == (sample_state, direction, sorted(weeks)[-3:])
    if direction == "CURRENT_ROLE_ONLY":
        assert result["text"]["role"] == "CURRENT ROLE ONLY — snap share 50%; targets 4 (Week 4; one supported completed game, so no trend is shown)."


def test_a_player_absent_from_his_teams_latest_completed_games_is_historical_only():
    data = reads([stats("g-1", 1, "BUF", targets=5, carries=0)], [snap("g-1", 1, "BUF", 0.6)])
    result = evidence(data)
    assert (result["state"], result["direction"]) == ("HISTORICAL_ONLY", "INSUFFICIENT_EVIDENCE")
    assert result["text"]["role"].startswith("HISTORICAL ONLY — No supported snap or usage row for this player after Week 1: Weeks 2–4: no stored snap or stats row")
    two_missed = evidence(reads([stats("g-1", 1, "BUF", targets=5, carries=0), stats("g-1", 2, "BUF", targets=6, carries=0)],
                                [snap("g-1", 1, "BUF", 0.6), snap("g-1", 2, "BUF", 0.7)]))
    assert two_missed["state"] == "CURRENT" and "Weeks 3–4: no stored snap or stats row" in two_missed["text"]["role"]


def test_no_supported_row_is_no_evidence_and_does_not_mean_a_poor_player():
    result = evidence(reads([], []))
    assert (result["state"], result["sample_state"], result["observations"]) == ("NO_EVIDENCE", "NO_EVIDENCE", [])
    assert "Missing role evidence does not mean a poor player." in result["text"]["role"]


# Direction.

@pytest.mark.parametrize("snaps,targets,direction", [((0.44, 0.61, 0.76), (3, 6, 9), "DIRECTION_UP"), ((0.80, 0.70, 0.31), (7, 6, 2), "DIRECTION_DOWN"),
                                                      ((0.52, 0.60, 0.68), (6, 4, 3), "MIXED"), ((1.0, 1.0, 1.0), (2, 2, 2), "FLAT"),
                                                      ((0.44, 0.45, 0.46), (2, 2, 2), "DIRECTION_UP"), ((0.50, 0.60, 0.55), (2, 2, 2), "MIXED")])
def test_direction_is_the_sign_of_change_across_supported_games(snaps, targets, direction):
    result = evidence(wr_weeks({2: (snaps[0], targets[0]), 3: (snaps[1], targets[1]), 4: (snaps[2], targets[2])}))
    assert result["direction"] == direction and result["label"] == direction.replace("DIRECTION_", "DIRECTION ").replace("_", " ")
    assert not PROHIBITED.search(all_text(result))


def test_a_tiny_increase_is_only_a_direction_never_a_significant_change():
    result = evidence(wr_weeks({2: (0.44, 2), 3: (0.45, 2), 4: (0.46, 2)}))
    assert result["direction"] == "DIRECTION_UP" and result["metrics"]["snap_share"]["display"] == "44% → 45% → 46%"
    assert DIRECTION_RULE in role_coverage_summary(index(wr_weeks({4: (0.5, 2)})), [result])["direction_rule"]
    assert "not its size" in DIRECTION_RULE and not PROHIBITED.search(all_text(result))
    assert not hasattr(role_module, "MATERIALITY_THRESHOLD") and "0.05" not in inspect.getsource(role_module)


def test_the_window_is_the_latest_three_supported_games_and_gaps_are_shown():
    result = evidence(wr_weeks({1: (0.9, 9), 2: (0.40, 2)} | {4: (0.50, 4)}))
    assert result["weeks"] == [1, 2, 4] and result["metrics"]["snap_share"]["display"] == "90% → 40% → 50%"
    later = evidence(wr_weeks({1: (0.9, 9), 2: (0.40, 2), 3: (0.45, 3), 4: (0.50, 4)}))
    assert later["weeks"] == [2, 3, 4] and later["direction"] == "DIRECTION_UP"


# Positions.

def test_position_metric_sets_and_unavailable_metrics():
    assert POSITION_METRICS == {"QB": ("snap_share", "carries"), "RB": ("snap_share", "carries", "targets"), "WR": ("snap_share", "targets"),
                                "TE": ("snap_share", "targets")}
    rows = [stats("g-1", week, "BUF", targets=week, carries=10 + week) for week in (2, 3, 4)]
    snap_rows = [snap("g-1", week, "BUF", 0.5 + week / 100) for week in (2, 3, 4)]
    for position, shown in (("QB", ["snap_share", "carries"]), ("RB", ["snap_share", "carries", "targets"]), ("WR", ["snap_share", "targets"]),
                            ("TE", ["snap_share", "targets"])):
        result = evidence(reads(rows, snap_rows), position=position)
        assert result["metric_order"] == shown and list(result["metrics"]) == shown
    wr = evidence(reads(rows, snap_rows), position="WR")
    assert any(item.startswith("routes and route participation") for item in wr["unavailable_metrics"])
    assert any(item.startswith("target share (the stored share divides") for item in wr["unavailable_metrics"])
    assert "target_share" not in wr["metrics"] and "route_participation" not in wr["metrics"]
    rb = evidence(reads(rows, snap_rows), position="RB")
    assert any(item.startswith("rush share") for item in rb["unavailable_metrics"]) and any(item.startswith("red-zone") for item in rb["unavailable_metrics"])
    assert evidence(reads(rows, snap_rows), position="QB")["unavailable_metrics"] == [
        "pass attempts and dropbacks (pass attempts are in the source artifact but not stored)"]


def test_role_evidence_is_intra_player_with_no_cross_position_rank_or_score():
    results = [evidence(wr_weeks({3: (0.5, 4), 4: (0.6, 6)}), position=position) for position in ("WR", "TE", "RB")]
    for result in results:
        assert not {key for key in result if re.search(r"rank|score|order_value|weight", key)} - {"metric_order"}
    summary = role_coverage_summary(index(wr_weeks({4: (0.5, 2)})), results)
    assert not {key for key in summary if re.search(r"rank|score", key)}
    assert set(METRIC_DEFINITIONS) == {"snap_share", "targets", "carries"}
    for definition in METRIC_DEFINITIONS.values():
        assert {"name", "purpose", "unit", "source", "valid_range", "directionality", "freshness", "missing", "decision_use", "owner", "tests"} <= set(definition)
        assert definition["decision_use"] == "INFORMATIONAL_ONLY"


# Persistence and future duration.

@pytest.mark.parametrize("values,state,reason", [
    ({2: (0.44, 3), 3: (0.61, 6), 4: (0.76, 9)}, "PERSISTED_ACROSS_OBSERVED_GAMES",
     "Higher snap share and targets held in each of the last 2 of 3 supported completed games (Weeks 3, 4 above Week 2). This looks back only."),
    ({2: (0.44, 3), 3: (0.44, 3), 4: (0.76, 9)}, "DURATION_UNVERIFIED",
     "The larger role has not been observed to hold: snap share rose only in the latest game; targets rose only in the latest game."),
    ({3: (0.44, 3), 4: (0.76, 9)}, "DURATION_UNVERIFIED",
     "The change appears across only 2 supported completed games (one change), so it has not been observed to hold."),
    ({4: (0.76, 9)}, "DURATION_UNVERIFIED", "Only one supported completed game is available."),
    ({2: (0.80, 7), 3: (0.70, 6), 4: (0.31, 2)}, "PERSISTED_ACROSS_OBSERVED_GAMES",
     "Lower snap share and targets held in each of the last 2 of 3 supported completed games (Weeks 3, 4 below Week 2). This looks back only."),
    ({2: (1.0, 2), 3: (1.0, 2), 4: (1.0, 2)}, "PERSISTED_ACROSS_OBSERVED_GAMES", "The observed role level held across 3 supported completed games. This looks back only."),
    ({2: (0.52, 6), 3: (0.60, 4), 4: (0.68, 3)}, "DURATION_UNVERIFIED",
     "The supported metrics moved in different directions, so no single role change has been observed to hold."),
])
def test_observed_persistence_requires_the_change_to_hold_and_never_becomes_future_duration(values, state, reason):
    result = evidence(wr_weeks(values))
    assert (result["persistence"]["state"], result["persistence"]["reason"]) == (state, reason)
    assert result["future_duration"] == {"state": "UNVERIFIED", "label": "UNVERIFIED", "reason": DURATION_REASON}
    assert result["text"]["duration"] == f"UNVERIFIED — {DURATION_REASON}"
    assert not PROHIBITED.search(result["text"]["persistence"] + result["text"]["duration"])


def test_teammate_absence_is_never_asserted_and_temporary_role_risk_is_never_produced():
    teammate = reads([stats("g-1", week, "BUF", targets=t, carries=0) for week, t in ((2, 2), (3, 8), (4, 9))] + [stats("g-2", 2, "BUF", targets=10, carries=0)],
                     [snap("g-1", week, "BUF", s) for week, s in ((2, 0.3), (3, 0.8), (4, 0.85))] + [snap("g-2", 2, "BUF", 0.9)])
    result = evidence(teammate)
    assert result["persistence"]["state"] == "PERSISTED_ACROSS_OBSERVED_GAMES"
    text = all_text(result)
    assert "TEMPORARY_ROLE_RISK" not in text and not re.search(r"teammate|absence|absent|returns?\b|return date|injur", text, re.I)
    assert "TEMPORARY_ROLE_RISK" not in inspect.getsource(role_evidence) and not re.search(r"\b20\d\d-\d\d-\d\d\b", result["text"]["duration"])


def test_unverified_future_duration_never_hides_the_observed_role():
    result = evidence(wr_weeks({2: (0.44, 3), 3: (0.61, 6), 4: (0.76, 9)}))
    assert result["future_duration"]["state"] == "UNVERIFIED" and result["state"] == "CURRENT" and result["observations"]
    assert result["text"]["role"].startswith("DIRECTION UP — snap share 44% → 61% → 76%")


# Production stays separate.

def test_production_is_shown_beside_role_and_only_described():
    up_flat = reads([stats("g-1", week, "BUF", targets=t, carries=0, points=8.0) for week, t in ((2, 3), (3, 6), (4, 9))],
                    [snap("g-1", week, "BUF", s) for week, s in ((2, 0.4), (3, 0.6), (4, 0.8))])
    result = evidence(up_flat)
    assert result["production"]["display"] == "8.0 → 8.0 → 8.0" and result["production"]["direction"] == "FLAT"
    assert result["production"]["comparison"] == ("Observed role increased over the supported completed games while Full-PPR production did not increase over "
                                                  "the same games.")
    flat_up = reads([stats("g-1", week, "BUF", targets=4, carries=0, points=p) for week, p in ((2, 4.0), (3, 9.5), (4, 21.0))],
                    [snap("g-1", week, "BUF", 0.7) for week in (2, 3, 4)])
    flat = evidence(flat_up)
    assert flat["direction"] == "FLAT" and flat["production"]["comparison"] == (
        "Recent Full-PPR production improved without a corresponding increase in the supported role evidence.")
    for item in (result, flat):
        assert not PROHIBITED.search(all_text(item)) and "score" not in json.dumps(item, default=str).lower()


# Coverage summary.

def test_coverage_summary_counts_the_actual_population_by_position():
    data = wr_weeks({3: (0.5, 4), 4: (0.6, 6)})
    idx = index(data)
    results = [evidence(idx, position="WR"), evidence(idx, player=None, identity="UNRESOLVED", position="WR"), evidence(idx, player="g-9", position="TE"),
               evidence(idx, position="K"), evidence(idx, position="DEF")]
    summary = role_coverage_summary(idx, results)
    assert summary["denominator"] == 5 and summary["through_week"] == 4 and summary["currency"] == "CURRENT"
    assert summary["positions"]["WR"] == {"population": 2, "current": 1, "historical_only": 0, "no_evidence": 0, "identity_unresolved": 1, "contradictory": 0,
                                          "blocked": 0, "not_applicable": 0}
    assert (summary["positions"]["TE"]["no_evidence"], summary["positions"]["K"]["not_applicable"], summary["positions"]["DEF"]["not_applicable"]) == (1, 1, 1)
    assert summary["recommendation_impact"] == "INFORMATIONAL_ONLY" and summary["refresh_command"] == "python refresh_opportunity_evidence.py"


# Batch readers: one SELECT per kind, read-time freshness, never a write.

class RecordingCursor:
    def __init__(self, results, log):
        self.results, self.log, self.query = results, log, ""

    def execute(self, query, params=None):
        self.query = query
        self.log.append((query, params))

    def fetchall(self):
        return next((rows for marker, rows in self.results.items() if marker in self.query), [])

    def close(self):
        pass


class RecordingConnection:
    def __init__(self, results):
        self.results, self.log = results, []

    def cursor(self):
        return RecordingCursor(self.results, self.log)


def test_batch_readers_use_one_select_per_kind_and_judge_freshness_at_read_time():
    from services.player_opportunity_reader import COLUMNS as OPP_COLUMNS, read_opportunity_observations
    from services.snap_share_reader import COLUMNS as SNAP_COLUMNS, read_snap_share_observations
    env = {"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400", "SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "86400"}
    old = NOW - timedelta(days=3)
    opp = {"season": 2026, "week": 4, "player_id": "g-1", "team": "BUF", "position": "WR", "targets": 6, "carries": 0, "fantasy_points_ppr": 9.5,
           "scoring_format": "FULL_PPR", "calculation_version": "full-ppr.v1", "source": "automated:nflverse", "source_authority": "automated",
           "source_recorded_at": old, "retrieved_at": old, "artifact_id": "stats_player_week_2026", "version": "stats_player_week_2026", "checksum": "c",
           "freshness_threshold_id": "opportunity.evidence.v1", "freshness_state": "FRESH", "completeness_state": "COMPLETE", "lineage": {}, "publication_state": "PUBLISHED"}
    snap_row = {"season": 2026, "week": 4, "player_id": "g-1", "pfr_player_id": "p1", "team": "BUF", "snap_share": 0.6, "source": "automated:nflverse",
                "source_authority": "automated", "source_recorded_at": NOW, "retrieved_at": NOW, "artifact_id": "snap_counts", "version": "snap_counts_2026",
                "checksum": "c", "freshness_threshold_id": "snap_share.evidence.v1", "freshness_state": "FRESH", "completeness_state": "COMPLETE",
                "lineage": json.dumps({"sample": {"participation_domain": "OFFENSE", "snap_count": "40", "position": "WR"}}), "publication_state": "PUBLISHED"}
    connection = RecordingConnection({"AND player_id = ANY": [tuple(opp.get(column) for column in OPP_COLUMNS)],
                                      "GROUP BY week, team": [(4, "BUF", 30, old, old)]})
    result = read_opportunity_observations(connection, player_ids=["g-1", "g-1", " ", None], season=2026, now=NOW, threshold_environment=env)
    assert [params for _, params in connection.log] == [(2026, ["g-1"]), (2026,)]
    assert all(query.lstrip().upper().startswith("SELECT") for query, _ in connection.log)
    [row] = result["rows"]
    assert (row["freshness_state"], row["persisted_freshness_state"], row["provenance_blockers"]) == ("STALE", "FRESH", [])
    assert result["coverage"] == [{"week": 4, "team": "BUF", "rows": 30, "retrieved_at": old, "source_recorded_at": old, "freshness_state": "STALE"}]
    snaps = RecordingConnection({"AND player_id = ANY": [tuple(snap_row.get(column) for column in SNAP_COLUMNS)], "GROUP BY week, team": [(4, "BUF", 40, NOW, NOW)]})
    snap_result = read_snap_share_observations(snaps, player_ids=["g-1"], season=2026, now=NOW, threshold_environment=env)
    [srow] = snap_result["rows"]
    assert (srow["freshness_state"], srow["participation_domain"], srow["source_snap_count"], srow["provenance_blockers"]) == ("FRESH", "OFFENSE", "40", [])
    assert snap_result["coverage"][0]["freshness_state"] == "FRESH" and len(snaps.log) == 2
    no_ids = RecordingConnection({})
    assert read_snap_share_observations(no_ids, player_ids=[], season=2026, threshold_environment=env)["state"] == "READ" and len(no_ids.log) == 1
    unpublished = read_opportunity_observations(RecordingConnection({"AND player_id = ANY": [tuple({**opp, "publication_state": "DRAFT"}.get(c) for c in OPP_COLUMNS)]}),
                                                player_ids=["g-1"], season=2026, now=NOW, threshold_environment=env)
    assert unpublished["rows"][0]["provenance_blockers"] == ["OPPORTUNITY_PUBLICATION_STATE_INVALID"]
    assert read_opportunity_observations(RecordingConnection({}), player_ids=["g-1"], season=None)["state"] == "BLOCKED"


# Explicit refresh: completed weeks only, each source atomic, failure keeps stored evidence.

class ScheduleConnection:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        rows = self.rows

        class Cursor:
            def execute(self, query, params=None):
                assert query.lstrip().upper().startswith("SELECT") and params == (2026,)

            def fetchall(self):
                return [tuple(row.get(key) for key in ("week", "home_team", "away_team", "result", "source")) for row in rows]

            def close(self):
                pass
        return Cursor()


def test_refresh_publishes_only_completed_weeks_and_reports_each_source():
    from refresh_opportunity_evidence import refresh_opportunity_evidence
    calls = []

    def step(name, *, fail=False, weeks=(1, 2, 3, 4)):
        def run(season, through_week, environ):
            calls.append((name, season, through_week))
            if fail:
                raise RuntimeError("nflverse unavailable")
            evidence = {"weeks": list(weeks), "rows": [{}] * 3, "provenance": {"retrieved_at": "now", "checksum": "sha"}, "reconciliation": {"reconciled": True}}
            return evidence, (lambda evidence: None), (lambda connection, evidence: calls.append((name, "published")) or 3)
        return run

    def current(connection, season, through_week, rows, environ):
        return {key: {"currency": "CURRENT"} for key in ("stats_player_week", "snap_counts")}

    fakes = {"environ": {}, "stored": lambda connection, season: {}, "evaluate": current}
    connection = ScheduleConnection(schedule())
    result = refresh_opportunity_evidence(connection, season=2026, steps=(("stats_player_week", step("stats")), ("snap_counts", step("snaps"))), **fakes)
    assert (result["status"], result["exit_code"], result["through_week"]) == ("success", 0, 4)
    assert calls == [("stats", 2026, 4), ("stats", "published"), ("snaps", 2026, 4), ("snaps", "published")]
    calls.clear()
    dry = refresh_opportunity_evidence(connection, season=2026, dry_run=True, steps=(("stats_player_week", step("stats")),), **fakes)
    assert dry["sources"]["stats_player_week"]["state"] == "DRY_RUN" and ("stats", "published") not in calls
    calls.clear()
    partial = refresh_opportunity_evidence(connection, season=2026, steps=(("stats_player_week", step("stats", fail=True)), ("snap_counts", step("snaps"))), **fakes)
    failed = partial["sources"]["stats_player_week"]
    assert (partial["status"], partial["exit_code"]) == ("partial", 2)
    assert (failed["state"], failed["stage"], failed["error"], failed["prior_evidence"]) == ("FAILED", "acquisition", "RuntimeError: nflverse unavailable", "RETAINED")
    assert ("stats", "published") not in calls and ("snaps", "published") in calls
    beyond = refresh_opportunity_evidence(connection, season=2026, steps=(("snap_counts", step("snaps", weeks=(1, 5))),), **fakes)
    assert beyond["status"] == "failed" and beyond["sources"]["snap_counts"]["stage"] == "validation"
    assert "after the completed Week 4" in beyond["sources"]["snap_counts"]["error"]
    nothing = refresh_opportunity_evidence(ScheduleConnection(schedule(completed=0, final_current=())), season=2026, steps=(), **fakes)
    assert (nothing["status"], nothing["exit_code"], nothing["through_week"]) == ("no_completed_week", 0, None) and "No 2026 week is complete" in nothing["message"]
