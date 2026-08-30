from flask import Blueprint,jsonify,render_template
from draft_readiness import build_draft_readiness

def create_draft_health_blueprint(db,league_id,season,signal_builder,health_builder):
 bp=Blueprint("draft_health",__name__,url_prefix="/draft-health")
 def load():
  conn=db();cur=conn.cursor()
  try:
   signals=signal_builder(cur,league_id,season=season,user_slot=5);health=health_builder(cur);return build_draft_readiness(cur,league_id,season,signals,health)
  finally:cur.close();conn.close()
 @bp.get("/")
 def home():return render_template("draft_health.html",readiness=load())
 @bp.get("/json")
 def data():return jsonify(load())
 return bp
