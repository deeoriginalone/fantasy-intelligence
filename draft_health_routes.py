from flask import Blueprint, jsonify, render_template

from auth import admin_required, csrf_required
from draft_readiness import (
    build_draft_readiness,
    ensure_reconciliation_table,
    record_reconciliation,
)


def create_draft_health_blueprint(db, league_id, season, signal_builder, health_builder):
    """Create read-only health endpoints plus an authenticated reconciliation writer."""
    bp = Blueprint("draft_health", __name__, url_prefix="/draft-health")

    def load(record=False):
        conn = db()
        cur = conn.cursor()
        try:
            signals = signal_builder(cur, league_id, season=season, user_slot=5)
            health = health_builder(cur)
            result = build_draft_readiness(cur, league_id, season, signals, health)
            if record:
                ensure_reconciliation_table(cur)
                record_reconciliation(
                    cur,
                    league_id,
                    signals.get("draft_id"),
                    signals.get("draft_status"),
                    result["draft_day"],
                )
                conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @bp.get("/")
    def home():
        return render_template("draft_health.html", readiness=load())

    @bp.get("/json")
    def data():
        return jsonify(load())

    @bp.post("/reconcile")
    @admin_required
    @csrf_required
    def reconcile():
        return jsonify(load(record=True))

    return bp
