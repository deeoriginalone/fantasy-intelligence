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


IDENTITY_CATALOG = {
    "10": {"full_name": "Delta QB", "position": "QB", "team": "KC", "gsis_id": "00-0000010", "espn_id": "1010"},
    "20": {"full_name": "Echo WR", "position": "WR", "team": "BUF", "gsis_id": "00-0000020", "espn_id": "2020"},
    "30": {"full_name": "Foxtrot WR", "position": "WR", "team": "SF", "gsis_id": None, "espn_id": "3030"},
    "40": {"full_name": "Golf RB", "position": "RB", "team": "DAL", "gsis_id": "00-0000040", "espn_id": None},
}


class IdentityRouteCursor:
    def __init__(self, matched_rows):
        self.matched_rows = matched_rows
        self.value = None
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append(query)
        key = str((params or [""])[0])
        self.value = self.matched_rows.get(key) if "FROM players" in query and "LIKE" not in query else None

    def fetchone(self):
        value, self.value = self.value, None
        return value

    def fetchall(self):
        return []

    def close(self):
        pass


class IdentityRouteConnection:
    def __init__(self, matched_rows):
        self.cursor_instance = IdentityRouteCursor(matched_rows)

    def cursor(self):
        return self.cursor_instance

    def close(self):
        pass


def render_identity_route(monkeypatch, roster_ids, *, catalog=None, starters=(), matched=()):
    import copy
    from pathlib import Path
    from flask import Flask
    import owner_operations
    catalog = copy.deepcopy(IDENTITY_CATALOG if catalog is None else catalog)
    catalog_before = copy.deepcopy(catalog)
    rosters = [{"owner_id": "owner", "roster_id": 1, "players": list(roster_ids), "starters": list(starters)}]
    rosters_before = copy.deepcopy(rosters)
    matched_rows = {
        IDENTITY_CATALOG[pid]["full_name"].lower().replace(" ", ""): (IDENTITY_CATALOG[pid]["full_name"], IDENTITY_CATALOG[pid]["position"], IDENTITY_CATALOG[pid]["team"], 10, 100.0, 2, 30.0, 9, None, None, int(pid))
        for pid in matched
    }
    captured = {"opportunity_calls": []}
    real_render = owner_operations.render_template

    def capture(name, **kwargs):
        captured.update(kwargs)
        return real_render(name, **kwargs)

    def record_opportunity(connection, roster, **kwargs):
        captured["opportunity_calls"].append({"roster": [dict(player) for player in roster], **kwargs})
        return {"state": "UNAVAILABLE", "players": [], "blockers": [], "decision_effect": "INFORMATIONAL_ONLY"}

    monkeypatch.setattr(owner_operations, "render_template", capture)
    monkeypatch.setattr(owner_operations, "build_team_opportunity_changes", record_opportunity)
    monkeypatch.setattr(owner_operations, "enrich_players", lambda cur, roster, week, **kwargs: [{**row, "weekly_baseline": 10.0, "weekly_score": 10.0, "matchup_modifier": 0.0, "injury_multiplier": 1.0} for row in roster])
    monkeypatch.setattr(owner_operations, "current_week", lambda cur: 3)
    league = {"name": "Controlled", "roster_positions": ["QB", "WR", "WR", "RB", "BN"], "scoring_settings": {"rec": 1.0}}
    connection = IdentityRouteConnection(matched_rows)
    blueprint = owner_operations.create_owner_operations_blueprint(
        lambda: connection,
        lambda league_id: league,
        lambda league_id: [{"user_id": "owner", "is_owner": True}],
        lambda league_id: rosters,
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
    assert catalog == catalog_before and rosters == rosters_before
    assert not any(statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) for statement in connection.cursor_instance.statements)
    identities = {row["source_player_id"]: (row.get("sleeper_gsis_id"), row.get("sleeper_espn_id")) for row in captured["roster"]}
    return response, captured, identities


def test_each_roster_player_receives_its_own_gsis_and_espn_ids(monkeypatch):
    response, captured, identities = render_identity_route(monkeypatch, ["10", "20"], starters=["10", "20"])
    assert response.status_code == 200
    assert identities == {"10": ("00-0000010", "1010"), "20": ("00-0000020", "2020")}
    assert "lineup_reconciliation" in captured and "team_needs" in captured and "opportunity_changes" in captured


def test_reversed_roster_order_does_not_cross_assign_identities(monkeypatch):
    forward = render_identity_route(monkeypatch, ["10", "20", "40"])[2]
    monkeypatch.undo()
    reverse = render_identity_route(monkeypatch, ["40", "20", "10"])[2]
    assert forward == reverse
    assert len({gsis for gsis, _ in forward.values()}) == 3


def test_last_catalog_record_is_not_copied_onto_every_player(monkeypatch):
    identities = render_identity_route(monkeypatch, ["10", "20", "40"])[2]
    assert identities["10"] != identities["40"] and identities["20"] != identities["40"]


def test_missing_gsis_or_espn_stays_unavailable_without_borrowing(monkeypatch):
    identities = render_identity_route(monkeypatch, ["10", "30", "40"])[2]
    assert identities["30"] == (None, "3030")
    assert identities["40"] == ("00-0000040", None)
    assert identities["10"] == ("00-0000010", "1010")


def test_missing_catalog_record_does_not_inherit_another_players_ids(monkeypatch):
    _, captured, identities = render_identity_route(monkeypatch, ["10", "99", "20"])
    assert "99" not in identities
    assert identities == {"10": ("00-0000010", "1010"), "20": ("00-0000020", "2020")}


def test_matched_and_unmatched_local_branches_use_each_players_record(monkeypatch):
    _, captured, identities = render_identity_route(monkeypatch, ["10", "20", "40"], matched=["20"])
    methods = {row["source_player_id"]: row["identity_match_method"] for row in captured["roster"]}
    assert methods == {"10": "LOCAL_PLAYER_UNAVAILABLE", "20": "UNIQUE_NORMALIZED_NAME", "40": "LOCAL_PLAYER_UNAVAILABLE"}
    assert identities == {"10": ("00-0000010", "1010"), "20": ("00-0000020", "2020"), "40": ("00-0000040", None)}


def test_identity_fix_preserves_current_lineup_fields(monkeypatch):
    _, captured, _ = render_identity_route(monkeypatch, ["10", "20", "40"], starters=["10", "20"])
    lineup = {row["source_player_id"]: (row["sleeper_current_starter"], row["sleeper_lineup_slot"], row["sleeper_lineup_index"]) for row in captured["roster"]}
    assert lineup == {"10": (True, "QB", 0), "20": (True, "WR", 1), "40": (False, None, None)}
    assert captured["meta"]["season"] == 2026 and captured["meta"]["week"] == 3


def test_team_opportunity_changes_receives_player_specific_identity(monkeypatch):
    _, captured, _ = render_identity_route(monkeypatch, ["10", "20"])
    (call,) = captured["opportunity_calls"]
    assert {row["source_player_id"]: row["sleeper_gsis_id"] for row in call["roster"]} == {"10": "00-0000010", "20": "00-0000020"}
    assert call["season"] == 2026 and call["week"] == 3
    assert call["sleeper_records"] is not None and set(call["sleeper_records"]) == set(IDENTITY_CATALOG)


def test_roster_identity_assignment_is_deterministic(monkeypatch):
    first = render_identity_route(monkeypatch, ["10", "20", "30", "40"])[2]
    monkeypatch.undo()
    second = render_identity_route(monkeypatch, ["10", "20", "30", "40"])[2]
    assert first == second


def injury_catalog():
    catalog = {pid: dict(record) for pid, record in IDENTITY_CATALOG.items()}
    catalog["10"].update(injury_status="Questionable")
    catalog["20"].update(injury_status="Out")
    catalog["30"].update(injury_status=None, status=None)
    catalog["40"].update(injury_status=None, status="Inactive")
    return catalog


def render_injury_route(monkeypatch, roster_ids, **kwargs):
    response, captured, identities = render_identity_route(monkeypatch, roster_ids, catalog=injury_catalog(), **kwargs)
    health = {row["source_player_id"]: (row["injury_status"], row["health_status_available"]) for row in captured["roster"]}
    return response, captured, identities, health


def test_unmatched_players_keep_their_own_injury_status(monkeypatch):
    response, _, _, health = render_injury_route(monkeypatch, ["10", "20"])
    assert response.status_code == 200
    assert health == {"10": ("Questionable", True), "20": ("Out", True)}


def test_last_unmatched_player_status_is_not_copied_onto_others(monkeypatch):
    health = render_injury_route(monkeypatch, ["10", "20", "30"])[3]
    assert health == {"10": ("Questionable", True), "20": ("Out", True), "30": ("Unknown", False)}


def test_reversed_order_keeps_each_players_injury_status(monkeypatch):
    forward = render_injury_route(monkeypatch, ["10", "20", "30", "40"])[3]
    monkeypatch.undo()
    reverse = render_injury_route(monkeypatch, ["40", "30", "20", "10"])[3]
    assert forward == reverse
    assert forward["40"] == ("Inactive", True)


def test_missing_injury_status_stays_unknown_and_never_borrows(monkeypatch):
    _, _, _, health = render_injury_route(monkeypatch, ["20", "30", "99"])
    assert health["30"] == ("Unknown", False)
    assert "99" not in health
    assert health["20"] == ("Out", True)


def test_matched_branch_injury_status_and_identity_are_unchanged(monkeypatch):
    _, captured, identities, health = render_injury_route(monkeypatch, ["10", "20", "30"], matched=["20"])
    matched = next(row for row in captured["roster"] if row["source_player_id"] == "20")
    assert matched["identity_match_method"] == "UNIQUE_NORMALIZED_NAME"
    assert health["20"] == ("Out", True) and matched["injury_source"] == "Sleeper API"
    assert health["10"] == ("Questionable", True) and health["30"] == ("Unknown", False)
    assert identities == {"10": ("00-0000010", "1010"), "20": ("00-0000020", "2020"), "30": (None, "3030")}


def test_injury_fix_preserves_lineup_fields_payloads_and_determinism(monkeypatch):
    response, captured, _, first = render_injury_route(monkeypatch, ["10", "20", "40"], starters=["10", "20"])
    assert response.status_code == 200
    lineup = {row["source_player_id"]: (row["sleeper_current_starter"], row["sleeper_lineup_slot"], row["sleeper_lineup_index"]) for row in captured["roster"]}
    assert lineup == {"10": (True, "QB", 0), "20": (True, "WR", 1), "40": (False, None, None)}
    assert captured["team_needs"] and "lineup_reconciliation" in captured and "opportunity_changes" in captured
    assert {"verdict", "starters", "start_sit_decisions"} <= set(captured["lineup_intelligence"])
    assert {"action"} <= set(captured["team_priority_action"])
    monkeypatch.undo()
    second = render_injury_route(monkeypatch, ["10", "20", "40"], starters=["10", "20"])[3]
    assert first == second
