"""Flask blueprint for Batch D Intelligence Operations."""
from flask import Blueprint, jsonify, request
from intelligence_readiness import calculate_readiness
from weekly_intelligence_report import build_weekly_report

def create_intelligence_operations_blueprint(get_db_connection):
    bp = Blueprint("intelligence_operations", __name__, url_prefix="/intelligence-operations")

    def query_all(sql, params=()):
        conn = get_db_connection(); cur = conn.cursor()
        try:
            cur.execute(sql, params)
            names = [d[0] for d in cur.description]
            return [dict(zip(names, row)) for row in cur.fetchall()]
        finally:
            cur.close(); conn.close()

    @bp.get("/health")
    def health():
        return jsonify({"status": "ok", "module": "batch_d_intelligence_operations"})

    @bp.get("/readiness")
    def readiness():
        season, week = request.args.get("season", type=int), request.args.get("week", type=int)
        if season is None or week is None:
            return jsonify({"error": "season and week are required"}), 400
        rows = query_all("SELECT component_name, component_score, blocker, warning FROM intelligence_readiness_components WHERE season=%s AND week=%s", (season, week))
        components = {r["component_name"]: float(r["component_score"]) for r in rows}
        blockers = [r["blocker"] for r in rows if r.get("blocker")]
        warnings = [r["warning"] for r in rows if r.get("warning")]
        return jsonify(calculate_readiness(components, blockers=blockers, warnings=warnings))

    @bp.get("/report")
    def report():
        season, week = request.args.get("season", type=int), request.args.get("week", type=int)
        if season is None or week is None:
            return jsonify({"error": "season and week are required"}), 400
        rows = query_all("SELECT model_pick, model_probability, crowd_pick, crowd_percentage, contrarian_edge, signal, confidence_points FROM pick_recommendations WHERE season=%s AND week=%s", (season, week))
        components = query_all("SELECT component_name, component_score, blocker, warning FROM intelligence_readiness_components WHERE season=%s AND week=%s", (season, week))
        readiness_result = calculate_readiness(
            {r["component_name"]: float(r["component_score"]) for r in components},
            blockers=[r["blocker"] for r in components if r.get("blocker")],
            warnings=[r["warning"] for r in components if r.get("warning")],
        )
        return jsonify(build_weekly_report(season=season, week=week, recommendations=rows, readiness=readiness_result))

    @bp.get("/audit")
    def audit():
        season, week = request.args.get("season", type=int), request.args.get("week", type=int)
        rows = query_all("SELECT * FROM recommendation_changes WHERE season=%s AND week=%s ORDER BY changed_at DESC", (season, week))
        return jsonify({"season": season, "week": week, "changes": rows})

    return bp
