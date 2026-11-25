"""Automated DynastyProcess ranking refresh: the scheduled command's status and failure contract, its systemd units, and the read-only
/waivers boundary.

The command only orchestrates services.dynastyprocess_rankings, so these tests drive it with controlled DynastyProcess releases (acquire()
stubbed) and controlled Sleeper NFL state and catalog readers; every freshness, week, identity and position outcome comes from the
unchanged evaluator.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import refresh_dynastyprocess_rankings as refresh_module
from refresh_dynastyprocess_rankings import CACHE_PATH, EXIT_CODES, main, refresh_dynastyprocess_rankings
from services import dynastyprocess_rankings

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "dynastyprocess-rankings-refresh.service"
TIMER = "dynastyprocess-rankings-refresh.timer"
NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
STATE = {"season": "2026", "week": 4, "season_type": "regular", "season_start_date": "2026-09-10"}
WEEK4_KICKOFF = datetime(2026, 10, 4, 17, tzinfo=timezone.utc)
WEEK5_KICKOFF = WEEK4_KICKOFF + timedelta(days=7)
OLD, NEW, LAGGING = "1" * 40, "2" * 40, "3" * 40
# (page, provider ID, Sleeper ID, crosswalk position, ECR): one player per supported position; the defense joins by its Sleeper team ID.
PLAYERS = (("qb", "fp-qb", "s-qb", "QB", "4"), ("ppr-rb", "fp-rb", "s-rb", "RB", "11"), ("ppr-wr", "fp-wr", "s-wr", "WR", "12.5"),
           ("ppr-te", "fp-te", "s-te", "TE", "7"), ("k", "fp-k", "s-k", "PK", "3"), ("dst", "fp-def", None, None, "2"))
CATALOG = {**{sleeper: {"full_name": f"Player {provider}", "position": position.replace("PK", "K"), "team": "KC", "status": "Active"}
              for _, provider, sleeper, position, _ in PLAYERS if sleeper},
           "KC": {"team": "KC", "position": "DEF"}}
EXPECTED_RANKS = {"s-qb": ("QB", 4.0, "PUBLISHED_PROVIDER_CROSSWALK"), "s-rb": ("RB", 11.0, "PUBLISHED_PROVIDER_CROSSWALK"),
                  "s-wr": ("WR", 12.5, "PUBLISHED_PROVIDER_CROSSWALK"), "s-te": ("TE", 7.0, "PUBLISHED_PROVIDER_CROSSWALK"),
                  "s-k": ("K", 3.0, "PUBLISHED_PROVIDER_CROSSWALK"), "KC": ("DEF", 2.0, "EXACT_SLEEPER_TEAM_ID")}


def release(version, *, scrape_date="2026-10-03", kickoff=WEEK4_KICKOFF, ros_date="2026-10-02", skip_pages=()):
    """One DynastyProcess commit in acquire()'s shape. Beside one player per supported position, the weekly file carries a provider ID
    missing from the crosswalk and a crosswalk position conflict, which the evaluator never ranks."""
    identities = [{"fantasypros_id": provider, "sleeper_id": sleeper, "position": position} for _, provider, sleeper, position, _ in PLAYERS if sleeper]
    identities.append({"fantasypros_id": "fp-conflict", "sleeper_id": "s-conflict", "position": "RB"})
    base = {"team": "KC", "scrape_date": scrape_date, "player_game_kickoff_ts": str(kickoff.timestamp())}
    weekly = [{**base, "page": page, "fantasypros_id": provider, "player_name": f"Player {provider}", "ecr": ecr}
              for page, provider, _, _, ecr in PLAYERS if page not in skip_pages]
    weekly += [{**base, "page": "ppr-wr", "fantasypros_id": provider, "player_name": name, "ecr": "30"}
               for provider, name in (("fp-unlinked", "Unlinked Receiver"), ("fp-conflict", "Conflicting Receiver"))]
    ros = [{"fp_page": f"/nfl/rankings/ros-{page}.php", "id": provider, "player": f"Player {provider}", "team": "KC", "ecr": ecr, "scrape_date": ros_date}
           for page, provider, _, _, ecr in PLAYERS]
    artifacts = {name: {"rows": rows, "url": f"https://raw.githubusercontent.com/DynastyProcess/data/{version}/files/{name}",
                        "checksum": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()}
                 for name, rows in (("db_playerids.csv", identities), ("fp_latest_weekly.csv", weekly), ("db_fpecr_latest.csv", ros))}
    return {"version": version, "artifacts": artifacts, "source": dynastyprocess_rankings.SOURCE}


class Upstream:
    """Stands in for acquire(): returns the current release, or raises it when it is an exception, and counts every acquisition."""

    def __init__(self):
        self.release, self.calls = None, 0

    def __call__(self, fetch=None):
        self.calls += 1
        if isinstance(self.release, Exception):
            raise self.release
        return copy.deepcopy(self.release)


@pytest.fixture
def upstream(monkeypatch):
    source = Upstream()
    monkeypatch.setattr(dynastyprocess_rankings, "acquire", source)
    return source


def run(path, *, at=NOW, state=STATE, catalog=CATALOG):
    read_catalog = catalog if callable(catalog) else (lambda: copy.deepcopy(catalog))
    return refresh_dynastyprocess_rankings(path, now=at, read_nfl_state=lambda: dict(state), read_catalog=read_catalog)


def published_ranks(path, *, at=NOW, state=STATE):
    """The current-week ranks GET /waivers would read from the published cache."""
    return dynastyprocess_rankings.read_cached_rankings(path, state, now=at, sleeper_catalog=copy.deepcopy(CATALOG))["horizons"]["this_week"]["ranks"]


# The command: publication, freshness, failure retention and week rollover.

def test_a_scheduled_refresh_publishes_the_newer_release_for_every_position_and_reports_both_horizons(tmp_path, upstream):
    path = tmp_path / "instance" / "dynastyprocess-rankings.json"
    upstream.release = release(OLD, scrape_date="2026-10-01", ros_date="2026-09-25")
    assert run(path, at=NOW - timedelta(days=2))["status"] == "success"
    upstream.release = release(NEW)

    result = run(path)

    assert (result["status"], result["exit_code"], result["blockers"], result["warnings"]) == ("success", 0, [], [])
    assert (result["source_repository"], result["source_commit"], result["previous_source_commit"], result["source_changed"]) == (
        "DynastyProcess/data", NEW, OLD, True)
    assert (result["season"], result["season_type"], result["week"], result["scope"]) == (2026, "regular", 4, "2026:regular:4")
    assert result["last_attempt"] == result["last_successful_refresh"] == NOW.isoformat() and result["refresh_error"] is None
    week, ros = result["current_week"], result["rest_of_season"]
    assert (week["source_date"], week["previous_source_date"], week["freshness_state"], week["threshold_seconds"]) == ("2026-10-03", "2026-10-01", "FRESH", 172800)
    assert (week["published_rank_count"], week["supported_source_row_count"], week["artifact_changed"]) == (6, 8, True)
    assert week["position_counts"] == {"QB": 1, "RB": 1, "WR": 1, "TE": 1, "K": 1, "DEF": 1}
    # Identity is the evaluator's: an uncrosswalked provider ID and a crosswalk position conflict stay unranked.
    assert week["rejections"] == {"POSITION_CONFLICT": 1, "PROVIDER_ID_ABSENT_FROM_CROSSWALK": 1}
    assert (ros["source_date"], ros["freshness_state"], ros["published_rank_count"], ros["threshold_seconds"]) == ("2026-10-02", "FRESH", 6, 604800)
    ranks = published_ranks(path)
    assert {player_id: (row["position"], row["ecr"], row["identity_method"]) for player_id, row in ranks.items()} == EXPECTED_RANKS
    assert {(row["season"], row["week"], row["scoring"], row["source_date"]) for row in ranks.values()} == {(2026, 4, "PPR", "2026-10-03")}


def test_an_unchanged_release_is_reacquired_inside_the_six_hour_guard_and_reported_as_no_source_update(tmp_path, upstream):
    path = tmp_path / "rankings.json"
    upstream.release = release(NEW)
    assert run(path)["status"] == "success"
    later = NOW + timedelta(hours=1)

    result = run(path, at=later)

    # The page's on-use guard would reuse a one-hour-old attempt; the scheduled run always reacquires.
    assert upstream.calls == 2
    assert (result["status"], result["exit_code"], result["source_changed"], result["source_commit"], result["previous_source_commit"]) == (
        "no_source_update", 0, False, NEW, NEW)
    assert (result["last_successful_refresh"], result["current_week"]["freshness_state"], result["current_week"]["artifact_changed"]) == (
        later.isoformat(), "FRESH", False)
    # The on-use path My Team keeps still honours the guard.
    dynastyprocess_rankings.refresh_rankings(path, STATE, now=later + timedelta(minutes=5))
    assert upstream.calls == 2


def test_reacquiring_an_old_scrape_renews_only_retrieval_and_stays_partial_until_a_newer_scrape_restores_ranks(tmp_path, upstream):
    path = tmp_path / "rankings.json"
    upstream.release = release(OLD, scrape_date="2026-10-01")
    for minutes in (0, 1):
        at = NOW + timedelta(minutes=minutes)
        result = run(path, at=at)
        week = result["current_week"]
        assert (result["status"], result["exit_code"], result["blockers"]) == ("partial", 2, ["CURRENT_WEEK_SOURCE_STALE"])
        assert (result["last_successful_refresh"], result["refresh_error"]) == (at.isoformat(), None)
        assert (week["source_date"], week["freshness_state"], week["published_rank_count"]) == ("2026-10-01", "STALE", 0)
        assert week["rejections"] == {"Source is stale or future-dated": 8}
    assert result["source_changed"] is False and not published_ranks(path, at=at)

    upstream.release = release(NEW)
    restored = run(path, at=NOW + timedelta(minutes=2))
    assert (restored["status"], restored["current_week"]["source_date"], restored["current_week"]["published_rank_count"]) == ("success", "2026-10-03", 6)


def test_a_future_dated_current_week_source_fails_closed(tmp_path, upstream):
    upstream.release = release(NEW, scrape_date="2026-10-04")
    result = run(tmp_path / "rankings.json")
    assert (result["status"], result["exit_code"], result["blockers"]) == ("failed", 1, ["CURRENT_WEEK_SOURCE_FUTURE_DATED"])
    assert (result["current_week"]["freshness_state"], result["current_week"]["published_rank_count"]) == ("FUTURE_DATED", 0)


def test_a_failed_acquisition_keeps_the_previous_release_and_never_renews_its_freshness(tmp_path, upstream):
    path = tmp_path / "rankings.json"
    upstream.release = release(NEW)
    run(path)
    before = json.loads(path.read_text())
    upstream.release = ConnectionError("GitHub unavailable")
    later = NOW + timedelta(hours=6)

    result = run(path, at=later)

    assert (result["status"], result["exit_code"], result["blockers"]) == ("failed", 1, ["SOURCE_ACQUISITION_FAILED"])
    assert (result["refresh_error"], result["last_attempt"], result["last_successful_refresh"]) == ("Ranking refresh failed: ConnectionError", later.isoformat(), NOW.isoformat())
    assert (result["source_commit"], result["source_changed"], result["current_week"]["source_date"]) == (NEW, None, "2026-10-03")
    after = json.loads(path.read_text())
    assert (after["artifacts"], after["version"], after["last_successful_refresh"]) == (before["artifacts"], NEW, NOW.isoformat())
    # Past 48 hours from its scrape date the retained release is stale; repeated failures never make it current.
    expired = run(path, at=datetime(2026, 10, 5, 0, 0, 1, tzinfo=timezone.utc))
    assert expired["blockers"] == ["SOURCE_ACQUISITION_FAILED", "CURRENT_WEEK_SOURCE_STALE"]
    assert expired["current_week"]["published_rank_count"] == 0 and json.loads(path.read_text())["artifacts"] == before["artifacts"]


def test_a_failed_publication_leaves_the_previous_cache_byte_identical(tmp_path, upstream, monkeypatch):
    path = tmp_path / "rankings.json"
    upstream.release = release(OLD)
    run(path)
    original = path.read_bytes()

    def refuse(source, target):
        raise OSError("No space left on device")

    monkeypatch.setattr(dynastyprocess_rankings, "os", SimpleNamespace(replace=refuse))
    upstream.release = release(NEW)
    result = run(path, at=NOW + timedelta(hours=6))

    assert (result["status"], result["exit_code"], result["blockers"]) == ("failed", 1, ["CACHE_PUBLICATION_FAILED"])
    assert (result["refresh_error"], result["source_commit"], result["last_successful_refresh"]) == ("Ranking cache unavailable", OLD, NOW.isoformat())
    assert path.read_bytes() == original


def test_last_weeks_release_never_ranks_the_new_week_until_the_new_weeks_release_is_acquired(tmp_path, upstream):
    path = tmp_path / "rankings.json"
    upstream.release = release(OLD)
    assert run(path)["current_week"]["published_rank_count"] == 6
    week5, tuesday = {**STATE, "week": 5}, datetime(2026, 10, 6, 15, tzinfo=timezone.utc)
    # Upstream has scraped again, but its weekly file still lists Week 4 games.
    upstream.release = release(LAGGING, scrape_date="2026-10-06")

    lagging = run(path, at=tuesday, state=week5)

    assert (lagging["status"], lagging["exit_code"], lagging["week"], lagging["scope"]) == ("partial", 2, 5, "2026:regular:5")
    assert lagging["blockers"] == ["CURRENT_WEEK_RANKS_UNAVAILABLE"] and json.loads(path.read_text())["scope"] == "2026:regular:5"
    assert (lagging["current_week"]["freshness_state"], lagging["current_week"]["published_rank_count"]) == ("FRESH", 0)
    assert lagging["current_week"]["rejections"] == {"Ranking belongs to another NFL week": 8}

    upstream.release = release(NEW, scrape_date="2026-10-06", kickoff=WEEK5_KICKOFF)
    current = run(path, at=tuesday + timedelta(hours=6), state=week5)
    assert (current["status"], current["current_week"]["published_rank_count"]) == ("success", 6)
    assert {row["week"] for row in published_ranks(path, at=tuesday + timedelta(hours=6), state=week5).values()} == {5}


def test_a_release_for_a_later_week_cannot_rank_the_current_week(tmp_path, upstream):
    upstream.release = release(NEW, kickoff=WEEK5_KICKOFF)
    result = run(tmp_path / "rankings.json")
    assert (result["status"], result["blockers"], result["current_week"]["published_rank_count"]) == ("partial", ["CURRENT_WEEK_RANKS_UNAVAILABLE"], 0)
    assert result["current_week"]["rejections"] == {"Ranking belongs to another NFL week": 8}


@pytest.mark.parametrize("state", [{**STATE, "season_type": "post"}, {**STATE, "week": 19}, {**STATE, "season": "2025"}])
def test_an_nfl_week_the_ranking_service_cannot_verify_fails_without_ranking(tmp_path, upstream, state):
    upstream.release = release(NEW)
    result = run(tmp_path / "rankings.json", state=state)
    assert (result["status"], result["exit_code"], result["current_week"]["published_rank_count"]) == ("failed", 1, 0)
    assert result["blockers"][0] == "NFL_WEEK_UNVERIFIED"


def test_an_unreadable_nfl_state_fails_before_touching_the_cache(tmp_path, upstream):
    path = tmp_path / "rankings.json"
    upstream.release = release(OLD)
    run(path)
    original, acquisitions = path.read_bytes(), upstream.calls

    def unavailable():
        raise RuntimeError("Sleeper state request failed")

    result = refresh_dynastyprocess_rankings(path, now=NOW + timedelta(hours=6), read_nfl_state=unavailable, read_catalog=lambda: dict(CATALOG))
    assert (result["status"], result["exit_code"], result["blockers"]) == ("failed", 1, ["NFL_STATE_UNAVAILABLE"])
    assert path.read_bytes() == original and upstream.calls == acquisitions


def _catalog_unavailable():
    raise ConnectionError("Sleeper catalog request failed")


@pytest.mark.parametrize("skip_pages, catalog, blockers, missing", [
    (("k",), CATALOG, ["CURRENT_WEEK_POSITION_COVERAGE_INCOMPLETE"], ["K"]),
    ((), _catalog_unavailable, ["SLEEPER_CATALOG_UNAVAILABLE", "CURRENT_WEEK_POSITION_COVERAGE_INCOMPLETE"], ["DEF"]),
])
def test_a_supported_position_without_published_ranks_is_partial(tmp_path, upstream, skip_pages, catalog, blockers, missing):
    upstream.release = release(NEW, skip_pages=skip_pages)
    result = run(tmp_path / "rankings.json", catalog=catalog)
    assert (result["status"], result["exit_code"], result["blockers"], result["current_week"]["missing_positions"]) == ("partial", 2, blockers, missing)


def test_the_manual_command_prints_one_json_result_without_credentials_and_maps_each_status_to_its_exit_code(tmp_path, upstream, monkeypatch, capsys):
    secrets = {"DB_PASSWORD": "pw-ranking-secret", "ADMIN_TOKEN": "token-ranking-secret", "FLASK_SECRET_KEY": "flask-ranking-secret"}
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    path, real, used, readers = tmp_path / "instance" / "dynastyprocess-rankings.json", refresh_dynastyprocess_rankings, [], {"state": lambda: dict(STATE)}

    def at_now(cache_path):
        used.append(cache_path)
        return real(cache_path, now=NOW, read_nfl_state=readers["state"], read_catalog=lambda: copy.deepcopy(CATALOG))

    monkeypatch.setattr(refresh_module, "CACHE_PATH", path)
    monkeypatch.setattr(refresh_module, "refresh_dynastyprocess_rankings", at_now)
    upstream.release = release(NEW)
    assert main([]) == 0 and used == [path]
    output = capsys.readouterr().out
    result = json.loads(output)
    assert (result["status"], result["source_commit"], result["current_week"]["source_date"], result["rest_of_season"]["source_date"]) == (
        "success", NEW, "2026-10-03", "2026-10-02")

    def leaky():
        raise RuntimeError(f"GET https://api.sleeper.app/v1/state/nfl?token={secrets['ADMIN_TOKEN']} failed")

    readers["state"] = leaky
    assert main([]) == 1
    failure_output = capsys.readouterr().out
    failure = json.loads(failure_output)
    assert (failure["status"], failure["blockers"]) == ("failed", ["NFL_STATE_UNAVAILABLE"])
    assert failure["error"] == "Sleeper NFL state could not be read (RuntimeError); the ranking cache was not changed."
    assert not any(secret in output + failure_output for secret in secrets.values())
    assert [EXIT_CODES.get(status, 1) for status in ("success", "no_source_update", "partial", "failed")] == [0, 0, 2, 1]
    usage = subprocess.run([sys.executable, str(ROOT / "refresh_dynastyprocess_rankings.py"), "--help"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert usage.returncode == 0 and usage.stdout.startswith("usage: refresh_dynastyprocess_rankings.py")


def test_the_command_publishes_the_cache_file_the_routes_read():
    from flask import Flask

    # app.py builds its app with Flask(__name__); the routes read current_app.instance_path + "/dynastyprocess-rankings.json".
    assert CACHE_PATH == Path(Flask("app").instance_path) / "dynastyprocess-rankings.json"


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


def test_the_service_runs_the_refresh_command_once_from_the_repository_venv():
    service = unit(SERVICE)
    (workdir,) = values(service, "Service", "WorkingDirectory")
    assert [workdir] == values(unit("opportunity-evidence-refresh.service"), "Service", "WorkingDirectory")
    assert values(service, "Service", "Type") == ["oneshot"]
    (command,) = values(service, "Service", "ExecStart")
    assert command.split() == [f"{workdir}/venv/bin/python", f"{workdir}/refresh_dynastyprocess_rankings.py"]
    assert (ROOT / "refresh_dynastyprocess_rankings.py").is_file() and refresh_module.main is main


def test_service_failure_is_visible_bounded_and_the_units_carry_no_credentials():
    service = unit(SERVICE)
    assert values(service, "Service", "TimeoutStartSec") == ["10min"]
    (command,) = values(service, "Service", "ExecStart")
    # A leading "-" would make systemd ignore a failed exit status; no other command, environment or exit-status override may run.
    assert not command.startswith(("-", "+", "!", "@", ":"))
    keys = {key for key, _ in service["Service"]}
    assert not keys & {"ExecStartPre", "ExecStartPost", "ExecStop", "ExecStopPost", "ExecReload", "SuccessExitStatus", "Restart", "Environment",
                       "EnvironmentFile", "User", "Group"}
    assert "Install" not in service
    for name in (SERVICE, TIMER):
        assert not re.search(r"password|passwd|token|secret|postgres(ql)?://|DB_[A-Z]+=", (ROOT / "scheduler" / name).read_text(encoding="utf-8"), re.I)


def test_the_timer_gives_eight_attempts_in_every_48_hour_window_and_a_run_before_the_utc_date_rollover():
    (calendar,) = values(unit(TIMER), "Timer", "OnCalendar")
    assert calendar == "*-*-* 05,11,17,23:40:00 UTC"
    hours, minute, _ = calendar.split()[1].split(":")
    runs = sorted(int(hour) * 60 + int(minute) for hour in hours.split(","))
    gaps = [(later - earlier) % 1440 or 1440 for earlier, later in zip(runs, runs[1:] + runs[:1])]
    assert max(gaps) == 360 and dynastyprocess_rankings.MAX_AGE["this_week"] // 60 // max(gaps) == 8
    # The last run of each UTC day follows the latest observed evening scrape (23:17 UTC) and precedes the midnight-UTC date rollover.
    assert 23 * 60 + 17 < runs[-1] < 24 * 60


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


# GET /waivers stays read-only: it reads the published cache and never acquires, refreshes or starts the refresh.

def test_viewing_waivers_reads_the_published_cache_and_never_acquires_refreshes_or_starts_a_process(tmp_path, upstream, monkeypatch):
    import owner_operations
    from tests.test_waiver_availability import render_waiver_route

    path = tmp_path / "rankings.json"
    upstream.release = release(NEW)
    run(path)
    published, modified = path.read_bytes(), path.stat().st_mtime_ns
    real_read, reads = dynastyprocess_rankings.read_cached_rankings, []

    def read_published(rankings_path, nfl_state, **kwargs):
        reads.append(str(rankings_path))
        return real_read(path, STATE, now=NOW, sleeper_catalog=copy.deepcopy(CATALOG))

    def forbidden(*args, **kwargs):
        pytest.fail("viewing /waivers attempted to acquire or refresh rankings or to start a process")

    monkeypatch.setattr(owner_operations, "get_nfl_state", lambda: dict(STATE))
    monkeypatch.setattr(owner_operations, "read_cached_rankings", read_published)
    for module, name in ((dynastyprocess_rankings, "acquire"), (dynastyprocess_rankings, "refresh"), (dynastyprocess_rankings, "refresh_rankings"),
                         (owner_operations, "refresh_rankings"), (refresh_module, "refresh_dynastyprocess_rankings"), (refresh_module, "main"),
                         (subprocess, "run"), (subprocess, "Popen"), (subprocess, "call"), (subprocess, "check_call"), (subprocess, "check_output"),
                         (os, "system")):
        monkeypatch.setattr(module, name, forbidden)

    response, _ = render_waiver_route(monkeypatch, testing=False)

    assert response.status_code == 200 and len(reads) == 1 and reads[0].endswith("/dynastyprocess-rankings.json")
    assert f"Last successful refresh:</strong> {NOW.isoformat()}" in response.get_data(as_text=True)
    assert (path.read_bytes(), path.stat().st_mtime_ns) == (published, modified)
