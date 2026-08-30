from flask import Blueprint,jsonify,render_template
from draft_outcome_tracker import accuracy_summary
def create_draft_accuracy_blueprint(db):
 bp=Blueprint("draft_accuracy",__name__,url_prefix="/draft-accuracy")
 @bp.get("/")
 def home():
  conn=db();cur=conn.cursor();data=accuracy_summary(cur);cur.close();conn.close();return render_template("draft_accuracy.html",data=data)
 @bp.get("/json")
 def data():
  conn=db();cur=conn.cursor();out=accuracy_summary(cur);cur.close();conn.close();return jsonify(out)
 return bp
