from datetime import datetime, timezone

from draft_outcome_health import build_outcome_health
from draft_outcome_tracker import accuracy_summary
from model_calibration import DEFAULT_WEIGHTS, MIN_SAMPLES, calibrated_weights, calibration_metrics


class Cursor:
    def __init__(self, fetchone_rows=None, fetchall_rows=None):
        self.fetchone_rows = list(fetchone_rows or [])
        self.fetchall_rows = list(fetchall_rows or [])
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.fetchone_rows.pop(0)

    def fetchall(self):
        return self.fetchall_rows.pop(0)


def test_calibration_metrics_known_values():
    cur = Cursor(fetchall_rows=[[(80, 70, 60, True), (20, 30, 40, False)]])
    metrics = calibration_metrics(cur)
    assert metrics["monte_carlo"]["samples"] == 2
    assert metrics["opponent"]["accuracy"] == 100.0
    assert metrics["survival"]["brier"] == 0.16


def test_calibration_stays_inactive_below_threshold():
    rows = [(80, 70, 60, True)] * (MIN_SAMPLES - 1)
    result = calibrated_weights(Cursor(fetchall_rows=[rows]))
    assert result["active"] is False
    assert result["weights"] == DEFAULT_WEIGHTS


def test_calibration_weights_are_bounded_and_normalized():
    rows = [(95, 55, 51, True)] * MIN_SAMPLES
    result = calibrated_weights(Cursor(fetchall_rows=[rows]))
    assert result["active"] is True
    assert abs(sum(result["weights"].values()) - 1.0) <= 0.002
    assert all(0.10 <= value <= 0.70 for value in result["weights"].values())


def test_accuracy_summary_reports_models_and_recent_rows():
    resolved = [("DRAFT NOW", 80, 70, 60, 90, True), ("WAIT", 20, 30, 40, 10, False)]
    recent = [(1, "Player A", "DRAFT NOW", 75, 80, True, "created", "resolved")]
    result = accuracy_summary(Cursor(fetchall_rows=[resolved, recent]))
    assert result["resolved"] == 2
    assert result["models"]["reconciled"]["accuracy"] == 100.0
    assert result["recent"][0]["player"] == "Player A"


def test_outcome_health_combines_counts_accuracy_and_calibration():
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    summary_rows = [[("DRAFT NOW", 80, 70, 60, 90, True)], []]
    calibration_rows = [[(80, 70, 60, True)]]
    cur = Cursor(
        fetchone_rows=[(1, 3, now, now)],
        fetchall_rows=summary_rows + calibration_rows,
    )
    result = build_outcome_health(cur)
    assert result["status"] == "ATTENTION"
    assert result["pending"] == 1
    assert result["resolved"] == 3
    assert result["oldest_pending_at"].startswith("2026-08-31")
    assert result["accuracy"]["resolved"] == 1
    assert result["calibration"]["active"] is False
