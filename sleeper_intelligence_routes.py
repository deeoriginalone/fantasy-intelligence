from flask import Blueprint,current_app,jsonify,render_template,request
import os
from sleeper_intelligence import build
def create_sleeper_intelligence_blueprint(db):
 bp=Blueprint("sleeper_intelligence",__name__,url_prefix="/sleeper-intelligence")
 def data():
  league=str(request.args.get("league_id") or current_app.config.get("SLEEPER_LEAGUE_ID") or os.getenv("SLEEPER_LEAGUE_ID") or "");week=int(request.args.get("week") or 1)
  if not league:return None,None,None
  c=db();cur=c.cursor();intel=build(cur,league,week);cur.close();c.close();return league,week,intel
 @bp.get("/")
 def home():
  league,week,intel=data()
  if not league:return "SLEEPER_LEAGUE_ID not configured",400
  return render_template("sleeper_intelligence.html",league=league,intel=intel)
 @bp.get("/json")
 def json_data():
  league,week,intel=data();return (jsonify(error="league_id required"),400) if not league else jsonify(intel)
 return bp
