"""Read-only operational health for Draft HQ outcome and calibration data."""
from __future__ import annotations

from datetime import datetime, timezone
from draft_outcome_tracker import accuracy_summary
from model_calibration import model_health


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def build_outcome_health(cur):
    """Build a read-only snapshot using the existing outcome schema."""
    cur.execute(
        """
        SELECT
            count(*) FILTER (WHERE actual_available IS NULL),
            count(*) FILTER (WHERE actual_available IS NOT NULL),
            min(created_at) FILTER (WHERE actual_available IS NULL),
            max(resolved_at) FILTER (WHERE actual_available IS NOT NULL)
        FROM draft_decision_outcomes
        """
    )
    row = cur.fetchone() or (0, 0, None, None)
    pending = int(row[0] or 0)
    resolved = int(row[1] or 0)
    accuracy = accuracy_summary(cur)
    calibration = model_health(cur)
    return {
        "status": "ATTENTION" if pending else "HEALTHY",
        "pending": pending,
        "resolved": resolved,
        "oldest_pending_at": _iso(row[2]),
        "latest_resolved_at": _iso(row[3]),
        "accuracy": accuracy,
        "calibration": calibration,
    }


def create_outcome_health_blueprint(get_db_connection):
    from flask import Blueprint, jsonify
    bp = Blueprint("draft_outcome_health", __name__, url_prefix="/draft-outcomes")

    @bp.get("/health")
    def health():
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            return jsonify(build_outcome_health(cur))
        finally:
            cur.close()
            conn.close()

    return bp
