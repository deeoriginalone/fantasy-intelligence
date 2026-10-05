import json
from datetime import datetime, timedelta, timezone
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from services.jerrygm_projections import (
    JerryGMProjectionClient,
    build_projection_edge,
    build_projection_evidence,
    build_changed_slot_projections,
)


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
ATTRIBUTION = "JerryGM projections. Derived from openly licensed nflverse data."


class Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def response(*players, generated_at=None, scoring="ppr", season=2026, week=5, **extra):
    return {
        "season": season,
        "week": week,
        "horizon": "week",
        "scoring": scoring,
        "source": "jgm_baseline",
        "generatedAt": generated_at or NOW.isoformat(),
        "dataThroughWeek": week - 1,
        "players": list(players),
        "attribution": ATTRIBUTION,
        **extra,
    }


def provider_player(sleeper_id, points=10.0):
    return {
        "name": f"Player {sleeper_id}",
        "projectedPPG": points,
        "ids": {"sleeper": sleeper_id},
    }


def evidence(payload, ids=("s1", "s2"), *, max_age=86400, threshold_id="jerrygm.fixture.ttl.v1", now=NOW):
    return build_projection_evidence(
        payload,
        ids,
        season=2026,
        week=5,
        scoring="ppr",
        retrieved_at=now.isoformat(),
        freshness_max_age_seconds=max_age,
        freshness_threshold_id=threshold_id,
        now=now,
    )


def test_exact_sleeper_ids_produce_provider_ppr_projection_evidence():
    result = evidence(response(provider_player("s1", 18.25), provider_player("s2", 12.0)))

    assert result["s1"]["sleeper_id"] == "s1"
    assert result["s1"]["projected_ppg"] == 18.25
    assert result["s1"]["metric_name"] == "Provider Full-PPR Projection"
    assert result["s1"]["unit"] == "fantasy_points_per_game"
    assert result["s1"]["state"] == "AVAILABLE"
    assert result["s1"]["evidence_level"] == "PRELIMINARY"
    assert result["s1"]["recommendation_impact"] == "INFORMATIONAL_ONLY"
    assert "confidence" not in result["s1"]
    assert "decision" not in result["s1"]


def test_compatible_players_get_informational_edge_only():
    result = evidence(response(provider_player("s1", 18.25), provider_player("s2", 12.0)))
    edge = build_projection_edge(result["s1"], result["s2"])

    assert edge["state"] == "AVAILABLE"
    assert edge["comparison_edge"] == pytest.approx(6.25)
    assert edge["unit"] == "fantasy_points_per_game"
    assert edge["recommendation_impact"] == "INFORMATIONAL_ONLY"
    assert edge["scoring_format"] == "ppr"


def test_verified_zero_is_preserved_and_zero_edge_is_not_unavailable():
    result = evidence(response(provider_player("s1", 0), provider_player("s2", 0)))
    edge = build_projection_edge(result["s1"], result["s2"])

    assert result["s1"]["projected_ppg"] == 0
    assert edge["state"] == "AVAILABLE"
    assert edge["comparison_edge"] == 0


def test_missing_player_and_ambiguous_identity_fail_closed():
    missing = evidence(response(provider_player("s1")))
    ambiguous = evidence(response(provider_player("s1"), provider_player("s1"), provider_player("s2")))

    assert missing["s2"]["projected_ppg"] is None
    assert missing["s2"]["blockers"] == ["JERRYGM_PLAYER_NOT_RETURNED"]
    assert ambiguous["s1"]["blockers"] == ["JERRYGM_PLAYER_ID_AMBIGUOUS"]


@pytest.mark.parametrize(
    ("payload", "blocker"),
    [
        (response(provider_player("s1"), provider_player("s2"), scoring="half"), "JERRYGM_SCORING_MISMATCH"),
        (response(provider_player("s1"), provider_player("s2"), season=2025), "JERRYGM_SEASON_WEEK_MISMATCH"),
        (response(provider_player("s1"), provider_player("s2"), week=4), "JERRYGM_SEASON_WEEK_MISMATCH"),
        (response(provider_player("s1"), provider_player("s2"), source="nflverse_naive"), "JERRYGM_SOURCE_UNSUPPORTED"),
        (response(provider_player("s1"), provider_player("s2"), degraded={"missingSeasons": ["prior"]}), "JERRYGM_SOURCE_DEGRADED"),
        (response(provider_player("s1"), provider_player("s2"), attribution=""), "JERRYGM_ATTRIBUTION_UNAVAILABLE"),
    ],
)
def test_incompatible_or_incomplete_response_fails_closed(payload, blocker):
    result = evidence(payload)

    assert all(item["state"] == "UNAVAILABLE" for item in result.values())
    assert all(item["blockers"] == [blocker] for item in result.values())


def test_missing_generated_time_fails_closed():
    payload = response(provider_player("s1"), provider_player("s2"), generatedAt=None)
    payload["generatedAt"] = None

    result = evidence(payload)

    assert all(item["blockers"] == ["JERRYGM_TIMESTAMP_UNAVAILABLE"] for item in result.values())


@pytest.mark.parametrize(
    ("age", "expected"),
    [(timedelta(hours=1), "FRESH"), (timedelta(hours=20), "AGING"), (timedelta(hours=30), "STALE")],
)
def test_source_timestamp_freshness_uses_explicit_threshold(age, expected):
    generated_at = (NOW - age).isoformat()
    result = evidence(response(provider_player("s1"), provider_player("s2"), generated_at=generated_at))

    assert result["s1"]["freshness_state"] == expected
    if expected == "STALE":
        assert result["s1"]["state"] == "STALE"
        assert result["s1"]["evidence_level"] == "HISTORICAL_CONTEXT_ONLY"
        assert build_projection_edge(result["s1"], result["s2"])["state"] == "UNAVAILABLE"


def test_missing_source_specific_freshness_threshold_keeps_value_but_blocks_current_use():
    result = build_projection_evidence(
        response(provider_player("s1")),
        ["s1"],
        season=2026,
        week=5,
        scoring="ppr",
        retrieved_at=NOW.isoformat(),
    )["s1"]

    assert result["projected_ppg"] == 10
    assert result["source_record_time"] == NOW.isoformat()
    assert result["age_seconds"] == 0
    assert result["freshness_state"] == "UNAVAILABLE"
    assert result["blockers"] == ["JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED"]


@pytest.mark.parametrize("value", ["not-a-number", float("nan"), float("inf"), float("-inf")])
def test_nonnumeric_and_nonfinite_projection_values_fail_closed(value):
    result = evidence(response(provider_player("s1", value)))

    assert result["s1"]["projected_ppg"] is None
    assert result["s1"]["blockers"] == ["JERRYGM_PROJECTION_INVALID"]


def test_failed_refresh_never_returns_old_projection_or_new_source_time():
    def fail_request(*_args, **_kwargs):
        raise URLError("offline")

    result = JerryGMProjectionClient(
        api_key="fixture-key",
        opener=fail_request,
        clock=lambda: NOW,
    ).fetch(["s1"], season=2026, week=5, scoring="ppr")["s1"]

    assert result["projected_ppg"] is None
    assert result["source_record_time"] is None
    assert result["retrieved_at"] == NOW.isoformat()
    assert result["blockers"] == ["JERRYGM_REFRESH_FAILED"]


def test_missing_api_key_returns_blocked_without_network_request():
    called = False

    def unexpected_request(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("request must not run without a key")

    result = JerryGMProjectionClient(api_key="", opener=unexpected_request).fetch(
        ["s1"], season=2026, week=5, scoring="ppr"
    )

    assert called is False
    assert result["s1"]["state"] == "BLOCKED"
    assert result["s1"]["blockers"] == ["JERRYGM_CONFIGURATION_BLOCKED"]


def test_client_reads_existing_jerrygm_token_environment_name(monkeypatch):
    monkeypatch.setenv("JERRYGM_TOKEN", "fixture-token")
    monkeypatch.delenv("JERRYGM_API_KEY", raising=False)

    client = JerryGMProjectionClient()

    assert client.api_key == "fixture-token"


def test_client_prefers_jerrygm_api_key_environment_name(monkeypatch):
    monkeypatch.setenv("JERRYGM_API_KEY", "api-key-name")
    monkeypatch.setenv("JERRYGM_TOKEN", "legacy-token-name")

    client = JerryGMProjectionClient()

    assert client.api_key == "api-key-name"


def test_request_is_read_only_scoped_to_sleeper_ids_and_preset_scoring():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response(response(provider_player("s1")))

    JerryGMProjectionClient(api_key="fixture-key", opener=opener, clock=lambda: NOW).fetch(
        ["s1"], season=2026, week=5, scoring="ppr", freshness_max_age_seconds=86400,
        freshness_threshold_id="jerrygm.fixture.ttl.v1",
    )
    request = captured["request"]
    query = parse_qs(urlparse(request.full_url).query)

    assert request.get_method() == "GET"
    assert request.get_header("X-api-key") == "fixture-key"
    assert query["ids"] == ["s1"]
    assert query["idType"] == ["sleeper"]
    assert query["scoring"] == ["ppr"]
    assert captured["timeout"] == 30


def test_free_request_limit_is_enforced():
    with pytest.raises(ValueError, match="JERRYGM_FREE_ID_LIMIT_EXCEEDED"):
        JerryGMProjectionClient(api_key="fixture-key").fetch(
            [f"s{index}" for index in range(26)], season=2026, week=5, scoring="ppr"
        )


def test_comparison_rejects_provider_or_metric_context_conflict():
    result = evidence(response(provider_player("s1", 15), provider_player("s2", 12)))
    current = dict(result["s2"], source="other-provider")

    edge = build_projection_edge(result["s1"], current)

    assert edge["state"] == "UNAVAILABLE"
    assert edge["comparison_edge"] is None
    assert edge["blocker"] == "JERRYGM_COMPARISON_CONTEXT_MISMATCH"


def test_returned_attribution_is_preserved_for_display():
    result = evidence(response(provider_player("s1")))

    assert result["s1"]["attribution"] == ATTRIBUTION


def test_changed_slot_fetch_uses_only_exact_sleeper_roster_ids():
    calls = []

    class FixtureClient:
        def fetch(self, sleeper_ids, *, season, week, scoring):
            calls.append((sleeper_ids, season, week, scoring))
            return evidence(response(*(provider_player(player_id) for player_id in sleeper_ids)), sleeper_ids, max_age=None, threshold_id=None)

    result = build_changed_slot_projections(
        [
            {"source_player_id": "sid-current", "local_player_id": "local-current"},
            {"source_player_id": "sid-recommended", "local_player_id": "local-recommended"},
        ],
        [{"slot": "QB", "current_id": "sid-current", "recommended_id": "sid-recommended"}],
        season=2026,
        week=5,
        client=FixtureClient(),
    )

    assert calls == [(["sid-recommended", "sid-current"], 2026, 5, "ppr")]
    assert result["QB"]["recommended"]["sleeper_id"] == "sid-recommended"
    assert result["QB"]["current"]["sleeper_id"] == "sid-current"
    assert result["QB"]["comparison"]["state"] == "UNAVAILABLE"
    assert result["QB"]["comparison"]["blocker"] == "JERRYGM_COMPARISON_FRESHNESS_UNAVAILABLE"


def test_changed_slot_fetch_rejects_ambiguous_sleeper_identity_without_name_join():
    calls = []

    class FixtureClient:
        def fetch(self, sleeper_ids, *, season, week, scoring):
            calls.append(sleeper_ids)
            return evidence(response(*(provider_player(player_id) for player_id in sleeper_ids)), sleeper_ids, max_age=None, threshold_id=None)

    result = build_changed_slot_projections(
        [
            {"source_player_id": "sid-current", "local_player_id": "local-a", "player": "Current"},
            {"source_player_id": "sid-current", "local_player_id": "local-b", "player": "Current"},
            {"source_player_id": "sid-recommended", "local_player_id": "local-c", "player": "Recommended"},
        ],
        [{"slot": "QB", "current_id": "sid-current", "recommended_id": "sid-recommended"}],
        season=2026,
        week=5,
        client=FixtureClient(),
    )

    assert calls == [["sid-recommended"]]
    assert result["QB"]["current"]["projected_ppg"] is None
    assert result["QB"]["current"]["blockers"] == ["JERRYGM_CURRENT_IDENTITY_AMBIGUOUS"]