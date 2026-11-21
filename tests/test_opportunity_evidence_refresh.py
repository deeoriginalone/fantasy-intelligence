"""Automated W6 opportunity-evidence refresh: the scheduled command's per-source outcome and exit contract, and its systemd units."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import refresh_opportunity_evidence as refresh_module
from refresh_opportunity_evidence import EXIT_CODES, main, refresh_opportunity_evidence

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "opportunity-evidence-refresh.service"
TIMER = "opportunity-evidence-refresh.timer"
ENV = {"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400", "SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "86400"}
TABLES = {"stats_player_week": "player_opportunity_evidence", "snap_counts": "snap_share_evidence"}
GAMES = (("KC", "DEN"), ("BUF", "MIA"))
NOW = datetime.now(timezone.utc)
SEVEN_HOURS_AGO = NOW - timedelta(hours=7)


def schedule(*, completed=4, current=5, final=()):
    """Weeks 1..current with every kickoff in the past; KC and DEN are on bye in Week 3. Only weeks through `completed`, plus the listed
    (week, home team) games, have a result in the automated schedule."""
    return [{"week": week, "home_team": home, "away_team": away, "game_time_utc": NOW - timedelta(days=7 * (current - week), hours=3),
             "result": "3" if week <= completed or (week, home) in final else None, "source": "automated:nflverse-schedules:games.csv.gz"}
            for week in range(1, current + 1) for home, away in GAMES if not (week == 3 and home == "KC")]


def table_rows(schedule_rows, *, through, retrieved, checksum, missing=()):
    """Stored coverage: one row per (week, team) that played a final game through `through`, except the `missing` pairs."""
    return {(row["week"], team): {"week": row["week"], "team": team, "retrieved_at": retrieved, "source_recorded_at": retrieved - timedelta(hours=1),
                                  "checksum": checksum}
            for row in schedule_rows if row["week"] <= through and row["result"] for team in (row["home_team"], row["away_team"])
            if (row["week"], team) not in missing}


class EvidenceDB:
    """A fake connection holding each source table in memory and serving only the SELECTs the refresh issues."""

    def __init__(self, schedule_rows, tables=None):
        self.schedule_rows = schedule_rows
        self.tables = {name: dict(rows) for name, rows in (tables or {}).items()}
        self.statements = []

    def cursor(self):
        return EvidenceCursor(self)

    def rollback(self):
        self.statements.append("ROLLBACK")


class EvidenceCursor:
    def __init__(self, db):
        self.db, self.result = db, []

    def execute(self, query, params=None):
        assert query.lstrip().upper().startswith("SELECT"), query
        self.db.statements.append(query)
        if "FROM nfl_schedule" in query:
            self.result = [tuple(row.get(key) for key in ("week", "home_team", "away_team", "result", "source")) for row in self.db.schedule_rows]
            return
        table = next(name for name in TABLES.values() if f"FROM {name}" in query)
        rows = list(self.db.tables.get(table, {}).values())
        if "GROUP BY week, team" in query:
            self.result = [(row["week"], row["team"], 1, row["retrieved_at"], row["source_recorded_at"]) for row in sorted(rows, key=lambda r: (r["week"], r["team"]))]
        elif "array_agg(DISTINCT checksum)" in query:
            def pick(function, field):
                return function((row[field] for row in rows), default=None)
            self.result = [(len(rows), pick(min, "week"), pick(max, "week"), pick(min, "retrieved_at"), pick(max, "retrieved_at"),
                            pick(max, "source_recorded_at"), sorted({row["checksum"] for row in rows}) or None)]
        else:
            raise AssertionError(query)

    def fetchall(self):
        return list(self.result)

    def fetchone(self):
        return self.result[0]

    def close(self):
        pass


def source_step(key, *, through=None, checksum="sha-new", fail=None, missing=()):
    """One source as the refresh sees it: acquisition returns provider evidence stamped with its own retrieval time, and publish replaces
    the batch's weeks in the fake table all at once (a failed publish writes nothing, like the real publishers)."""
    calls = []

    def run(season, through_week, environ):
        calls.append(("acquire", through_week))
        if fail == "download":
            raise OSError("<urlopen error timed out>")
        if fail == "parse":
            raise ValueError("NFLVERSE_OPPORTUNITY_SCHEMA_UNVERIFIED: ['targets']")
        last = through_week if through is None else through
        retrieved = datetime.now(timezone.utc)
        weeks = list(range(1, last + 1))
        evidence = {"weeks": weeks, "rows": [{}] * (4 * len(weeks)), "reconciliation": {"reconciled": True, "duplicate_player_week_count": 0},
                    "provenance": {"source_location": f"https://github.com/nflverse/nflverse-data/releases/download/{key}.csv", "version": f"{key}_2026",
                                   "checksum": checksum, "source_recorded_at": (retrieved - timedelta(hours=1)).isoformat(), "retrieved_at": retrieved.isoformat()}}

        def publish(connection, evidence):
            calls.append(("publish", tuple(evidence["weeks"])))
            if fail == "publication":
                raise RuntimeError("SIMULATED_TRANSACTION_FAILURE")
            table = connection.tables.setdefault(TABLES[key], {})
            kept = {pair: row for pair, row in table.items() if row["week"] not in evidence["weeks"]}
            table.clear()
            table.update(kept)
            table.update(table_rows(connection.schedule_rows, through=last, retrieved=retrieved, checksum=checksum, missing=missing))
            return len(evidence["rows"])
        return evidence, (lambda evidence: None), publish
    run.calls = calls
    return run


def stored_db(rows, *, through=4, retrieved=SEVEN_HOURS_AGO, checksum="sha-old"):
    return EvidenceDB(rows, {table: table_rows(rows, through=through, retrieved=retrieved, checksum=checksum) for table in TABLES.values()})


def run(db, steps, **kwargs):
    return refresh_opportunity_evidence(db, season=2026, environ=ENV, steps=tuple(steps), **kwargs)


def stamp(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


# Scheduled command: per-source outcome, exit contract, completed-week boundary and timestamps.

def test_a_scheduled_refresh_publishes_completed_weeks_and_reports_each_source_separately():
    rows = schedule()
    db = stored_db(rows)
    steps = {key: source_step(key) for key in TABLES}
    result = run(db, steps.items())
    assert (result["status"], result["exit_code"], result["through_week"]) == ("success", 0, 4)
    for key, step in steps.items():
        source = result["sources"][key]
        assert step.calls == [("acquire", 4), ("publish", (1, 2, 3, 4))]
        assert (source["state"], source["rows_published"], source["prior_evidence"]) == ("PUBLISHED", 16, "REPLACED")
        assert (source["acquired"]["source_update"], source["acquired"]["checksum"], source["acquired"]["weeks"]) == ("UPDATED", "sha-new", [1, 2, 3, 4])
        assert (source["stored_before"]["newest_retrieved_at"], source["stored_before"]["checksums"]) == (SEVEN_HOURS_AGO, ["sha-old"])
        stored = source["stored"]
        assert (stored["currency"], stored["completeness"], stored["verified_through_week"], stored["freshness_state"]) == ("CURRENT", "COMPLETE", 4, "FRESH")
        # retrieved_at is this run's own acquisition time and source_recorded_at the provider's; neither is copied or derived from the other.
        assert stamp(stored["retrieved_at"]) == stamp(source["acquired"]["retrieved_at"]) > SEVEN_HOURS_AGO
        assert stamp(stored["source_recorded_at"]) == stamp(source["acquired"]["source_recorded_at"]) < stamp(stored["retrieved_at"])
        # A bye is never stored as a zero-usage row; the completed-week check expects only teams that played.
        assert (3, "KC") not in db.tables[TABLES[key]] and (3, "BUF") in db.tables[TABLES[key]]
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in db.statements)


def test_an_unchanged_artifact_is_reacquired_never_copied_and_reported_as_no_source_update():
    rows = schedule()
    db = EvidenceDB(rows)
    first = run(db, [(key, source_step(key, checksum=f"sha-{key}")) for key in TABLES])
    assert first["status"] == "success" and {s["acquired"]["source_update"] for s in first["sources"].values()} == {"FIRST_PUBLICATION"}
    stored_first = copy.deepcopy(db.tables)
    second = run(db, [(key, source_step(key, checksum=f"sha-{key}")) for key in TABLES])
    assert (second["status"], second["exit_code"]) == ("no_source_update", 0)
    for key, source in second["sources"].items():
        assert source["acquired"]["source_update"] == "UNCHANGED" and source["stored"]["currency"] == "CURRENT"
        # The same rows, keyed by week and team, without duplicates; only the retrieval time moved, to the new acquisition.
        assert set(db.tables[TABLES[key]]) == set(stored_first[TABLES[key]])
        assert stamp(source["stored"]["retrieved_at"]) == stamp(source["acquired"]["retrieved_at"]) >= stamp(first["sources"][key]["acquired"]["retrieved_at"])


@pytest.mark.parametrize("through, missing", [(3, ()), (4, ((4, "BUF"), (4, "MIA")))], ids=["week-not-published", "late-game-not-published"])
def test_a_source_missing_a_completed_game_is_partial_and_never_current_however_fresh(through, missing):
    rows = schedule(completed=4)
    db = stored_db(rows, through=3, checksum="sha-week3")
    steps = {"stats_player_week": source_step("stats_player_week"), "snap_counts": source_step("snap_counts", through=through, checksum="sha-week3", missing=missing)}
    result = run(db, steps.items())
    snaps = result["sources"]["snap_counts"]
    assert snaps["state"] == "PUBLISHED" and snaps["stored"]["freshness_state"] == "FRESH"
    assert (snaps["stored"]["currency"], snaps["stored"]["completeness"], snaps["stored"]["verified_through_week"]) == ("NOT_CURRENT", "PARTIAL", 3)
    assert snaps["stored"]["blocker"] == "SNAP_COUNTS_PIPELINE_INCOMPLETE"
    assert result["sources"]["stats_player_week"]["stored"]["currency"] == "CURRENT"
    assert (result["status"], result["exit_code"]) == ("partial", 2)


@pytest.mark.parametrize("failing", list(TABLES))
@pytest.mark.parametrize("fail, stage", [("download", "acquisition"), ("parse", "acquisition"), ("publication", "publication")])
def test_a_failed_source_keeps_its_rows_and_retrieval_time_and_the_run_exits_nonzero(failing, fail, stage):
    rows = schedule()
    db = stored_db(rows)
    before = copy.deepcopy(db.tables)
    steps = {key: source_step(key, fail=fail if key == failing else None) for key in TABLES}
    result = run(db, steps.items())
    failed = result["sources"][failing]
    other = result["sources"][next(key for key in TABLES if key != failing)]
    assert (failed["state"], failed["stage"], failed["prior_evidence"]) == ("FAILED", stage, "RETAINED") and failed["error"]
    assert db.tables[TABLES[failing]] == before[TABLES[failing]]
    assert stamp(failed["stored"]["retrieved_at"]) == SEVEN_HOURS_AGO and failed["stored"]["currency"] == "CURRENT"
    assert other["state"] == "PUBLISHED" and other["stored"]["currency"] == "CURRENT"
    assert (result["status"], result["exit_code"]) == ("partial", 2)
    if fail != "publication":
        assert [call for call in steps[failing].calls if call[0] == "publish"] == []


def test_a_failed_run_never_renews_freshness_and_a_later_success_restores_current():
    rows = schedule()
    expired = NOW - timedelta(hours=30)
    db = stored_db(rows, retrieved=expired)
    before = copy.deepcopy(db.tables)
    failed = run(db, [(key, source_step(key, fail="download")) for key in TABLES])
    assert (failed["status"], failed["exit_code"]) == ("failed", 1) and db.tables == before
    for source in failed["sources"].values():
        assert (source["state"], source["prior_evidence"]) == ("FAILED", "RETAINED")
        assert (source["stored"]["currency"], source["stored"]["freshness_state"], stamp(source["stored"]["retrieved_at"])) == ("NOT_CURRENT", "STALE", expired)
    restored = run(db, [(key, source_step(key)) for key in TABLES])
    assert (restored["status"], restored["exit_code"]) == ("success", 0)
    assert {source["stored"]["currency"] for source in restored["sources"].values()} == {"CURRENT"}


def test_no_completed_week_is_a_safe_noop_that_fetches_and_writes_nothing():
    db = EvidenceDB(schedule(completed=0))
    step = source_step("stats_player_week")
    result = run(db, [("stats_player_week", step)])
    assert (result["status"], result["exit_code"], result["through_week"], result["sources"]) == ("no_completed_week", 0, None, {})
    assert step.calls == [] and all("FROM nfl_schedule" in statement for statement in db.statements)


@pytest.mark.parametrize("rows", [[], [{**row, "source": "csv:bootstrap"} for row in schedule()]], ids=["no-schedule", "not-automated"])
def test_without_an_automated_schedule_nothing_is_published_and_the_run_fails(rows):
    step = source_step("stats_player_week")
    result = run(EvidenceDB(rows), [("stats_player_week", step)])
    assert (result["status"], result["exit_code"], step.calls) == ("failed", 1, []) and "No automated nflverse schedule" in result["error"]


def test_the_completed_week_comes_from_schedule_results_not_the_clock():
    # Weeks 5 and 6 kicked off in the past; one Week 5 game is final. Only Week 4 is complete.
    rows = schedule(completed=4, current=6, final=((5, "KC"),))
    step = source_step("stats_player_week")
    result = run(EvidenceDB(rows), [("stats_player_week", step)])
    assert result["through_week"] == 4 and step.calls[0] == ("acquire", 4)
    late = source_step("snap_counts", through=5)
    rejected = run(EvidenceDB(rows), [("snap_counts", late)])
    assert (rejected["status"], rejected["sources"]["snap_counts"]["stage"]) == ("failed", "validation") and "after the completed Week 4" in rejected["sources"]["snap_counts"]["error"]
    assert [call for call in late.calls if call[0] == "publish"] == []


def test_a_dry_run_acquires_and_validates_but_writes_nothing():
    rows = schedule()
    db = stored_db(rows)
    before = copy.deepcopy(db.tables)
    steps = {key: source_step(key) for key in TABLES}
    result = run(db, steps.items(), dry_run=True)
    assert (result["status"], result["exit_code"]) == ("success", 0) and db.tables == before
    assert {(source["state"], source["prior_evidence"]) for source in result["sources"].values()} == {("DRY_RUN", "RETAINED")}
    assert all(call[0] == "acquire" for step in steps.values() for call in step.calls)


def test_unreadable_stored_state_is_reported_and_never_counted_as_current():
    rows = schedule()

    def unreadable(connection, season):
        raise RuntimeError("relation does not exist")

    def blocked(connection, season, through_week, schedule_rows, environ):
        raise RuntimeError("connection lost")

    db = stored_db(rows)
    result = run(db, [(key, source_step(key)) for key in TABLES], stored=unreadable, evaluate=blocked)
    assert result["stored_before_error"] == "RuntimeError: relation does not exist" and "ROLLBACK" in db.statements
    for source in result["sources"].values():
        assert source["acquired"]["source_update"] == "UNKNOWN" and source["stored"]["currency"] == "BLOCKED"
    assert (result["status"], result["exit_code"]) == ("partial", 2)
    broken = run(EvidenceDB(rows), [], schedule=unreadable)
    assert (broken["status"], broken["exit_code"]) == ("failed", 1) and broken["error"].startswith("Schedule: RuntimeError")


def test_the_manual_command_prints_one_json_result_and_maps_each_status_to_its_exit_code(monkeypatch, capsys):
    import dotenv
    import psycopg2

    class Connection:
        closed = False

        def set_session(self, **kwargs):
            self.session = kwargs

        def close(self):
            Connection.closed = True

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr(psycopg2, "connect", lambda **kwargs: Connection())
    for status, code in (("success", 0), ("no_source_update", 0), ("no_completed_week", 0), ("partial", 2), ("failed", 1)):
        assert EXIT_CODES.get(status, 1) == code
        monkeypatch.setattr(refresh_module, "refresh_opportunity_evidence",
                            lambda connection, *, season, dry_run, status=status: {"season": season, "status": status, "exit_code": EXIT_CODES.get(status, 1)})
        assert main(["--season", "2026"]) == code and Connection.closed
        assert json.loads(capsys.readouterr().out)["status"] == status

    def refused(**kwargs):
        raise psycopg2.OperationalError('connection to server at "db.internal" failed: password authentication failed for user "fantasy-owner"')

    monkeypatch.setattr(psycopg2, "connect", refused)
    assert main(["--season", "2026"]) == 1
    output = capsys.readouterr().out
    assert json.loads(output)["error"] == "Database connection failed (OperationalError); nothing was fetched or written."
    assert "fantasy-owner" not in output and "db.internal" not in output
    usage = subprocess.run([sys.executable, str(ROOT / "refresh_opportunity_evidence.py"), "--help"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert usage.returncode == 0 and "--dry-run" in usage.stdout


# systemd units: the timer runs the same command, outside the request path.

def unit(name):
    """Parse a repository systemd unit into {section: [(key, value), ...]}, keeping repeated keys and skipping comments."""
    sections, current = {}, None
    for raw in (ROOT / "scheduler" / name).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], [])
            continue
        key, _, value = line.partition("=")
        current.append((key.strip(), value.strip()))
    return sections


def values(sections, section, key):
    return [value for name, value in sections.get(section, []) if name == key]


def test_the_service_runs_the_existing_refresh_command_with_the_repository_venv():
    service = unit(SERVICE)
    (workdir,) = values(service, "Service", "WorkingDirectory")
    reference = unit("nflverse-schedule-refresh.service")
    assert [workdir] == values(reference, "Service", "WorkingDirectory")
    (command,) = values(service, "Service", "ExecStart")
    assert command.split() == [f"{workdir}/venv/bin/python", f"{workdir}/refresh_opportunity_evidence.py"]
    assert values(reference, "Service", "ExecStart")[0].split()[0] == f"{workdir}/venv/bin/python"
    assert (ROOT / "refresh_opportunity_evidence.py").is_file() and refresh_module.main is main


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
    assert not re.search(r"password|passwd|token|postgres(ql)?://|DB_[A-Z]+=", text, re.I)


def test_the_timer_runs_every_six_hours_after_the_schedule_refresh_inside_the_freshness_limit():
    calendars = values(unit(TIMER), "Timer", "OnCalendar")
    assert calendars == ["*-*-* 00,06,12,18:30:00 America/Los_Angeles"]
    assert values(unit("nflverse-schedule-refresh.timer"), "Timer", "OnCalendar") == ["*-*-* 00,06,12,18:00:00 America/Los_Angeles"]
    hours = [int(hour) for hour in calendars[0].split()[1].split(":")[0].split(",")]
    gaps = [(later - earlier) % 24 or 24 for earlier, later in zip(hours, hours[1:] + hours[:1])]
    limit_hours = int(ENV["OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS"]) // 3600
    # Four attempts in every 24-hour freshness window: stored evidence stays current through three consecutive failed attempts.
    assert max(gaps) == 6 and limit_hours // max(gaps) == 4


def test_timer_persistence_is_explicit_and_it_triggers_only_the_refresh_service():
    timer = unit(TIMER)
    assert values(timer, "Timer", "Persistent") == ["true"] and values(timer, "Timer", "RandomizedDelaySec") == ["0"]
    assert values(timer, "Timer", "Unit") in ([], [SERVICE])
    assert values(timer, "Install", "WantedBy") == ["timers.target"]


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze is not installed")
def test_systemd_accepts_the_units_and_the_calendar():
    verify = subprocess.run(["systemd-analyze", "--user", "verify", str(ROOT / "scheduler" / SERVICE), str(ROOT / "scheduler" / TIMER)],
                            capture_output=True, text=True, timeout=120)
    assert (verify.returncode, verify.stdout.strip(), verify.stderr.strip()) == (0, "", "")
    (calendar,) = values(unit(TIMER), "Timer", "OnCalendar")
    parsed = subprocess.run(["systemd-analyze", "calendar", calendar], capture_output=True, text=True, timeout=60)
    assert parsed.returncode == 0 and "Next elapse" in parsed.stdout


# GET /waivers stays read-only, and a refresh changes role currency but no waiver decision.

def test_viewing_waivers_never_runs_the_refresh_or_starts_a_process(monkeypatch):
    from tests.test_waiver_availability import render_w6_route

    def forbidden(*args, **kwargs):
        pytest.fail("viewing /waivers attempted to run the refresh or a process")
    for module, name in ((subprocess, "run"), (subprocess, "Popen"), (subprocess, "call"), (subprocess, "check_call"), (subprocess, "check_output"),
                         (os, "system"), (refresh_module, "refresh_opportunity_evidence"), (refresh_module, "main")):
        monkeypatch.setattr(module, name, forbidden)
    response, captured = render_w6_route(monkeypatch)
    assert response.status_code == 200 and captured["waiver_decision"]["moves"][0]["role"]["state"] == "CURRENT"
    assert all(query.lstrip().upper().startswith("SELECT") for query in captured["executed_queries"])


def test_a_refresh_that_makes_role_evidence_current_changes_no_waiver_decision(monkeypatch):
    from tests.test_waiver_availability import render_w6_route, w6_decision_view, w6_role_reads

    def snapshot(hours_since_retrieval):
        # Copy every value right after its render: a later render reuses objects that an earlier captured context still points to.
        _, captured = render_w6_route(monkeypatch, role=w6_role_reads(retrieved_hours_ago=hours_since_retrieval))
        move = captured["waiver_decision"]["moves"][0]
        return copy.deepcopy({"decisions": w6_decision_view(captured), "currency": captured["waiver_role_coverage"]["currency"],
                              "role": move["role"], "faab": move["faab"]})

    expired, refreshed = snapshot(30), snapshot(0)
    assert expired["decisions"] == refreshed["decisions"]
    assert (expired["currency"], refreshed["currency"]) == ("HISTORICAL", "CURRENT")
    assert (expired["role"]["state"], refreshed["role"]["state"]) == ("HISTORICAL_ONLY", "CURRENT")
    for view in (expired, refreshed):
        role = view["role"]
        assert (role["future_duration"]["state"], role["recommendation_impact"], role["decision_effect"]) == ("UNVERIFIED", "INFORMATIONAL_ONLY", "NONE")
        assert view["faab"] == {"state": "UNSUPPORTED", "label": "Advanced FAAB valuation is not yet supported."}
