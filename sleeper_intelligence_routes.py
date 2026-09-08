from flask import Blueprint,current_app,jsonify,render_template,request
import os
from sleeper_intelligence import build
from services.publication_gate import PublicationBlockedError
from services.readiness_report_io import load_readiness_report
from services.waiver_action_publication import build_waiver_publication


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

    def waiver_publication(data):
        path=current_app.config.get("F3_READINESS_REPORT_PATH") or os.getenv("F3_READINESS_REPORT_PATH")
        if not path:
            return {
                "allowed":False,
                "decision":{"reason_codes":["READINESS_REPORT_PATH_MISSING"]},
                "waiver_candidates":[],"waiver_action_plans":[],"local_roster_context":{},
            }
        try:
            report=load_readiness_report(path)
            return build_waiver_publication(data,report)
        except (OSError,ValueError,KeyError,TypeError,PublicationBlockedError) as exc:
            current_app.logger.warning("Waiver publication blocked: %s",exc)
            return {
                "allowed":False,
                "decision":{"reason_codes":["READINESS_REPORT_INVALID"]},
                "waiver_candidates":[],"waiver_action_plans":[],"local_roster_context":{},
            }

    @bp.get("/")
    def home():
        loaded=load()
        if not loaded:return "SLEEPER_LEAGUE_ID not configured",400
        publication=waiver_publication(loaded[1])
        return render_template("sleeper_intelligence.html",league=loaded[0],intel=loaded[1],waiver_publication=publication)

    @bp.get("/json")
    def json_data():
        loaded=load();return (jsonify(error="league_id required"),400) if not loaded else jsonify(loaded[1])
    return bp
