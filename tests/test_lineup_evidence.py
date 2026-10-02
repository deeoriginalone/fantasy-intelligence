from services.lineup_evidence import build_lineup_evidence, build_matchup_evidence, build_projection_evidence

NOW = "2026-09-16T12:00:00+00:00"


def player(**updates):
    value = {
        "source_player_id": "sleeper-123",
        "local_player_id": 123,
        "position": "WR",
        "opponent": "KC",
        "projection": 120.0,
        "projection_source": "players.projected_points",
        "projection_retrieved_at": NOW,
        "projection_lineage": {"source": "players.projected_points"},
        "matchup_rank": 12,
        "matchup_source": "automated:nflverse",
        "matchup_retrieved_at": NOW,
        "matchup_lineage": {"source": "automated:nflverse", "version": "v1"},
    }
    value.update(updates)
    return value


def test_projection_preserves_identity_timestamps_and_explicit_source_blocker():
    result = build_projection_evidence(player(), season=2026, week=3, now=NOW)
    assert result["identity"] == {"source_player_id": "sleeper-123", "local_player_id": 123}
    assert result["season"] == 2026
    assert result["week"] == 3
    assert result["value"] == 120.0
    assert result["retrieved_at"] == NOW
    assert result["lineage"] == {"source": "players.projected_points"}
    assert result["freshness_state"] == "FRESH"
    assert "PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False
    assert result["projection_consumable"] is True


def test_matchup_preserves_identity_context_and_unverified_threshold_blockers():
    result = build_matchup_evidence(player(), season=2026, week=3, now=NOW)
    assert result["identity"] == {"source_player_id": "sleeper-123", "local_player_id": 123}
    assert result["opponent_identity"] == "KC"
    assert result["position"] == "WR"
    assert result["scoring_context"] == "FULL_PPR"
    assert result["freshness_state"] == "FRESH"
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_POPULATION_UNVERIFIED" in result["blockers"]
    assert result["decision_effect"] == "NONE"


def test_projection_blockers_are_warnings_for_projection_consumption():
    result = build_projection_evidence(player(), season=2026, week=3, now=NOW)
    assert result["projection_consumable"] is True
    assert result["authoritative"] is False


def test_published_metadata_is_preserved_without_upgrading_missing_authority():
    result = build_matchup_evidence(player(
        matchup_source_recorded_at=NOW,
        matchup_version="release-2026-w3",
        matchup_checksum="abc123",
        matchup_publication_lineage={"source": "nflverse", "artifact": "weekly.csv.gz"},
        matchup_sample_size=8,
        matchup_population="NFL WR opponents",
        matchup_directionality="LOWER_IS_HARDER",
        matchup_sample_threshold_id=None,
    ), season=2026, week=3, now=NOW)
    assert result["source_recorded_at"] == NOW
    assert result["version"] == "release-2026-w3"
    assert result["checksum"] == "abc123"
    assert result["lineage"] == {"source": "nflverse", "artifact": "weekly.csv.gz"}
    assert result["sample_size"] == 8
    assert result["comparison_population"] == "NFL WR opponents"
    assert result["rank_directionality"] == "LOWER_IS_HARDER"
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_POPULATION_UNVERIFIED" not in result["blockers"]
    assert "MATCHUP_DIRECTIONALITY_UNVERIFIED" not in result["blockers"]


def test_shared_lineup_evidence_preserves_partial_authority_and_blockers():
    projection = build_projection_evidence(player(), season=2026, week=3, now=NOW)
    matchup = build_matchup_evidence(player(), season=2026, week=3, now=NOW)
    result = build_lineup_evidence(projection, matchup)
    assert result["authoritative"] is False
    assert result["state"] == "BLOCKED"
    assert "PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE" in result["blockers"]
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert result["projection"]["lineage"] == projection["lineage"]
    assert result["matchup"]["lineage"] == matchup["lineage"]
    assert result["decision_effect"] == "NONE"


def test_missing_and_stale_evidence_fail_closed_without_values():
    missing = player(projection=None, projection_retrieved_at=None, matchup_source="Unavailable", matchup_retrieved_at=None)
    projection = build_projection_evidence(missing, season=2026, week=3, now=NOW)
    matchup = build_matchup_evidence(missing, season=2026, week=3, now=NOW)
    assert projection["value"] is None
    assert projection["freshness_state"] == "UNAVAILABLE"
    assert "PROJECTION_VALUE_UNAVAILABLE" in projection["blockers"]
    assert matchup["freshness_state"] == "UNAVAILABLE"
    assert "MATCHUP_SOURCE_UNAVAILABLE" in matchup["blockers"]
    stale = build_projection_evidence(player(projection_retrieved_at="2020-01-01T00:00:00+00:00"), season=2026, week=3, now=NOW)
    assert stale["freshness_state"] == "STALE"
    assert "PROJECTION_DATA_STALE" in stale["blockers"]


def test_identity_missing_is_blocked():
    result = build_matchup_evidence(player(source_player_id=None, local_player_id=None), season=2026, week=3, now=NOW)
    assert "MATCHUP_PLAYER_IDENTITY_UNAVAILABLE" in result["blockers"]


def test_display_formatted_matchup_source_does_not_override_structured_authority():
    result = build_matchup_evidence(player(
        matchup_source="nfl_schedule + automated:nflverse:weekly-w3",
        matchup_source_authority="automated",
        matchup_sample_threshold_id="matchup.sample.v1",
        matchup_population="ALL_DEFENSES_BY_POSITION",
        matchup_directionality="LOWER_IS_HARDER",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE" not in result["blockers"]
    assert result["source_authority"] == "automated"


def test_missing_structured_source_authority_fails_closed_on_display_formatted_source():
    result = build_matchup_evidence(player(
        matchup_source="nfl_schedule + automated:nflverse:weekly-w3",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE" in result["blockers"]
    assert result["source_authority"] == "UNVERIFIED"


def test_missing_population_blocker_persists_with_other_contract_fields_present():
    result = build_matchup_evidence(player(
        matchup_source_authority="automated",
        matchup_sample_threshold_id="matchup.sample.v1",
        matchup_directionality="LOWER_IS_HARDER",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_POPULATION_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" not in result["blockers"]
    assert "MATCHUP_DIRECTIONALITY_UNVERIFIED" not in result["blockers"]
    assert result["authoritative"] is False


def test_missing_directionality_blocker_persists_with_other_contract_fields_present():
    result = build_matchup_evidence(player(
        matchup_source_authority="automated",
        matchup_sample_threshold_id="matchup.sample.v1",
        matchup_population="ALL_DEFENSES_BY_POSITION",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_DIRECTIONALITY_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" not in result["blockers"]
    assert "MATCHUP_POPULATION_UNVERIFIED" not in result["blockers"]
    assert result["authoritative"] is False


def test_fully_authoritative_matchup_evidence_when_all_contract_fields_verified():
    result = build_matchup_evidence(player(
        matchup_source_authority="automated",
        matchup_sample_threshold_id="matchup.sample.v1",
        matchup_population="ALL_DEFENSES_BY_POSITION",
        matchup_directionality="LOWER_IS_HARDER",
    ), season=2026, week=3, now=NOW)
    assert result["blockers"] == []
    assert result["authoritative"] is True
    assert result["comparison_population"] == "ALL_DEFENSES_BY_POSITION"
    assert result["rank_directionality"] == "LOWER_IS_HARDER"


def test_missing_rank_is_not_authoritative_even_with_complete_contract():
    result = build_matchup_evidence(player(
        matchup_rank=None,
        matchup_source_authority="automated",
        matchup_sample_threshold_id="matchup.sample.v1",
        matchup_population="ALL_DEFENSES_BY_POSITION",
        matchup_directionality="LOWER_IS_HARDER",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_RANK_MISSING" in result["blockers"]
    assert result["authoritative"] is False


def test_rank_with_incomplete_contract_is_not_authoritative():
    result = build_matchup_evidence(player(
        matchup_source_authority="automated",
        matchup_sample_threshold_id=None,
        matchup_population="ALL_DEFENSES_BY_POSITION",
        matchup_directionality="LOWER_IS_HARDER",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED" in result["blockers"]
    assert "MATCHUP_RANK_CONTRACT_INCOMPLETE" in result["blockers"]
    assert result["authoritative"] is False


def test_unrelated_blockers_remain_intact_when_matchup_authority_is_verified():
    result = build_matchup_evidence(player(
        opponent=None,
        matchup_source_authority="automated",
        matchup_sample_threshold_id="matchup.sample.v1",
        matchup_population="ALL_DEFENSES_BY_POSITION",
        matchup_directionality="LOWER_IS_HARDER",
    ), season=2026, week=3, now=NOW)
    assert "MATCHUP_OPPONENT_IDENTITY_UNAVAILABLE" in result["blockers"]
    assert "MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE" not in result["blockers"]
    assert result["authoritative"] is False


def lineup_player(pid, name, position, *, slot=None, current_slot=None, index=None, **updates):
    row = {"player": name, "position": position, "source_player_id": pid, "injury_status": "Healthy", "weekly_score": 10.0, "rank": 10}
    if slot:
        row.update(slot=slot, vacant=False, decision="START")
    if current_slot:
        row.update(sleeper_current_starter=True, sleeper_lineup_slot=current_slot, sleeper_lineup_index=index)
    row.update(updates)
    return row


def current_and_recommended(recommended_wr2="w3"):
    roster = [
        lineup_player("q1", "QB One", "QB", current_slot="QB", index=0),
        lineup_player("w1", "WR One", "WR", current_slot="WR", index=1),
        lineup_player("w2", "WR Two", "WR", current_slot="WR", index=2),
        lineup_player("w3", "WR Three", "WR"),
        lineup_player("r1", "RB One", "RB"),
    ]
    by_id = {row["source_player_id"]: row for row in roster}
    recommended = [
        {**by_id["q1"], "slot": "QB", "vacant": False},
        {**by_id["w1"], "slot": "WR1", "vacant": False},
        {**by_id[recommended_wr2], "slot": "WR2", "vacant": False},
    ]
    return roster, recommended


def test_matching_current_and_recommended_lineups_have_no_pending_changes():
    from owner_operations import build_lineup_reconciliation
    roster, recommended = current_and_recommended(recommended_wr2="w2")
    result = build_lineup_reconciliation(roster, recommended, [])
    assert result["state"] == "AVAILABLE"
    assert result["changes"] == [] and result["changed_recommended"] == []
    assert [row["slot"] for row in result["current"]] == ["QB", "WR1", "WR2"]


def test_different_lineups_produce_deterministic_identity_based_changes():
    from owner_operations import build_lineup_reconciliation
    roster, recommended = current_and_recommended()
    decisions = [{"slot": "WR2", "decision": "START", "reason": "Supported weekly value."}]
    first = build_lineup_reconciliation(roster, recommended, decisions)
    second = build_lineup_reconciliation(roster, recommended, decisions)
    assert first["changes"] == second["changes"]
    assert [(c["slot"], c["current_id"], c["recommended_id"], c["authority"]) for c in first["changes"]] == [("WR2", "w2", "w3", "START")]
    assert first["changed_recommended"][0]["replaced_current"] == "WR Two"


def test_slot_swap_among_current_starters_is_not_a_pending_change():
    from owner_operations import build_lineup_reconciliation
    roster, _ = current_and_recommended()
    by_id = {row["source_player_id"]: row for row in roster}
    recommended = [{**by_id["q1"], "slot": "QB"}, {**by_id["w2"], "slot": "WR1"}, {**by_id["w1"], "slot": "WR2"}]
    assert build_lineup_reconciliation(roster, recommended, [])["changes"] == []


def test_displayed_bench_excludes_every_recommended_starter_and_keeps_the_rest():
    from owner_operations import build_recommended_bench
    roster, recommended = current_and_recommended()
    bench = build_recommended_bench(roster, recommended)
    assert {row["source_player_id"] for row in bench} == {"w2", "r1"}
    assert all(row["decision"] in {"SIT", "MONITOR"} for row in bench)
    assert [row["bench_order"] for row in bench] == [1, 2]


def test_duplicate_names_do_not_override_stable_identity():
    from owner_operations import build_lineup_reconciliation, build_recommended_bench
    roster = [
        lineup_player("a", "Same Name", "QB", current_slot="QB", index=0),
        lineup_player("b", "Same Name", "QB"),
    ]
    recommended = [{**roster[1], "slot": "QB", "vacant": False}]
    result = build_lineup_reconciliation(roster, recommended, [])
    assert [(c["current_id"], c["recommended_id"]) for c in result["changes"]] == [("a", "b")]
    assert [row["source_player_id"] for row in build_recommended_bench(roster, recommended)] == ["a"]


def test_missing_current_lineup_identity_fails_closed():
    from owner_operations import build_lineup_reconciliation
    roster, recommended = current_and_recommended()
    roster[1] = {**roster[1], "source_player_id": None}
    result = build_lineup_reconciliation(roster, recommended, [])
    assert result["state"] == "UNAVAILABLE"
    assert result["blocker"] == "CURRENT_LINEUP_IDENTITY_UNAVAILABLE"
    assert result["changes"] == []
    assert build_lineup_reconciliation([], recommended, [])["blocker"] == "CURRENT_LINEUP_UNAVAILABLE"


def test_incomplete_current_lineup_does_not_claim_ready_or_changes():
    from owner_operations import build_lineup_reconciliation
    roster, recommended = current_and_recommended()
    roster[2] = {**roster[2], "sleeper_current_starter": False}
    result = build_lineup_reconciliation(roster, recommended, [])
    assert result["state"] == "UNAVAILABLE"
    assert result["blocker"] == "CURRENT_LINEUP_INCOMPLETE"
    assert result["changes"] == []


def test_unverified_recommended_identity_keeps_committed_bench():
    from owner_operations import build_lineup_reconciliation, build_recommended_bench
    roster, recommended = current_and_recommended()
    recommended[2] = {**recommended[2], "source_player_id": None}
    assert build_recommended_bench(roster, recommended) is None
    assert build_lineup_reconciliation(roster, recommended, [])["blocker"] == "RECOMMENDED_LINEUP_IDENTITY_UNAVAILABLE"


def test_reconciliation_does_not_alter_lineup_decisions():
    import copy
    from owner_operations import build_lineup_reconciliation, build_recommended_bench
    roster, recommended = current_and_recommended()
    decisions = [{"slot": slot, "decision": value} for slot, value in (("QB", "START"), ("WR1", "FLEX"), ("WR2", "MONITOR"))]
    before = copy.deepcopy((roster, recommended, decisions))
    build_lineup_reconciliation(roster, recommended, decisions)
    build_recommended_bench(roster, recommended)
    assert (roster, recommended, decisions) == before


class TeamRouteCursor:
    def execute(self, query, params=None):
        pass

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class TeamRouteConnection:
    def cursor(self):
        return TeamRouteCursor()

    def close(self):
        pass


def render_team_route(monkeypatch, reconciliation=None, drop_reconciliation=False):
    from pathlib import Path
    from flask import Flask
    import owner_operations
    catalog = {
        "1": {"full_name": "Alpha QB", "position": "QB", "team": "KC", "injury_status": None, "gsis_id": "00-0000001", "espn_id": "101"},
        "2": {"full_name": "Bravo WR", "position": "WR", "team": "KC", "injury_status": None, "gsis_id": "00-0000002", "espn_id": "102"},
        "3": {"full_name": "Charlie WR", "position": "WR", "team": "KC", "injury_status": None, "gsis_id": "00-0000003", "espn_id": "103"},
    }
    captured = {"catalog": catalog}
    real_render = owner_operations.render_template

    def capture(name, **kwargs):
        if drop_reconciliation:
            kwargs.pop("lineup_reconciliation", None)
        captured.update(kwargs)
        return real_render(name, **kwargs)

    monkeypatch.setattr(owner_operations, "render_template", capture)
    if reconciliation is not None:
        monkeypatch.setattr(owner_operations, "build_lineup_reconciliation", lambda *args, **kwargs: reconciliation)
    monkeypatch.setattr(owner_operations, "enrich_players", lambda cur, roster, week, **kwargs: [{**row, "weekly_baseline": 10.0, "weekly_score": 10.0, "matchup_modifier": 0.0, "injury_multiplier": 1.0} for row in roster])
    monkeypatch.setattr(owner_operations, "current_week", lambda cur: 3)
    league = {"name": "Controlled", "roster_positions": ["QB", "WR", "WR", "BN"], "scoring_settings": {"rec": 1.0}}
    blueprint = owner_operations.create_owner_operations_blueprint(
        lambda: TeamRouteConnection(),
        lambda league_id: league,
        lambda league_id: [{"user_id": "owner", "is_owner": True}],
        lambda league_id: [{"owner_id": "owner", "roster_id": 1, "players": ["1", "2", "3"], "starters": ["1", "2"]}],
        lambda: catalog,
        lambda value: str(value).lower().replace(" ", ""),
    )
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder="templates")
    app.config.update(TESTING=True, SLEEPER_LEAGUE_ID="controlled")
    app.register_blueprint(blueprint)
    app.jinja_env.globals["url_for"] = lambda *args, **kwargs: "/"
    app.jinja_env.globals["ux_roster_lineage"] = lambda roster: []
    app.jinja_env.globals["ux_route_evidence"] = lambda *args: {"fields": {}}
    response = app.test_client().get("/team")
    return response, captured


def test_team_route_carries_current_lineup_fields_and_committed_payloads(monkeypatch):
    import owner_operations
    response, captured = render_team_route(monkeypatch)
    assert response.status_code == 200
    by_id = {row["source_player_id"]: row for row in captured["roster"]}
    assert by_id["1"]["sleeper_current_starter"] is True and by_id["1"]["sleeper_lineup_slot"] == "QB" and by_id["1"]["sleeper_lineup_index"] == 0
    assert by_id["2"]["sleeper_lineup_slot"] == "WR" and by_id["2"]["sleeper_lineup_index"] == 1
    assert by_id["3"]["sleeper_current_starter"] is False and by_id["3"]["sleeper_lineup_slot"] is None
    assert all("sleeper_gsis_id" in row and "sleeper_espn_id" in row for row in captured["roster"])
    assert captured["meta"]["sleeper_catalog"] is captured["catalog"]
    assert captured["lineup_reconciliation"]["state"] in {"AVAILABLE", "UNAVAILABLE"}
    assert "team_needs" in captured and "opportunity_changes" in captured
    assert callable(owner_operations.build_team_opportunity_changes)


NO_CHANGES = "No lineup changes recommended."
COMPARISON_UNAVAILABLE = "Lineup comparison unavailable. The current Sleeper lineup could not be fully compared with the recommended lineup."


def test_team_template_available_with_changes_shows_supported_change(monkeypatch):
    change = {"slot": "WR2", "current": "Bravo WR", "current_id": "2", "recommended": "Charlie WR", "recommended_id": "3", "authority": "START", "recommended_player": {"player": "Charlie WR", "reason": "Supported weekly value."}, "reason": "Supported weekly value.", "watch_item": None, "confidence": None}
    reconciliation = {"state": "AVAILABLE", "blocker": None, "current": [{"slot": "QB", "player": "Alpha QB", "position": "QB", "injury_status": "Healthy"}], "recommended": [], "changes": [change], "changed_recommended": [change["recommended_player"]]}
    response, _ = render_team_route(monkeypatch, reconciliation)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "1 lineup changes recommended" in html and "Charlie WR" in html
    assert f"<p>{NO_CHANGES}</p>" not in html and COMPARISON_UNAVAILABLE not in html


def test_team_template_available_without_changes_claims_no_changes(monkeypatch):
    reconciliation = {"state": "AVAILABLE", "blocker": None, "current": [{"slot": "QB", "player": "Alpha QB", "position": "QB", "injury_status": "Healthy"}], "recommended": [], "changes": [], "changed_recommended": []}
    response, _ = render_team_route(monkeypatch, reconciliation)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert f"<p>{NO_CHANGES}</p>" in html
    assert COMPARISON_UNAVAILABLE not in html


def test_team_template_unavailable_comparison_never_claims_no_changes(monkeypatch):
    reconciliation = {"state": "UNAVAILABLE", "blocker": "CURRENT_LINEUP_INCOMPLETE", "current": [], "recommended": [], "changes": [], "changed_recommended": []}
    response, captured = render_team_route(monkeypatch, reconciliation)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert f"<p>{NO_CHANGES}</p>" not in html
    assert COMPARISON_UNAVAILABLE in html
    assert "missing a starter for at least one recommended slot" in html
    assert "CURRENT_LINEUP_INCOMPLETE" not in html
    assert "team_needs" in captured and "opportunity_changes" in captured


def test_team_template_missing_reconciliation_payload_fails_closed(monkeypatch):
    response, captured = render_team_route(monkeypatch, drop_reconciliation=True)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "lineup_reconciliation" not in captured
    assert f"<p>{NO_CHANGES}</p>" not in html
    assert COMPARISON_UNAVAILABLE in html
