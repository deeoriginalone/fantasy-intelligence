from flask import Blueprint,jsonify,render_template,request
from psycopg2.extras import RealDictCursor
from pickem_pg_store import connect
from market_intelligence import summarize
from market_refresh import run
from auth import admin_required
market_bp=Blueprint('market_intelligence',__name__)
def context(season,week,strategy='balanced'):
    conn=connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            c.execute('''SELECT p.*,g.away_team,g.home_team,g.kickoff,g.away_moneyline,g.home_moneyline,g.projected_total,g.market_updated_at FROM market_intelligence_predictions p JOIN yahoo_pickem_games g USING(game_id) WHERE g.season=%s AND g.week=%s AND p.strategy=%s ORDER BY p.confidence_points DESC''',(season,week,strategy)); rows=[dict(x) for x in c.fetchall()]
            c.execute('SELECT * FROM market_intelligence_runs WHERE season=%s AND week=%s ORDER BY started_at DESC LIMIT 1',(season,week)); health=c.fetchone()
    finally:conn.close()
    return {'market_predictions':rows,'market_summary':summarize(rows),'market_season':season,'market_week':week,'market_strategy':strategy,'market_health':health}
@market_bp.get('/market-intelligence')
def home():return render_template('market_intelligence.html',**context(request.args.get('season',2026,type=int),request.args.get('week',1,type=int),request.args.get('strategy','balanced')))
@market_bp.post('/api/market-intelligence/refresh')
@admin_required
def refresh():
    d=request.get_json(silent=True) or {};return jsonify(run(int(d.get('season',2026)),int(d.get('week',1)),d.get('strategy','balanced'),bool(d.get('dry_run',False))))
