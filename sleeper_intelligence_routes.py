from flask import Blueprint,current_app,jsonify,render_template,request
import os
from sleeper_intelligence import build

def create_sleeper_intelligence_blueprint(db):
    bp=Blueprint("sleeper_intelligence",__name__,url_prefix="/sleeper-intelligence")
    def load():
        league=str(request.args.get("league_id") or current_app.config.get("SLEEPER_LEAGUE_ID") or os.getenv("SLEEPER_LEAGUE_ID") or "")
        season=int(request.args.get("season") or os.getenv("FANTASY_SEASON",2026));week=int(request.args.get("week") or 1)
        if not league:return None
        conn=db();cur=conn.cursor()
        try:
            data=build(cur,league,week,season)
            return league,data
        finally:
            cur.close();conn.close()
    @bp.get("/")
    def home():
        loaded=load()
        if not loaded:return "SLEEPER_LEAGUE_ID not configured",400
        return render_template("sleeper_intelligence.html",league=loaded[0],intel=loaded[1])
    @bp.get("/json")
    def json_data():
        loaded=load();return (jsonify(error="league_id required"),400) if not loaded else jsonify(loaded[1])
    return bp
