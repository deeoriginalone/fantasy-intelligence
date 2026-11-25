"""Automated W5 transaction-history refresh: the scheduled command's per-week retrieval, storage and closure report, and its systemd units.

The command runs the existing refresh (services/sleeper_snapshots.py) and reports W5's own closure verdict
(services/waiver_market_evidence.py). These tests drive it against the in-memory snapshot store of the W5 tests and a Sleeper
stand-in that, like Sleeper, returns each week's transactions once they have processed.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import pytest
import requests

import refresh_sleeper_transactions as refresh_module
from refresh_sleeper_transactions import main, refresh_league_transactions
from services.sleeper_snapshots import read_transaction_history
from services.waiver_market_evidence import build_faab_market_evidence
from tests.test_opportunity_evidence_refresh import unit, values
from tests.test_waiver_market_evidence import CATALOG, LEAGUE, PROHIBITED, SEASON, START, USERS, FakeSnapshotDB, claim, free_agent, league, rosters

ROOT = Path(__file__).resolve().parents[1]
SERVICE, TIMER = "sleeper-transactions-refresh.service", "sleeper-transactions-refresh.timer"
WIDE_ONE = "1197534528390496256"
# Week 1: a contested claim (completed $6, failed $4) and a free-agent add. Week 2: an uncontested $0 claim, a claim without a bid
# and a free-agent add, all processed at the end of the week. Week 3 (open): a free-agent add and a completed $9 claim.
SEASON_TRANSACTIONS = [
    free_agent("fa-1", 1, "x1", 1), claim(WIDE_ONE, 1, "wr-1", 1, bid=6), claim("l1", 1, "wr-1", 2, bid=4, status="failed", seq=1),
    free_agent("fa-2", 2, "x2", 2), claim("c2", 2, "rb-1", 3, bid=0), claim("c-missing", 2, "te-1", 2, settings={"seq": 0}),
    free_agent("fa-3", 3, "x3", 3), claim("c3", 3, "qb-1", 1, bid=9, run_day=2),
]


def moment(week, day=0, hour=14):
    """A time in transaction week `week`; each week begins on Wednesday START."""
    return START + timedelta(days=7 * (week - 1) + day, hours=hour)


WEEK_2 = moment(2, 4)                # Week 2 is open and its claims have not processed
QUIET_MORNING = moment(3, 0)         # Week 3 has begun, but no Week 3 transaction exists yet
AFTER_FIRST_WEEK_3 = moment(3, 2)    # a Week 3 transaction exists, so Week 2 was closed when it is retrieved now


def http_error(status, week):
    response = requests.Response()
    response.status_code, response.url = status, f"https://api.sleeper.app/v1/league/{LEAGUE}/transactions/{week}"
    return requests.HTTPError(f"{status} Server Error: Service Unavailable for url: {response.url}", response=response)


class Sleeper:
    """Read-only Sleeper at one moment: the league's current transaction week and each week's processed transactions."""

    def __init__(self, when, transactions=SEASON_TRANSACTIONS, *, fail=(), league_payload=None):
        self.leg = (when - START).days // 7 + 1
        self.league_payload = league_payload(self.leg) if callable(league_payload) else league(leg=self.leg)
        self.weeks = defaultdict(list)
        for transaction in transactions:
            if transaction["status_updated"] <= when.timestamp() * 1000:
                self.weeks[transaction["leg"]].append(transaction)
        self.fail, self.calls, self.clock = set(fail), [], when

    def get_league(self, league_id):
        self.calls.append("league")
        return copy.deepcopy(self.league_payload)

    def get_transactions(self, league_id, week):
        self.calls.append(week)
        if week in self.fail:
            raise http_error(503, week)
        return copy.deepcopy(self.weeks.get(week, []))

    def now(self):
        self.clock += timedelta(seconds=1)
        return self.clock


def run(db, when, transactions=SEASON_TRANSACTIONS, league_id=LEAGUE, **options):
    sleeper = Sleeper(when, transactions, **options)
    return refresh_league_transactions(db, league_id=league_id, get_league=sleeper.get_league, get_transactions=sleeper.get_transactions,
                                       now=sleeper.now), sleeper


def week(result, number):
    return next(entry for entry in result["weeks"] if entry["week"] == number)


def page_market(db, roster_list=None):
    """The W5 market /waivers builds from the stored weeks (live league in Week 3) with the page's users, rosters and catalog."""
    return build_faab_market_evidence(league_id=LEAGUE, season=SEASON, league=league(leg=3), users=USERS, rosters=rosters() if roster_list is None else roster_list,
                                      history=read_transaction_history(db.cursor(), LEAGUE, SEASON), catalog=CATALOG)


# Each run: retrieval, storage and W5's own closure verdict for every week.

def test_a_run_after_the_first_new_week_transaction_verifies_the_closed_week_and_reports_every_week():
    db = FakeSnapshotDB()
    first, _ = run(db, WEEK_2)
    assert (first["status"], first["exit_code"], first["verified_closed_weeks"], first["newly_verified_weeks"], first["open_weeks"]) == ("success", 0, [1], [1], [2])
    result, sleeper = run(db, AFTER_FIRST_WEEK_3)
    assert sleeper.calls == ["league", 1, 2, 3]
    assert (result["status"], result["exit_code"], result["fetch_status"], result["completeness_before"], result["completeness"]) == (
        "success", 0, "success", "PARTIAL", "COMPLETE")
    assert (result["requested_weeks"], result["fetched_weeks"], result["stored_weeks"], result["failed_weeks"]) == ([1, 2, 3], [1, 2, 3], [1, 2, 3], [])
    assert (result["verified_closed_weeks"], result["newly_verified_weeks"], result["open_weeks"], result["through_week"]) == ([1, 2], [2], [3], 2)
    assert [(entry["fetch_state"], entry["source_state"], entry["snapshot"], entry["transaction_count"], entry["closed_state_before"], entry["closed_state"])
            for entry in result["weeks"]] == [("FETCHED", "TRANSACTION_LIST", "STORED", 3, "CLOSED", "FINAL"),
                                              ("FETCHED", "TRANSACTION_LIST", "STORED", 3, "OPEN_AT_RETRIEVAL", "CLOSED"),
                                              ("FETCHED", "TRANSACTION_LIST", "STORED", 2, "OPEN", "OPEN")]
    assert [entry["payload_changed"] for entry in result["weeks"]] == [False, True, None]
    assert all(entry["retrieved_at"] == entry["requested_at"] for entry in result["weeks"])
    # One row per week holds Sleeper's exact payload, transaction IDs included; the run outcome is the one W5 reads.
    stored = read_transaction_history(db.cursor(), LEAGUE, SEASON)
    assert [row["payload"] for row in stored["rows"]] == [sleeper.weeks[number] for number in (1, 2, 3)] and len(db.rows) == 3
    assert db.runs[result["run_id"]]["status"] == stored["latest_refresh"]["status"] == "success"
    page = page_market(db)
    assert {entry["week"]: entry["closed_state"] for entry in result["weeks"]} == page["completeness"]["weeks"]
    assert (page["state"], page["through_week"], page["completeness"]["verified_weeks"]) == ("AVAILABLE", 2, result["verified_closed_weeks"])
    assert {item["transaction_id"] for item in page["claims"]} == {WIDE_ONE, "l1", "c2", "c-missing"}
    report = json.dumps(result)
    assert "$" not in report and not PROHIBITED.search(report)


def test_the_morning_after_the_waiver_run_is_partial_until_a_new_week_transaction_proves_the_week_closed():
    db = FakeSnapshotDB()
    run(db, WEEK_2)
    quiet, sleeper = run(db, QUIET_MORNING)
    # Sleeper's current week has moved on and every week was stored, but Week 2 was retrieved before any Week 3 transaction existed.
    assert (sleeper.leg, quiet["fetch_status"], quiet["stored_weeks"]) == (3, "success", [1, 2, 3])
    assert (quiet["status"], quiet["exit_code"], quiet["completeness"], quiet["verified_closed_weeks"], quiet["open_at_retrieval_weeks"], quiet["open_weeks"]) == (
        "partial", 2, "PARTIAL", [1], [2], [3])
    # sleeper_sync_runs keeps the retrieval outcome W5 already reads; the closure verdict is reported, never stored.
    assert db.runs[quiet["run_id"]]["status"] == "success"
    page = page_market(db)
    assert (page["state"], page["through_week"]) == ("PARTIAL", 1)
    assert {entry["week"]: entry["closed_state"] for entry in quiet["weeks"]} == page["completeness"]["weeks"] == {1: "CLOSED", 2: "OPEN_AT_RETRIEVAL", 3: "OPEN"}
    later, _ = run(db, AFTER_FIRST_WEEK_3)
    assert (later["status"], later["newly_verified_weeks"], later["verified_closed_weeks"], later["no_longer_verified_weeks"]) == ("success", [2], [1, 2], [])


def test_an_identical_rerun_keeps_one_row_per_week_and_changes_no_market_figure():
    db = FakeSnapshotDB()
    run(db, WEEK_2)
    run(db, AFTER_FIRST_WEEK_3)
    first = copy.deepcopy(page_market(db))
    rerun, _ = run(db, AFTER_FIRST_WEEK_3 + timedelta(hours=1))
    assert (rerun["status"], rerun["exit_code"], rerun["newly_verified_weeks"], rerun["verified_closed_weeks"]) == ("no_new_closed_week", 0, [], [1, 2])
    assert [entry["payload_changed"] for entry in rerun["weeks"]] == [False, False, False] and rerun["sample"] == rerun["sample_before"]
    assert (len(db.rows), len(db.runs), rerun["duplicates_removed"]) == (3, 3, 0)
    again = page_market(db)
    for key in ("state", "through_week", "claims", "season_summary", "recent_summary", "groups", "position_summaries", "players", "manager_spending", "budget_context"):
        assert again[key] == first[key], key


def test_a_claim_processed_after_its_week_closed_is_stored_by_the_next_run_and_the_week_never_reopens():
    # A Week 2 claim that processes in Week 3, after the first Week 3 transaction (like a claim on a player dropped just before the run).
    late = claim("late", 2, "wr-2", 1, bid=3, status="failed", run_day=9)
    db = FakeSnapshotDB()
    closed, _ = run(db, moment(3, 1), [*SEASON_TRANSACTIONS, late])
    assert (week(closed, 2)["closed_state"], closed["sample"]["failed"]) == ("CLOSED", 1)
    later, _ = run(db, moment(3, 2), [*SEASON_TRANSACTIONS, late], fail=(3,))
    # Week 3 failed, so its stored copy is the earlier one; Week 2 was refetched later and stays closed, now with the late claim.
    assert (week(later, 2)["payload_changed"], week(later, 2)["closed_state_before"], week(later, 2)["closed_state"]) == (True, "CLOSED", "CLOSED")
    assert (later["status"], later["no_longer_verified_weeks"], later["sample"]["failed"]) == ("partial", [], 2)


def test_a_failed_week_keeps_its_snapshot_and_retrieval_time_never_becomes_empty_and_the_run_is_partial():
    db = FakeSnapshotDB()
    run(db, WEEK_2)
    run(db, AFTER_FIRST_WEEK_3)
    before, summary = copy.deepcopy(db.rows), page_market(db)["season_summary"]
    result, _ = run(db, AFTER_FIRST_WEEK_3 + timedelta(days=1), fail=(2,))
    failed = week(result, 2)
    assert (result["status"], result["exit_code"], result["fetch_status"], result["failed_weeks"], result["stored_weeks"]) == ("partial", 2, "partial", [2], [1, 3])
    assert (failed["fetch_state"], failed["source_state"], failed["http_status"], failed["snapshot"], failed["prior_snapshot_retained"]) == (
        "FAILED", "HTTP_ERROR", 503, "RETAINED", True)
    assert failed["error"].startswith("HTTPError: 503 Server Error") and result["error"].startswith("Week 2: HTTPError: 503") and failed["transaction_count"] is None
    key = ("transactions", LEAGUE, SEASON, 2)
    assert db.rows[key] == before[key] and failed["retrieved_at"] == before[key]["fetched_at"].isoformat()
    assert (failed["stored_transaction_count"], failed["closed_state"]) == (3, "CLOSED")
    assert all(db.rows[other]["fetched_at"] > before[other]["fetched_at"] for other in before if other != key)
    page = page_market(db)
    assert (page["state"], page["completeness"]["latest_refresh"]["failed_weeks"], page["season_summary"]) == ("PARTIAL", [2], summary)


def test_a_week_retrieved_empty_after_it_closed_is_verified_empty_while_a_week_never_retrieved_is_missing():
    without_week_2 = [transaction for transaction in SEASON_TRANSACTIONS if transaction["leg"] != 2]
    db = FakeSnapshotDB()
    empty, _ = run(db, AFTER_FIRST_WEEK_3, without_week_2)
    assert (week(empty, 2)["snapshot"], week(empty, 2)["transaction_count"], week(empty, 2)["closed_state"]) == ("STORED", 0, "CLOSED")
    assert (empty["status"], empty["empty_verified_weeks"], empty["missing_weeks"], db.rows[("transactions", LEAGUE, SEASON, 2)]["payload"]) == (
        "success", [2], [], [])
    db = FakeSnapshotDB()
    missing, _ = run(db, AFTER_FIRST_WEEK_3, fail=(2,))
    assert (week(missing, 2)["snapshot"], week(missing, 2)["closed_state"], week(missing, 2)["prior_snapshot_retained"]) == ("MISSING", "MISSING", False)
    assert (missing["status"], missing["exit_code"], missing["missing_weeks"], missing["verified_closed_weeks"]) == ("partial", 2, [2], [1])
    assert ("transactions", LEAGUE, SEASON, 2) not in db.rows


def test_a_refresh_that_stores_nothing_fails_and_leaves_every_stored_week_untouched():
    db = FakeSnapshotDB()
    run(db, AFTER_FIRST_WEEK_3)
    rows = copy.deepcopy(db.rows)

    def unreachable(league_id):
        raise requests.ConnectionError("Sleeper unreachable")

    def no_week_without_a_league(league_id, number):
        pytest.fail("a week was requested without a verified league")
    result = refresh_league_transactions(db, league_id=LEAGUE, get_league=unreachable, get_transactions=no_week_without_a_league)
    assert (result["status"], result["exit_code"], result["requested_weeks"], result["error"]) == ("failed", 1, [], "League: ConnectionError: Sleeper unreachable")
    assert db.rows == rows and db.runs[result["run_id"]]["status"] == "failed"
    everything, _ = run(db, AFTER_FIRST_WEEK_3 + timedelta(hours=1), fail=(1, 2, 3))
    assert (everything["status"], everything["exit_code"], everything["stored_weeks"]) == ("failed", 1, [])
    assert [entry["snapshot"] for entry in everything["weeks"]] == ["RETAINED"] * 3 and db.rows == rows
    # The stored weeks stay readable; the failed attempts only stop coverage from claiming COMPLETE.
    assert (page_market(db)["state"], page_market(db)["through_week"]) == ("PARTIAL", 2)


def test_without_a_verified_closed_week_market_history_stays_unavailable_and_is_never_invented():
    db = FakeSnapshotDB()
    # Week 1 is still open: nothing has closed yet, so there is no history and nothing is wrong.
    opening, _ = run(db, moment(1, 2))
    assert (opening["status"], opening["exit_code"], opening["stored_weeks"], opening["open_weeks"], opening["verified_closed_weeks"]) == (
        "no_new_closed_week", 0, [1], [1], [])
    assert (opening["completeness"], opening["market_state"], opening["through_week"], opening["sample"]) == ("UNAVAILABLE", "UNAVAILABLE", None, None)
    # Sleeper has moved to Week 2, but no Week 2 transaction proves Week 1 closed: still no history, and the run is partial.
    unproven, _ = run(db, moment(2))
    assert (unproven["status"], unproven["exit_code"], unproven["open_at_retrieval_weeks"], unproven["completeness"], unproven["market_state"]) == (
        "partial", 2, [1], "UNAVAILABLE", "UNAVAILABLE")
    # A first run that retrieves no week stores nothing, and the page shows no verified week rather than an empty history.
    db = FakeSnapshotDB()
    nothing, _ = run(db, AFTER_FIRST_WEEK_3, fail=(1, 2, 3))
    assert (nothing["status"], nothing["exit_code"], nothing["missing_weeks"], nothing["completeness"], db.rows) == ("failed", 1, [1, 2], "UNAVAILABLE", {})
    page = page_market(db)
    assert (page["state"], page["through_week"], page["blockers"], page["claims"], page["season_summary"]) == (
        "UNAVAILABLE", None, ["NO_VERIFIED_TRANSACTION_WEEK"], [], None)


def test_a_database_failure_reports_only_its_type_and_stores_no_week():
    import psycopg2

    class WriteFailure(FakeSnapshotDB):
        def cursor(self):
            cursor = super().cursor()
            execute = cursor.execute

            def guarded(query, params=()):
                if query.startswith("INSERT INTO sleeper_api_snapshots"):
                    raise psycopg2.OperationalError('server "db.internal" closed the connection for user "fantasy-owner"')
                return execute(query, params)
            cursor.execute = guarded
            return cursor

    db = WriteFailure()
    result, _ = run(db, AFTER_FIRST_WEEK_3)
    assert (result["status"], result["exit_code"], db.rows) == ("failed", 1, {})
    assert result["error"] == "The refresh failed (OperationalError); no transaction week from this run was stored."
    assert "db.internal" not in json.dumps(result) and "fantasy-owner" not in json.dumps(result)
    # The interrupted attempt stays visible as running, so W5 never counts it as a successful refresh.
    assert [entry["status"] for entry in db.runs.values()] == ["running"]


def test_one_transaction_id_counts_once_and_conflicting_records_for_it_fail_closed():
    contested = next(transaction for transaction in SEASON_TRANSACTIONS if transaction["transaction_id"] == WIDE_ONE)
    db = FakeSnapshotDB()
    repeated, _ = run(db, AFTER_FIRST_WEEK_3, [*SEASON_TRANSACTIONS, copy.deepcopy(contested)])
    assert (repeated["status"], repeated["duplicates_removed"], repeated["sample"]["completed"]) == ("success", 1, 3)
    assert [item["transaction_id"] for item in page_market(db)["claims"]].count(WIDE_ONE) == 1
    db = FakeSnapshotDB()
    conflicting, _ = run(db, AFTER_FIRST_WEEK_3, [*SEASON_TRANSACTIONS, {**copy.deepcopy(contested), "settings": {"waiver_bid": 60, "seq": 0}}])
    assert (conflicting["status"], conflicting["exit_code"], conflicting["completeness"], conflicting["conflicting_transaction_ids"]) == (
        "partial", 2, "CONTRADICTORY", [WIDE_ONE])
    blocked = page_market(db)
    assert (blocked["state"], blocked["season_summary"], blocked["blockers"]) == ("CONTRADICTORY", None, ["TRANSACTION_HISTORY_CONTRADICTORY"])


def test_refreshed_history_keeps_completed_failed_zero_missing_and_free_agent_populations_apart():
    db = FakeSnapshotDB()
    run(db, AFTER_FIRST_WEEK_3)
    market = page_market(db)
    summary = market["season_summary"]
    assert (summary["completed"], summary["failed"], summary["zero_bid_completed"], summary["missing_bids"], summary["free_agent_adds"]) == (3, 1, 1, 1, 2)
    # Completed bids are $6 and the verified $0; the failed $4 and the missing bid stay out, and a free-agent add has no bid.
    assert (summary["completed_bids"]["text"], summary["failed_bids"]["text"]) == ("$0–$6, median $3 (N=2)", "$4 (N=1, single observation)")
    assert (summary["contested"], summary["uncontested"], summary["contested_bids"]["text"], summary["uncontested_bids"]["text"]) == (
        1, 2, "$6 (N=1, single observation)", "$0 (N=1, single observation)")
    assert {item["transaction_id"] for item in market["claims"]} == {WIDE_ONE, "l1", "c2", "c-missing"}
    assert next(item for item in market["claims"] if item["transaction_id"] == "c-missing")["bid"] is None
    run(db, AFTER_FIRST_WEEK_3 + timedelta(hours=1))
    assert page_market(db)["season_summary"] == summary


def test_team_budgets_stay_live_and_the_refresh_never_reads_or_writes_them():
    db = FakeSnapshotDB()
    run(db, WEEK_2)
    live = rosters(used=(10, 20, 0))
    unreported = [*live[:2], {"roster_id": 3, "owner_id": "u3", "settings": {}}]

    def budgets(roster_list):
        return sorted((entry["roster_id"], entry["state"], entry["used"], entry["remaining"], entry["completed_bid_total"])
                      for entry in page_market(db, roster_list)["budget_context"]["teams"])
    before = budgets(live), budgets(unreported)
    _, sleeper = run(db, AFTER_FIRST_WEEK_3)
    after = budgets(live), budgets(unreported)
    # Stored completed bids grew (Roster 1: $6, then $15 with the open week), but every remaining budget is still Sleeper's own.
    assert [row[:4] for row in after[0]] == [row[:4] for row in before[0]] == [(1, "VERIFIED", 10, 90), (2, "VERIFIED", 20, 80), (3, "VERIFIED", 0, 100)]
    assert (before[0][0][4], after[0][0][4]) == (6, 15)
    assert (3, "UNAVAILABLE", None, None) in [row[:4] for row in after[1]]
    assert set(sleeper.calls) == {"league", 1, 2, 3}
    written = {re.match(r"(?:INSERT INTO|UPDATE) (\w+)", statement).group(1) for statement in db.statements if not statement.lstrip().upper().startswith("SELECT")}
    assert written == {"sleeper_api_snapshots", "sleeper_sync_runs"}


def test_the_manual_command_loads_the_env_makes_only_read_only_gets_and_maps_each_status_to_its_exit_code(monkeypatch, capsys):
    import config
    import dotenv
    import psycopg2

    sleeper, db, failing = Sleeper(AFTER_FIRST_WEEK_3), FakeSnapshotDB(), set()

    def http_get(url, timeout):
        path, response = url.removeprefix("https://api.sleeper.app/v1"), requests.Response()
        response.url = url
        if path == f"/league/{LEAGUE}":
            payload = sleeper.league_payload
        else:
            number = int(path.rsplit("/", 1)[1])
            assert path == f"/league/{LEAGUE}/transactions/{number}"
            if number in failing:
                response.status_code, response.reason = 503, "Service Unavailable"
                return response
            payload = sleeper.weeks.get(number, [])
        response.status_code, response._content = 200, json.dumps(payload).encode()
        return response

    def forbidden(*args, **kwargs):
        pytest.fail("the refresh attempted a request that is not a read-only GET")
    monkeypatch.setattr(requests, "get", http_get)
    for name in ("post", "put", "patch", "delete"):
        monkeypatch.setattr(requests, name, forbidden)
    # Under systemd nothing is exported: the league id must come from the repository .env that the command loads itself.
    monkeypatch.delenv("SLEEPER_LEAGUE_ID", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: monkeypatch.setenv("SLEEPER_LEAGUE_ID", LEAGUE) or True)
    monkeypatch.setattr(config.Config, "db_kwargs", staticmethod(lambda: {"host": "db.internal", "user": "fantasy-owner"}))
    monkeypatch.setattr(psycopg2, "connect", lambda **kwargs: db)
    outcomes = []
    for failing_week in (None, None, 2):
        failing.update({failing_week} - {None})
        code = main([])
        result = json.loads(capsys.readouterr().out)
        outcomes.append((code, result["status"], result["exit_code"], result["league_id"]))
    assert outcomes == [(0, "success", 0, LEAGUE), (0, "no_new_closed_week", 0, LEAGUE), (2, "partial", 2, LEAGUE)]
    assert week(result, 2)["http_status"] == 503 and len(db.rows) == 3

    rows = copy.deepcopy(db.rows)
    monkeypatch.setattr(psycopg2, "connect", forbidden)
    failing.clear()
    assert main(["--dry-run"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert (dry["status"], dry["dry_run"], dry["run_id"], dry["stored_weeks"], dry["completeness"]) == ("success", True, None, [], None)
    assert {entry["snapshot"] for entry in dry["weeks"]} == {"NOT_WRITTEN_DRY_RUN"} and db.rows == rows

    def refused(**kwargs):
        raise psycopg2.OperationalError('connection to server at "db.internal" failed: password authentication failed for user "fantasy-owner"')
    monkeypatch.setattr(psycopg2, "connect", refused)
    assert main([]) == 1
    output = capsys.readouterr().out
    assert json.loads(output)["error"] == "Database connection failed (OperationalError); nothing was fetched or written."
    assert "db.internal" not in output and "fantasy-owner" not in output
    usage = subprocess.run([sys.executable, str(ROOT / "refresh_sleeper_transactions.py"), "--help"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert usage.returncode == 0 and "--dry-run" in usage.stdout


# systemd units: the timer runs the same command after the weekly waiver run, outside the request path.

def test_the_service_runs_the_existing_refresh_command_with_the_repository_venv():
    service = unit(SERVICE)
    (workdir,) = values(service, "Service", "WorkingDirectory")
    reference = unit("opportunity-evidence-refresh.service")
    assert [workdir] == values(reference, "Service", "WorkingDirectory")
    (command,) = values(service, "Service", "ExecStart")
    assert command.split() == [f"{workdir}/venv/bin/python", f"{workdir}/refresh_sleeper_transactions.py"]
    assert values(reference, "Service", "ExecStart")[0].split()[0] == f"{workdir}/venv/bin/python"
    assert (ROOT / "refresh_sleeper_transactions.py").is_file() and refresh_module.main is main


def test_service_failure_is_visible_bounded_and_carries_no_credentials():
    service = unit(SERVICE)
    assert values(service, "Service", "Type") == ["oneshot"] and values(service, "Service", "TimeoutStartSec") == ["15min"]
    (command,) = values(service, "Service", "ExecStart")
    # A leading "-" would make systemd ignore a failed exit status; no other command, environment or exit-status override may run.
    assert not command.startswith(("-", "+", "!", "@", ":"))
    keys = {key for key, _ in service["Service"]}
    assert not keys & {"ExecStartPre", "ExecStartPost", "ExecStop", "ExecStopPost", "ExecReload", "SuccessExitStatus", "Restart", "Environment",
                       "EnvironmentFile", "User", "Group"}
    assert "Install" not in service
    text = (ROOT / "scheduler" / SERVICE).read_text(encoding="utf-8")
    assert not re.search(r"password|passwd|token|postgres(ql)?://|DB_[A-Z]+=|SLEEPER_LEAGUE_ID=", text, re.I)


# This league's weekly waiver run, from its Sleeper settings (daily_waivers 0, waiver_clear_days 2) and the stored 2026 transactions:
# processed Wednesday 00:10-00:12 Pacific, the first transaction of each new week appeared by 06:05, and a claim of the closed week can
# still process until two days after the run (as weekday, hour, minute).
LATEST_FIRST_NEW_WEEK_TRANSACTION, LAST_CLOSED_WEEK_CLAIM = (2, 6, 5), (4, 0, 12)


def test_the_timer_follows_the_weekly_waiver_run_with_a_same_day_retry_and_never_polls():
    calendars = values(unit(TIMER), "Timer", "OnCalendar")
    assert calendars == ["Wed *-*-* 06:30:00 America/Los_Angeles", "Wed *-*-* 18:30:00 America/Los_Angeles", "Fri *-*-* 06:30:00 America/Los_Angeles"]
    runs = []
    for calendar in calendars:
        day, dates, time, zone = calendar.split()
        hour, minute, _ = (int(part) for part in time.split(":"))
        assert (dates, zone) == ("*-*-*", "America/Los_Angeles")
        runs.append(({"Wed": 2, "Fri": 4}[day], hour, minute))
    primary, retry, closing = runs
    assert LATEST_FIRST_NEW_WEEK_TRANSACTION < primary < retry and retry[0] == primary[0] and closing > LAST_CLOSED_WEEK_CLAIM


def test_timer_persistence_is_explicit_and_it_triggers_only_the_refresh_service():
    timer = unit(TIMER)
    assert values(timer, "Timer", "Persistent") == ["true"] and values(timer, "Timer", "RandomizedDelaySec") == ["0"]
    assert values(timer, "Timer", "Unit") in ([], [SERVICE])
    assert values(timer, "Install", "WantedBy") == ["timers.target"]


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze is not installed")
def test_systemd_accepts_the_units_and_every_calendar():
    verify = subprocess.run(["systemd-analyze", "--user", "verify", str(ROOT / "scheduler" / SERVICE), str(ROOT / "scheduler" / TIMER)],
                            capture_output=True, text=True, timeout=120)
    assert (verify.returncode, verify.stdout.strip(), verify.stderr.strip()) == (0, "", "")
    for calendar in values(unit(TIMER), "Timer", "OnCalendar"):
        parsed = subprocess.run(["systemd-analyze", "calendar", calendar], capture_output=True, text=True, timeout=60)
        assert parsed.returncode == 0 and "Next elapse" in parsed.stdout


# GET /waivers stays read-only, and a refresh that closes a week changes market history but no waiver decision.

def test_viewing_waivers_never_runs_the_refresh_or_starts_a_process(monkeypatch):
    from tests.test_waiver_availability import render_w5_route

    def forbidden(*args, **kwargs):
        pytest.fail("viewing /waivers attempted to run the transaction refresh or start a process")
    for module, name in ((subprocess, "run"), (subprocess, "Popen"), (subprocess, "call"), (subprocess, "check_call"), (subprocess, "check_output"),
                         (os, "system"), (refresh_module, "main"), (refresh_module, "refresh_league_transactions")):
        monkeypatch.setattr(module, name, forbidden)
    response, captured = render_w5_route(monkeypatch)
    assert response.status_code == 200 and captured["waiver_market"]["state"] == "AVAILABLE"
    assert all(query.lstrip().upper().startswith("SELECT") for query in captured["executed_queries"])


def test_a_refresh_that_closes_a_week_changes_market_history_but_no_waiver_decision(monkeypatch):
    import tests.test_waiver_availability as availability

    transactions = [transaction for _, payload, *_ in availability.w5_market_rows() for transaction in payload]

    def controlled(leg):
        return {**availability.W5_LEAGUE, "settings": {**availability.W5_LEAGUE["settings"], "leg": leg}}
    db = FakeSnapshotDB()
    stored = []
    for when in (WEEK_2, AFTER_FIRST_WEEK_3):
        result, _ = run(db, when, transactions, league_id="controlled", league_payload=controlled)
        assert result["status"] == "success"
        stored.append([(row["week"], row["payload"], row["fetched_at"], row["league_id"], row["season"])
                       for row in read_transaction_history(db.cursor(), "controlled", SEASON)["rows"]])
    roles = availability.w6_role_reads()

    def snapshot(rows):
        # Copy every value right after its render: a later render reuses objects that an earlier captured context still points to.
        with monkeypatch.context() as patch:
            patch.setattr(availability, "w5_market_rows", lambda: rows)
            response, captured = availability.render_w6_route(patch, role=roles)
            html = response.get_data(as_text=True)
            market = captured["waiver_market"]
            text = (html[html.index('id="waiver-faab-market"'):html.index('id="waiver-player-lookup"')]
                    + "".join(re.findall(r'<p class="(?:move|outcome)-market">.*?</p>', html, re.S)))
            return copy.deepcopy({
                "decisions": availability.w6_decision_view(captured)[:-1], "roles": [move.get("role") for move in captured["waiver_decision"]["moves"]],
                "coverage": captured["waiver_role_coverage"],
                # The live balance is fetched on every render; only its retrieval time may differ.
                "faab_balance": {key: value for key, value in captured["faab_balance"].items() if key != "retrieved_at"},
                "budgets": [(team["roster_id"], team["used"], team["remaining"]) for team in market["budget_context"]["teams"]],
                "market": (market["state"], market["through_week"], market["recommendation_impact"]), "text": text})

    before, after = snapshot(stored[0]), snapshot(stored[1])
    assert (before["market"], after["market"]) == (("PARTIAL", 1, "INFORMATIONAL_ONLY"), ("AVAILABLE", 2, "INFORMATIONAL_ONLY"))
    for key in ("decisions", "roles", "coverage", "faab_balance", "budgets"):
        assert before[key] == after[key], key
    moves = before["decisions"][0]
    assert (moves[0]["decision"], moves[0]["add"]["player_id"], moves[0]["drop"]["player_id"]) == ("ADD_DROP", "s-vet", "s-bench")
    assert (before["roles"][0]["state"], before["roles"][0]["recommendation_impact"], before["decisions"][7]) == ("CURRENT", "INFORMATIONAL_ONLY", False)
    for view in (before, after):
        assert not availability.W5_PROHIBITED.search(view["text"])
