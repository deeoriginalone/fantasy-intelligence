from flask import Blueprint, jsonify, render_template, request
from pickem_pg_store import connect
from pickem_auto_feed import refresh
pickem_feed_bp=Blueprint('pickem_feed',__name__)
@pickem_feed_bp.get('/pickem/feed-health')
def health_page():
    conn=connect()
    try:
        with conn.cursor() as cur:
            cur.execute('''SELECT id,season,week,provider,started_at,finished_at,status,games_received,games_updated,errors,details FROM pickem_feed_runs ORDER BY started_at DESC LIMIT 25''')
            cols=[d[0] for d in cur.description]; runs=[dict(zip(cols,r)) for r in cur.fetchall()]
    finally: conn.close()
    return render_template('pickem_feed_health.html',title='Pick’em Feed Health',runs=runs)
@pickem_feed_bp.post('/api/pickem/refresh')
def refresh_api():
    data=request.get_json(silent=True) or {}; return jsonify(refresh(int(data.get('season',2026)),int(data.get('week',1)),bool(data.get('dry_run',False))))
