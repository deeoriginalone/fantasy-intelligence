from services.player_role_evidence import (
    METRIC_DEFINITIONS,
    ROLE_CLASSIFICATION_BLOCKER,
    SOURCE_DECISIONS,
    SUPPORTED_METRICS,
    build_role_evidence,
)

NOW = "2026-09-17T12:00:00+00:00"


def evidence(**overrides):
    kwargs = {
        "player_id": "p1", "season": 2026, "week": 3,
        "source": "automated:nflverse", "source_authority": "automated",
        "retrieved_at": NOW, "freshness_threshold_id": "opportunity.evidence.v1",
        "freshness_state": "FRESH",
    }
    kwargs.update(overrides)
    return build_role_evidence(**kwargs)


# 1/3. Each requested metric remains unavailable with an explicit blocker reason.
def test_all_requested_metrics_remain_unavailable_with_explicit_blockers():
    result = evidence()
    for metric in SUPPORTED_METRICS:
        assert SOURCE_DECISIONS[metric] == "SOURCE_UNAVAILABLE"
        assert result["metrics"][metric]["value"] is None
        assert result["metrics"][metric]["state"] == "SOURCE_UNAVAILABLE"
        assert result["metrics"][metric]["blocker"] == "OPPORTUNITY_METRIC_SOURCE_UNAVAILABLE"


# no importer or publication authority is invented
def test_no_importer_or_publication_authority_is_invented():
    import services.player_role_evidence as module
    assert not hasattr(module, "publish_role_evidence")
    assert not hasattr(module, "calculate_role_evidence")
    assert "psycopg2" not in open(module.__file__, encoding="utf-8").read()


# never derive metrics from unrelated raw counting stats, even if supplied
def test_metrics_are_never_derived_from_targets_carries_or_touchdowns():
    result = evidence(values={"snap_share": 12, "route_participation": 4, "red_zone_share": 2, "targets": 8, "carries": 3, "touchdowns": 2})
    for metric in SUPPORTED_METRICS:
        assert result["metrics"][metric]["value"] is None


# 4. missing identity fails closed
def test_missing_identity_fails_closed():
    result = evidence(player_id=None)
    assert "OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False


# 5. missing retrieved_at fails closed
def test_missing_retrieved_at_fails_closed():
    result = evidence(retrieved_at=None)
    assert "OPPORTUNITY_RETRIEVAL_TIME_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False


# 6. missing threshold fails closed
def test_missing_threshold_fails_closed():
    result = evidence(freshness_threshold_id=None)
    assert "OPPORTUNITY_FRESHNESS_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert result["authoritative"] is False


# 7. stale/non-current evidence fails closed
def test_non_current_freshness_fails_closed():
    result = evidence(freshness_state="STALE")
    assert "OPPORTUNITY_EVIDENCE_NOT_CURRENT" in result["blockers"]
    assert result["authoritative"] is False


def test_missing_season_or_week_fails_closed():
    assert "OPPORTUNITY_SEASON_UNAVAILABLE" in evidence(season=None)["blockers"]
    assert "OPPORTUNITY_WEEK_UNAVAILABLE" in evidence(week=None)["blockers"]


# 12. unsupported CSV/manual input cannot claim automated authority
def test_csv_source_does_not_become_authoritative():
    result = evidence(source="csv:manual-upload.csv", source_authority=None)
    assert result["source"] == "csv:manual-upload.csv"
    assert result["authoritative"] is False


# 13. role_classification remains unavailable without a verified classification contract
def test_role_classification_remains_unavailable():
    result = evidence()
    assert result["role_classification"] is None
    assert result["role_classification_blocker"] == ROLE_CLASSIFICATION_BLOCKER
    assert ROLE_CLASSIFICATION_BLOCKER in result["blockers"]


def test_fully_supplied_evidence_is_still_not_authoritative_due_to_unavailable_metrics_and_role():
    result = evidence()
    assert result["authoritative"] is False
    assert result["decision_effect"] == "INFORMATIONAL_ONLY"


def test_metric_definitions_document_required_fields_for_each_supported_metric():
    required_fields = {
        "name", "purpose", "unit", "numerator", "denominator", "eligible_population",
        "source_fields", "freshness_requirement", "missing_data_behavior", "owner",
        "validation_tests", "decision_effect",
    }
    for metric in SUPPORTED_METRICS:
        definition = METRIC_DEFINITIONS[metric]
        assert required_fields.issubset(definition.keys())
        assert definition["decision_effect"] == "INFORMATIONAL_ONLY"
