from flask import Blueprint, current_app, jsonify, request
from sleeper_sync import sync_sleeper_data

def create_sleeper_api_blueprint(get_db_connection):
    bp=Blueprint("sleeper_api",__name__,url_prefix="/sleeper-api")
    @bp.get("/status")
    def status():
        conn=get_db_connection(); cur=conn.cursor()
        cur.execute("SELECT id,league_id,season,week,status,resources,error_message,started_at,completed_at FROM sleeper_sync_runs ORDER BY id DESC LIMIT 10")
        cols=[d[0] for d in cur.description]; rows=[dict(zip(cols,r)) for r in cur.fetchall()]; cur.close(); conn.close()
        return jsonify(rows)
    @bp.post("/sync")
    def sync():
        body=request.get_json(silent=True) or request.form
        league_id=body.get("league_id") or current_app.config.get("SLEEPER_LEAGUE_ID")
        season=int(body.get("season") or current_app.config.get("FANTASY_SEASON",2026))
        week=int(body.get("week") or 1)
        if not league_id: return jsonify(error="league_id is required"),400
        return jsonify(sync_sleeper_data(get_db_connection,league_id,season,week,str(body.get("include_brackets","")).lower() in {"1","true","yes"}))
    @bp.get("/latest/<resource_type>")
    def latest(resource_type):
        league_id=request.args.get("league_id") or current_app.config.get("SLEEPER_LEAGUE_ID")
        conn=get_db_connection(); cur=conn.cursor()
        cur.execute("SELECT payload,fetched_at FROM sleeper_api_snapshots WHERE resource_type=%s AND resource_key=%s ORDER BY fetched_at DESC LIMIT 1",(resource_type,str(league_id)))
        row=cur.fetchone(); cur.close(); conn.close()
        return (jsonify(error="snapshot not found"),404) if not row else jsonify(resource_type=resource_type,fetched_at=row[1],data=row[0])
    return bp
