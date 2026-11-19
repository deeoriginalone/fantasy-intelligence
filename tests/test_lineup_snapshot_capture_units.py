from pathlib import Path

from flask import Flask

import owner_operations

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "lineup-snapshot-capture.service"
TIMER = "lineup-snapshot-capture.timer"


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


def test_service_runs_the_existing_capture_command_from_the_repository_venv():
    service = unit(SERVICE)
    (workdir,) = values(service, "Service", "WorkingDirectory")
    assert [workdir] == values(unit("nflverse-schedule-refresh.service"), "Service", "WorkingDirectory")
    (command,) = values(service, "Service", "ExecStart")
    assert command.split() == [f"{workdir}/venv/bin/flask", "--app", "app", "owner_ops", "capture-lineup-snapshots"]
    app = Flask(__name__)
    app.register_blueprint(owner_operations.create_owner_operations_blueprint(*[lambda *args, **kwargs: None] * 6))
    assert "capture-lineup-snapshots" in app.test_cli_runner().invoke(args=["owner_ops", "--help"]).output


def test_service_failure_is_visible_and_the_unit_runs_nothing_else():
    service = unit(SERVICE)
    assert values(service, "Service", "Type") == ["oneshot"]
    (command,) = values(service, "Service", "ExecStart")
    # A leading "-" would make systemd ignore a failed exit status; no other command or exit-status override may run.
    assert not command.startswith(("-", "+", "!", "@", ":"))
    keys = {key for key, _ in service["Service"]}
    assert not keys & {"ExecStartPre", "ExecStartPost", "ExecStop", "ExecStopPost", "ExecReload", "SuccessExitStatus", "Restart"}


def test_timer_runs_before_the_weekly_kickoff_windows_in_pacific_time():
    timer = unit(TIMER)
    calendars = values(timer, "Timer", "OnCalendar")
    assert calendars and all(entry.endswith(" America/Los_Angeles") for entry in calendars)
    weekly = {entry.split()[0]: entry.split()[2] for entry in calendars if not entry[0].isdigit()}
    assert weekly == {"Thu": "13:00:00", "Sun": "09:00:00", "Mon": "13:00:00"}
    assert sorted(entry for entry in calendars if entry[0].isdigit()) == [
        "2026-11-25 15:00:00 America/Los_Angeles", "2026-11-26 08:00:00 America/Los_Angeles"]


def test_timer_persistence_is_explicit_and_it_triggers_only_the_capture_service():
    timer = unit(TIMER)
    assert values(timer, "Timer", "Persistent") == ["true"] and values(timer, "Timer", "RandomizedDelaySec") == ["0"]
    assert values(timer, "Timer", "Unit") in ([], [SERVICE])
    assert values(timer, "Install", "WantedBy") == ["timers.target"]
