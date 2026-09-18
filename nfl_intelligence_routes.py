from flask import Blueprint, abort, current_app, render_template, request
from nfl_intelligence import available_weeks, build_week_intelligence

nfl_intelligence_bp = Blueprint('nfl_intelligence', __name__)


@nfl_intelligence_bp.get('/nfl-intelligence')
def home():
    season = request.args.get('season', 2026, type=int)
    week = request.args.get('week', type=int)
    if week is None:
        acquire_week = current_app.config.get("WEEK_AUTHORITY_ACQUIRER")
        if acquire_week is None:
            context={"state":"UNAVAILABLE","blockers":["WEEK_AUTHORITY_ACQUISITION_UNAVAILABLE"]}
        else:
            context=acquire_week(season)
        if not context["authoritative"]:
            blocked = [{"name":"Week evidence unavailable", "detail":"The current NFL week could not be verified from the shared week authority boundary.", "impact":"No prediction or recommendation is published."}]
            intelligence={"season":season,"week":None,"evidence_state":"UNAVAILABLE","freshness_state":"UNAVAILABLE","last_verified":None,"top_signals":[],"high_risk":[],"games":[],"insights":{},"blockers":blocked,"scheduled_games":0,"missing_predictions":0}
            return render_template("nfl_intelligence.html", title="NFL Intelligence", season=season, week=None, intelligence=intelligence, available_weeks=available_weeks(season))
        week = context["week"]
    intelligence = build_week_intelligence(season, week)
    return render_template(
        'nfl_intelligence.html', title='NFL Intelligence', season=season, week=week,
        intelligence=intelligence, available_weeks=available_weeks(season),
    )
