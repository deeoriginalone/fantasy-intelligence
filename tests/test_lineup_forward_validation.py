import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.authoritative_week import build_sleeper_week_contract
from services.game_lock import build_roster_game_locks
from services.lineup_decision_intelligence import build_lineup_decision
from services.lineup_forward_validation import capture_lineup_snapshots, review_lineup_snapshots, sleeper_actual_points
from services.pre_decision_snapshots import snapshot_identity
from services.team_needs import league_settings_contract

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)
KICKOFF = NOW + timedelta(hours=3)
SOURCE = "automated:nflverse-schedules:games.csv.gz:sha256:fixture"
FRESH_HEALTH = {"state": "AVAILABLE", "source": "Sleeper API", "freshness_state": "FRESH", "last_verified": NOW.isoformat()}
SCORING = {"rec": 1.0, "rec_yd": 0.1, "rush_yd": 0.1}
RB_LINE = {"rushYds": 50.0, "receptions": 1.0, "recYds": 5.0}


def game(home, away, *, result=None):
    return {"season": 2026, "week": 10, "home_team": home, "away_team": away, "game_time_utc": KICKOFF, "source": SOURCE,
            "source_recorded_at": NOW - timedelta(hours=2), "retrieved_at": NOW - timedelta(hours=2), "result": result}


def row(player_id, position, value, *, slot=None, index=None, team="KC", status="Active", known=True):
    return {"player": f"P{player_id}", "position": position, "source_player_id": player_id, "nfl_team": team, "injury_status": status,
            "health_status_available": known, "opponent": "BUF" if team == "KC" else "MIA", "is_bye": False, "weekly_score": value,
            "weekly_baseline": value, "matchup_modifier": 0.0, "injury_multiplier": 1.0, "sleeper_current_starter": slot is not None,
            "sleeper_lineup_slot": slot, "sleeper_lineup_index": index}


def roster(**weekly):
    values = {"1": 20.0, "2": 10.0, "3": 8.0, "4": 12.0, "5": 0.0, "6": None, **weekly}
    return [row("1", "QB", values["1"], slot="QB", index=0), row("2", "RB", values["2"], slot="RB", index=1),
            row("3", "WR", values["3"], slot="FLEX", index=2), row("4", "RB", values["4"]), row("5", "RB", values["5"], team="NYJ"),
            row("6", "WR", values["6"], status="", known=False)]


def provider(player_id, line=RB_LINE):
    return {"state": "PRELIMINARY", "projected_ppg": 15.0, "season": 2026, "week": 10, "source_record_time": "2026-11-15T12:00:00+00:00",
            "retrieved_at": "2026-11-15T13:00:00+00:00", "data_through_week": 9, "scoring_format": "ppr", "attribution": "JerryGM projections.",
            "provider_position": "RB", "provider_team": "KC", "sleeper_id": player_id, "roster_status": "active",
            "provider_availability": {"injury_status": None, "p_play": 0.97}, "stat_line": line, "blockers": ["JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED"]}


def lineup(rows=None, *, now=NOW, projections=None):
    rows = rows if rows is not None else roster()
    locks = build_roster_game_locks(rows, schedule_rows=[game("KC", "BUF"), game("NYJ", "MIA")], season=2026, week=10, now=now, max_age_seconds=86400)
    settings = league_settings_contract({"roster_positions": ["QB", "RB", "FLEX", "BN", "BN", "BN"], "scoring_settings": SCORING})
    return build_lineup_decision(rows, league_settings=settings, team_health=FRESH_HEALTH, season=2026, week=10, game_locks=locks, now=now,
                                 provider_projections=projections, scoring_settings=SCORING)


class SnapshotStore:
    """In-memory pre_decision_snapshots with the migration's primary-key ON CONFLICT DO NOTHING behavior."""

    def __init__(self, fail_inserts=()):
        self.rows, self.statements, self.inserts, self.fail_inserts = {}, [], 0, set(fail_inserts)
        self.commits = self.rollbacks = 0

    def connect(self):
        return StoreConnection(self)

    def payloads(self):
        return {payload["decision_subject"]: payload for payload in (json.loads(text) for text in self.rows.values())}


class StoreConnection:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return StoreCursor(self.store)

    def commit(self):
        self.store.commits += 1

    def rollback(self):
        self.store.rollbacks += 1

    def close(self):
        pass


class StoreCursor:
    def __init__(self, store):
        self.store, self.rowcount = store, -1

    def execute(self, sql, params=None):
        self.store.statements.append(" ".join(sql.split()))
        if "INSERT INTO pre_decision_snapshots" in sql:
            self.store.inserts += 1
            if self.store.inserts in self.store.fail_inserts:
                raise RuntimeError("database unavailable")
            self.rowcount = 0 if params[0] in self.store.rows else 1
            self.store.rows.setdefault(params[0], params[-1])

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


WRITE_VERBS = ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "ALTER", "DROP", "CREATE")


def writes(store):
    return [statement for statement in store.statements if statement.upper().startswith(WRITE_VERBS)]


def capture(contract, store, *, at=NOW + timedelta(minutes=1)):
    return capture_lineup_snapshots(store.connect, contract, clock=lambda: at)


def test_pre_kickoff_decisions_are_persisted_with_their_decision_time_evidence():
    contract = lineup()
    store = SnapshotStore()
    result = capture(contract, store)
    assert result["state"] == "CAPTURED" and result["counts"]["captured"] == 6 and result["decision_effect"] == "NONE"
    stored = store.payloads()
    for decision in contract["slots"]:
        output = stored[f"sleeper:{decision['recommended']['player_id']}"]["decision_output"]
        assert (output["decision"], output["recommended_slot"], output["decision_confidence"]) == (decision["decision"], decision["slot"], decision["decision_confidence"])
    decisions = {subject: (payload["decision_output"]["decision"], payload["decision_output"]["changed"]) for subject, payload in stored.items()}
    assert decisions == {"sleeper:1": ("START", False), "sleeper:2": ("START", False), "sleeper:3": ("SIT", True), "sleeper:4": ("FLEX", True),
                         "sleeper:5": ("SIT", False), "sleeper:6": ("MONITOR", False)}
    flex = stored["sleeper:4"]
    output = flex["decision_output"]
    assert (flex["season"], flex["week"], flex["captured_at"], flex["entity_identity"]["sleeper_id"]) == (2026, 10, NOW.isoformat(), "4")
    assert (output["current_slot"], output["slot_status"], output["opponent"], output["nfl_team"]) == ("BENCH", "CHANGE", "BUF", "KC")
    assert output["lock"].items() >= {"contract_id": "lineup.game_lock.v1", "state": "OPEN", "kickoff_utc": KICKOFF.isoformat(), "decision_authority": True,
                                   "freshness_state": "FRESH", "schedule_source": SOURCE}.items()
    assert output["health_evidence"].items() >= {"state": "HEALTHY", "verified": True, "source": "Sleeper API", "freshness_state": "FRESH"}.items()
    assert output["weekly_value"].items() >= {"basis": "REPOSITORY_WEEKLY_SCORE", "value": 12.0, "state": "AVAILABLE"}.items()
    assert output["contract_versions"] == {"snapshot_output": "lineup.forward_validation.snapshot.v1", "lineup_decision": "lineup-decision.v1",
                                           "game_lock": "lineup.game_lock.v1", "league_scored_projection": "league-scored-projection.v1"}
    assert stored["sleeper:3"]["decision_output"]["related_slots"][0].items() >= {"slot": "FLEX", "role": "OUTGOING", "status": "CHANGE"}.items()


def test_stored_snapshot_reconstructs_the_decision_without_later_mutable_state():
    contract = lineup()
    store = SnapshotStore()
    capture(contract, store)
    built = {snapshot["decision_subject"]: snapshot for snapshot in contract["forward_validation"]["snapshots"]}
    stored = store.payloads()
    assert stored == built and all(snapshot_identity(payload) == payload["snapshot_id"] for payload in stored.values())
    for view in contract["players"]:
        view["value"]["value"], view["health"]["state"], view["lock"]["state"] = 99.0, "OUT", "LOCKED"
    for decision in contract["slots"]:
        decision["decision"] = "SIT"
    assert store.payloads() == stored
    assert {snapshot["decision_subject"]: snapshot for snapshot in contract["forward_validation"]["snapshots"]} == stored
    review = review_lineup_snapshots(list(stored.values()), actual_points=sleeper_actual_points([]), schedule_rows=[], season=2026, week=10)
    assert [(row["player_id"], row["decision"], row["recommended_slot"], row["weekly_value"]["value"]) for row in review["players"]][:4] == [
        ("1", "START", "QB", 20.0), ("2", "START", "RB", 10.0), ("3", "SIT", None, 8.0), ("4", "FLEX", "FLEX", 12.0)]


def test_locked_or_post_kickoff_decisions_are_never_captured_as_pre_kickoff():
    connections = []
    after_kickoff = lineup(now=KICKOFF + timedelta(minutes=1))
    result = capture_lineup_snapshots(lambda: connections.append(1), after_kickoff, clock=lambda: KICKOFF + timedelta(minutes=1))
    assert result["state"] == "UNAVAILABLE" and connections == [] and {item["reason"] for item in result["not_eligible"]} == {"LOCK_LOCKED"}
    store = SnapshotStore()
    late_write = capture(lineup(), store, at=KICKOFF)
    assert late_write["state"] == "UNAVAILABLE" and store.rows == {} and writes(store) == []
    assert {item["reason"] for item in late_write["rejected"]} == {"KICKOFF_PASSED_BEFORE_CAPTURE"}
    tampered = copy.deepcopy(lineup())
    unverified, altered = tampered["forward_validation"]["snapshots"][:2]
    unverified["decision_output"]["lock"]["decision_authority"] = False
    altered["decision_output"]["decision"] = "SIT"
    rejected = {item["snapshot_id"]: item["reason"] for item in capture(tampered, store)["rejected"]}
    assert rejected == {unverified["snapshot_id"]: "KICKOFF_LOCK_NOT_VERIFIED_OPEN",
                        altered["snapshot_id"]: "SNAPSHOT_INVALID: snapshot_id does not match immutable snapshot content"}
    assert len(store.rows) == 4 and not rejected.keys() & store.rows.keys()


def test_reruns_are_idempotent_and_never_overwrite_the_original_evidence():
    store = SnapshotStore()
    first = capture(lineup(), store)
    original = dict(store.rows)
    rerun = capture(lineup(now=NOW + timedelta(minutes=30)), store, at=NOW + timedelta(minutes=31))
    assert rerun["state"] == "NO_NEW_EVIDENCE" and rerun["counts"]["duplicates"] == 6 and store.rows == original
    assert {json.loads(text)["captured_at"] for text in store.rows.values()} == {NOW.isoformat()}
    changed = capture(lineup(roster(**{"6": 5.0}), now=NOW + timedelta(minutes=45)), store, at=NOW + timedelta(minutes=46))
    assert changed["state"] == "CAPTURED" and all(store.rows[key] == text for key, text in original.items()) and len(store.rows) > len(original)
    assert first["counts"]["captured"] == 6 and all("ON CONFLICT (snapshot_id) DO NOTHING" in statement for statement in writes(store))
    assert not any(statement.upper().startswith(("UPDATE", "DELETE")) for statement in store.statements)


def test_verified_zero_and_missing_evidence_stay_distinct_without_defaults():
    store = SnapshotStore()
    capture(lineup(), store)
    stored = store.payloads()
    zero, missing = stored["sleeper:5"], stored["sleeper:6"]
    assert zero["decision_output"]["weekly_value"].items() >= {"value": 0.0, "state": "AVAILABLE", "evidence_level": "PRELIMINARY", "blocker": None}.items()
    assert missing["decision_output"]["weekly_value"].items() >= {"value": None, "state": "UNAVAILABLE", "evidence_level": "INSUFFICIENT", "blocker": "WEEKLY_VALUE_UNAVAILABLE"}.items()
    assert "WEEKLY_VALUE_UNAVAILABLE" in missing["blockers"] and "WEEKLY_VALUE_UNAVAILABLE" not in zero["blockers"]
    assert "WEEKLY_VALUE" in {item["domain"] for item in missing["decision_output"]["missing_evidence"]}
    assert (missing["decision_output"]["health_evidence"]["state"], missing["decision_output"]["health_evidence"]["verified"]) == ("UNKNOWN", False)
    output = zero["decision_output"]
    assert (output["league_scored_projection"], output["league_scored_range"], output["projection_evidence_state"]) == (None, None, "UNAVAILABLE")
    assert (zero["completeness_state"], zero["freshness_state"], zero["blockers"][0]) == ("UNAVAILABLE", "UNAVAILABLE", "PROVIDER_PROJECTION_NOT_REQUESTED")


def test_preliminary_and_informational_evidence_keeps_its_labels():
    projections = {"state": "AVAILABLE", "blockers": [], "players": {"4": provider("4")}}
    def selection(result):
        return result["recommended_lineup"], [(change["verb"], change["slot"], change["start"]["player_id"], change["sit"]["player_id"]) for change in result["changes"]]

    without = lineup()
    contract = lineup(projections=projections)
    assert selection(contract) == selection(without) and selection(contract)[1] == [("FLEX", "FLEX", "4", "3")]
    store = SnapshotStore()
    capture(contract, store)
    payload = store.payloads()["sleeper:4"]
    output = payload["decision_output"]
    assert (output["league_scored_projection"], output["projection_evidence_state"], payload["evidence_state"]) == (6.5, "PRELIMINARY", "AVAILABLE")
    assert output["projection_evidence"]["recommendation_impact"] == "INFORMATIONAL_ONLY" and output["weekly_value"]["evidence_level"] == "PRELIMINARY"
    assert output["lineup"]["projection_basis"].items() >= {"recommendation_impact": "INFORMATIONAL_ONLY", "used_for": "INFORMATIONAL_COMPARISON"}.items()
    assert output["lineup"]["projection_basis"]["action_threshold"]["state"] == "UNAPPROVED" and output["lineup"]["value_basis"]["evidence_level"] == "PRELIMINARY"
    assert payload["decision_effect"] == "NONE" and payload["freshness_state"] == "UNAVAILABLE"


def test_database_failure_fails_safely_without_touching_stored_snapshots():
    def refuse():
        raise ConnectionError("database down")

    down = capture_lineup_snapshots(refuse, lineup(), clock=lambda: NOW + timedelta(minutes=1))
    assert down["state"] == "FAILED" and down["counts"]["failed"] == 6 and down["counts"]["captured"] == 0
    store = SnapshotStore()
    capture(lineup(), store)
    original = dict(store.rows)
    store.fail_inserts = {store.inserts + 2}
    partial = capture(lineup(roster(**{"6": 5.0}), now=NOW + timedelta(minutes=45)), store, at=NOW + timedelta(minutes=46))
    assert partial["state"] == "PARTIAL" and [item["reason"] for item in partial["failed"]] == ["DATABASE_WRITE_FAILED: RuntimeError"]
    assert store.rollbacks == 1 and all(store.rows[key] == text for key, text in original.items())
    assert len(store.rows) == len(original) + partial["counts"]["captured"]
    assert not any(statement.upper().startswith(("UPDATE", "DELETE")) for statement in store.statements)


def team_app(monkeypatch, store):
    from flask import Flask
    import owner_operations

    now = datetime.now(timezone.utc)
    schedule = [{"home_team": "KC", "away_team": "BUF", "game_time_utc": now + timedelta(days=2), "game_time_pacific": None, "source": SOURCE,
                 "source_recorded_at": now - timedelta(hours=1), "retrieved_at": now - timedelta(hours=1)}]
    names = {"1": ("Alpha QB", "QB"), "2": ("Bravo RB", "RB"), "3": ("Charlie WR", "WR"), "4": ("Delta RB", "RB")}
    weekly = {"Alpha QB": 20.0, "Bravo RB": 10.0, "Charlie WR": 8.0, "Delta RB": 12.0}
    catalog = {pid: {"full_name": name, "position": position, "team": "KC", "status": "Active"} for pid, (name, position) in names.items()}
    pages = []
    real_render = owner_operations.render_template

    def render(name, **kwargs):
        pages.append(kwargs["lineup_decision"])
        return real_render(name, **kwargs)

    def enrich(cur, rows, week, **kwargs):
        return [{**item, "opponent": "BUF", "is_bye": False, "weekly_score": weekly.get(item["player"]), "weekly_baseline": weekly.get(item["player"]),
                 "matchup_modifier": 0.0, "injury_multiplier": 1.0} for item in rows]

    monkeypatch.setattr(owner_operations, "render_template", render)
    monkeypatch.setattr(owner_operations, "enrich_players", enrich)
    monkeypatch.setattr(owner_operations, "build_team_opportunity_changes", lambda *args, **kwargs: {"state": "UNAVAILABLE", "players": [], "blockers": [], "decision_effect": "INFORMATIONAL_ONLY"})
    monkeypatch.setattr(owner_operations, "read_week_schedule_rows", lambda cur, season, week: schedule)
    monkeypatch.setenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", "604800")
    blueprint = owner_operations.create_owner_operations_blueprint(
        store.connect,
        lambda league_id: {"name": "Controlled", "roster_positions": ["QB", "RB", "FLEX", "BN"], "scoring_settings": {"rec": 1.0}},
        lambda league_id: [{"user_id": "owner", "is_owner": True}],
        lambda league_id: [{"owner_id": "owner", "roster_id": 1, "players": ["1", "2", "3", "4"], "starters": ["1", "2", "3"]}],
        lambda: catalog,
        lambda value: str(value).lower().replace(" ", ""),
    )
    app = Flask(__name__, root_path=str(ROOT), template_folder="templates")
    app.config.update(TESTING=True, SLEEPER_LEAGUE_ID="controlled")
    app.config["WEEK_AUTHORITY_ACQUIRER"] = lambda season: build_sleeper_week_contract({"season": str(season), "week": 3}, season=season)
    app.register_blueprint(blueprint)
    app.jinja_env.globals["url_for"] = lambda *args, **kwargs: "/"
    app.jinja_env.globals["ux_roster_lineage"] = lambda rows: []
    app.jinja_env.globals["ux_route_evidence"] = lambda *args: {"fields": {}}
    return app, pages


def test_capture_command_stores_the_page_decision_without_changing_it_or_submitting_anything(monkeypatch):
    import requests

    outbound = []
    monkeypatch.setattr(requests.Session, "request", lambda self, method, url, *args, **kwargs: outbound.append((method, url)) or pytest.fail("no outbound request"))
    store = SnapshotStore()
    app, pages = team_app(monkeypatch, store)
    assert app.test_client().get("/team").status_code == 200 and store.rows == {} and writes(store) == []
    run = app.test_cli_runner().invoke(args=["owner_ops", "capture-lineup-snapshots"])
    result = json.loads(run.output)
    assert run.exit_code == 0 and result["state"] == "CAPTURED" and result["counts"]["captured"] == 4 and result["decision_effect"] == "NONE"
    assert app.test_client().get("/team").status_code == 200
    before, after = pages
    assert before["recommended_lineup"] == after["recommended_lineup"] and before["changes"] == after["changes"]
    assert [(change["verb"], change["start"]["player"], change["sit"]["player"]) for change in after["changes"]] == [("FLEX", "Delta RB", "Charlie WR")]
    stored = {subject: (payload["decision_output"]["decision"], payload["decision_output"]["recommended_slot"]) for subject, payload in store.payloads().items()}
    assert stored == {"sleeper:1": ("START", "QB"), "sleeper:2": ("START", "RB"), "sleeper:3": ("SIT", None), "sleeper:4": ("FLEX", "FLEX")}
    assert outbound == [] and len(writes(store)) == 4
    assert all(statement.startswith("INSERT INTO pre_decision_snapshots") and "ON CONFLICT (snapshot_id) DO NOTHING" in statement for statement in writes(store))


def test_post_week_review_compares_only_final_sleeper_points():
    store = SnapshotStore()
    capture(lineup(roster(**{"4": 11.0}), now=NOW - timedelta(hours=1)), store, at=NOW - timedelta(hours=1))
    capture(lineup(projections={"state": "AVAILABLE", "blockers": [], "players": {"4": provider("4")}}), store)
    payloads = [json.loads(text) for text in store.rows.values()]
    late = copy.deepcopy(payloads[0])
    late["captured_at"] = KICKOFF.isoformat()
    schedule = [game("KC", "BUF", result="7"), game("NYJ", "MIA")]
    matchups = [{"roster_id": 1, "players_points": {"1": 21.5, "2": 0.0, "3": 4.0, "5": 0.0}},
                {"roster_id": 2, "players_points": {"4": 9.2, "3": 6.0}}]
    review = review_lineup_snapshots([*payloads, late], actual_points=sleeper_actual_points(matchups, retrieved_at=KICKOFF + timedelta(days=2)),
                                     schedule_rows=schedule, season=2026, week=10)
    rows = {row["player_id"]: row for row in review["players"]}
    assert review["state"] == "PARTIAL" and review["decision_effect"] == "NONE" and review["excluded"][0]["reason"] == "NOT_PROVEN_PRE_KICKOFF"
    assert (rows["1"]["actual"]["state"], rows["1"]["actual"]["points"], rows["2"]["actual"]["points"]) == ("AVAILABLE", 21.5, 0.0)
    assert (rows["3"]["actual"]["state"], rows["3"]["actual"]["points"]) == ("CONTRADICTORY", None)
    assert (rows["5"]["actual"]["state"], rows["5"]["actual"]["points"], rows["5"]["game"]["reason"]) == ("NOT_FINAL", None, "GAME_RESULT_NOT_PUBLISHED")
    assert (rows["6"]["actual"]["state"], rows["6"]["actual"]["reason"]) == ("UNAVAILABLE", "PLAYER_NOT_IN_SLEEPER_MATCHUPS")
    assert (rows["4"]["snapshot_count"], rows["4"]["weekly_value"]["value"], rows["4"]["decision"], rows["4"]["actual"]["points"]) == (2, 12.0, "FLEX", 9.2)
    assert rows["4"]["projection_difference"] == {"state": "AVAILABLE", "reason": None, "actual_minus_projection": 2.7, "evidence_level": "PRELIMINARY",
                                                  "recommendation_impact": "INFORMATIONAL_ONLY"}
    assert rows["1"]["projection_difference"] == {"state": "NOT_COMPARED", "reason": "PROJECTION_UNAVAILABLE", "actual_minus_projection": None}
    unavailable = review_lineup_snapshots(payloads, actual_points=sleeper_actual_points(None), schedule_rows=schedule, season=2026, week=10)
    assert unavailable["state"] == "UNAVAILABLE" and {row["actual"]["points"] for row in unavailable["players"]} == {None}
