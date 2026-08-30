from flask import Blueprint,jsonify,render_template
from draft_outcome_tracker import accuracy_summary
from model_calibration import model_health

def create_draft_accuracy_blueprint(db):
 bp=Blueprint("draft_accuracy",__name__,url_prefix="/draft-accuracy")
 def load():
  conn=db();cur=conn.cursor();accuracy=accuracy_summary(cur);health=model_health(cur);cur.close();conn.close();return accuracy,health
 @bp.get("/")
 def home():
  accuracy,health=load();return render_template("draft_accuracy.html",data=accuracy,health=health)
 @bp.get("/json")
 def data():
  accuracy,health=load();return jsonify({"accuracy":accuracy,"health":health})
 @bp.get("/models")
 def models():return jsonify(load()[1])
 @bp.get("/calibration")
 def calibration():
  accuracy,health=load();return jsonify({"resolved":health["resolved"],"active":health["active"],"weights":health["weights"],"metrics":health["metrics"],"minimum_samples":health["minimum_samples"],"reason":health["reason"]})
 @bp.get("/outcomes")
 def outcomes():return jsonify(load()[0].get("recent",[]))
 return bp
