from services.player_opportunity_calculation import calculate_player_opportunity
from services.opportunity_evidence import build_nflverse_usage_evidence

NOW = "2026-09-17T12:00:00+00:00"


def stat_row(player_id, team, opponent, week=3, targets=0, carries=0, season=2026):
    return {"player_id": player_id, "team": team, "opponent_team": opponent, "season": season, "week": week, "targets": targets, "carries": carries}


def rows():
    return [
        stat_row("p1", "KC", "DEN", targets=8, carries=0),
        stat_row("p2", "KC", "DEN", targets=2, carries=15),
        stat_row("p3", "DEN", "KC", targets=5, carries=5),
        stat_row("p4", "DEN", "KC", targets=5, carries=5),
    ]


def test_target_carry_touch_share_computed_from_team_totals():
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    by_id = {row["player_id"]: row for row in evidence["rows"]}
    assert by_id["p1"]["target_share"] == 0.8
    assert by_id["p2"]["carry_share"] == 1.0
    assert by_id["p3"]["target_share"] == 0.5
    assert by_id["p3"]["carry_share"] == 0.5
    assert by_id["p1"]["touch_share"] == 0.32
    assert evidence["rows"][0]["authoritative"] is True


def test_unavailable_metrics_are_disclosed_not_invented():
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    assert evidence["unavailable_metrics"] == ["snap_share", "route_participation", "red_zone_share", "role_classification"]
    for row in evidence["rows"]:
        assert row["snap_share"] is None
        assert row["route_participation"] is None
        assert row["red_zone_share"] is None
        assert row["role_classification"] is None


def test_missing_identity_is_excluded_not_estimated():
    incomplete = rows() + [{"team": "KC", "opponent_team": "DEN", "season": 2026, "week": 3, "targets": 3, "carries": 0}]
    evidence = calculate_player_opportunity(incomplete, season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    assert len(evidence["unresolved_identities"]) == 1
    assert evidence["unresolved_identities"][0]["reason"] == "OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"
    assert len(evidence["rows"]) == 4


def test_missing_threshold_fails_closed_without_a_numeric_default():
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": ""})
    assert evidence["freshness_state"] == "UNAVAILABLE"
    assert evidence["blocker"] == "OPPORTUNITY_FRESHNESS_THRESHOLD_UNVERIFIED"
    assert all(not row["authoritative"] for row in evidence["rows"])
    assert evidence["publication_contracts"]["threshold"]["state"] == "UNAVAILABLE"


def test_missing_retrieved_at_fails_closed():
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=None, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    assert evidence["freshness_state"] == "UNAVAILABLE"
    assert evidence["blocker"] == "OPPORTUNITY_RETRIEVAL_TIME_UNAVAILABLE"


def test_stale_evidence_is_blocked_not_silently_used():
    old = "2020-01-01T00:00:00+00:00"
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=old, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    assert evidence["freshness_state"] == "STALE"
    assert evidence["blocker"] == "OPPORTUNITY_DATA_STALE"
    assert all(not row["authoritative"] for row in evidence["rows"])


def test_no_team_targets_leaves_share_unavailable_not_zero():
    evidence = calculate_player_opportunity([stat_row("p1", "KC", "DEN", targets=0, carries=0)], season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    row = evidence["rows"][0]
    assert row["target_share"] is None
    assert row["carry_share"] is None
    assert row["touch_share"] is None


def test_publication_contract_never_invents_a_threshold_default():
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=NOW, now=NOW, threshold_environment={})
    contract = evidence["publication_contracts"]["threshold"]
    assert contract["identifier"] == "opportunity.evidence.v1"
    assert contract["value"] is None
    assert contract["state"] == "UNAVAILABLE"


def test_build_nflverse_usage_evidence_passes_through_new_metrics_without_inventing_them():
    result = build_nflverse_usage_evidence(
        {"targets": 8, "target_share": 0.22, "carries": 3, "carry_share": 0.4, "touch_share": 0.3},
        player_id="player-1", season=2026, week=3, source="automated:nflverse",
        source_recorded_at=NOW, retrieved_at=NOW, freshness_state="FRESH",
    )
    assert result["carry_share"] == 0.4
    assert result["touch_share"] == 0.3
    assert result["snap_share"] is None
    assert result["route_participation"] is None
    assert result["red_zone_share"] is None
    assert result["role_classification"] is None


FRESH_ENV = {"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"}


# 1. all input rows are accounted for
def test_all_input_rows_are_accounted_for():
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV)
    reconciliation = evidence["reconciliation"]
    assert reconciliation["input_row_count"] == len(rows())
    assert reconciliation["published_row_count"] + reconciliation["excluded_row_count"] == reconciliation["input_row_count"]
    assert reconciliation["reconciled"] is True


# 6. unresolved identity is explicitly counted
def test_unresolved_identity_is_explicitly_counted():
    incomplete = rows() + [{"team": "KC", "opponent_team": "DEN", "season": 2026, "week": 3, "targets": 3, "carries": 0}]
    evidence = calculate_player_opportunity(incomplete, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV)
    reconciliation = evidence["reconciliation"]
    assert reconciliation["unresolved_identity_count"] == 1
    assert reconciliation["input_row_count"] == len(incomplete)
    assert reconciliation["published_row_count"] + reconciliation["excluded_row_count"] == reconciliation["input_row_count"]
    assert reconciliation["reconciled"] is True


# 4. duplicate player-week is detected and excluded from publication
def test_duplicate_player_week_is_detected_and_excluded():
    duplicated = rows() + [stat_row("p1", "KC", "DEN", targets=1, carries=0)]
    evidence = calculate_player_opportunity(duplicated, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV)
    reconciliation = evidence["reconciliation"]
    assert reconciliation["duplicate_player_week_count"] == 1
    assert reconciliation["duplicate_player_weeks"][0]["player_id"] == "p1"
    assert "p1" not in {row["player_id"] for row in evidence["rows"]}
    assert reconciliation["published_row_count"] + reconciliation["excluded_row_count"] == reconciliation["input_row_count"]


# 5. contradictory team identity is detected and excluded from publication
def test_contradictory_team_identity_is_detected_and_excluded():
    contradictory = rows() + [stat_row("p1", "DEN", "KC", targets=1, carries=0)]
    evidence = calculate_player_opportunity(contradictory, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV)
    reconciliation = evidence["reconciliation"]
    assert reconciliation["contradictory_player_week_count"] == 1
    assert sorted(reconciliation["contradictory_player_weeks"][0]["teams"]) == ["DEN", "KC"]
    assert "p1" not in {row["player_id"] for row in evidence["rows"]}
    assert reconciliation["published_row_count"] + reconciliation["excluded_row_count"] == reconciliation["input_row_count"]


# 7. zero eligible rows
def test_zero_eligible_rows_reconciles_with_no_published_rows():
    all_unresolved = [{"team": "KC", "opponent_team": "DEN", "season": 2026, "week": 3, "targets": 3, "carries": 0}]
    evidence = calculate_player_opportunity(all_unresolved, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV)
    assert evidence["rows"] == []
    assert evidence["reconciliation"]["eligible_input_count"] == 0
    assert evidence["reconciliation"]["reconciled"] is True


# 11. AGING follows the verified opportunity authority contract (both FRESH and AGING are authoritative)
def test_aging_evidence_remains_authoritative_per_existing_contract():
    threshold_env = {"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "100"}
    aging_retrieved_at = "2026-09-17T11:58:30+00:00"  # 90s old against a 100s threshold: AGING (>80%, <=100%)
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at=aging_retrieved_at, now=NOW, threshold_environment=threshold_env)
    assert evidence["freshness_state"] == "AGING"
    assert evidence["blocker"] is None
    assert all(row["authoritative"] for row in evidence["rows"])
