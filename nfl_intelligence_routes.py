from flask import Blueprint, render_template, request
from nfl_intelligence import available_weeks, build_week_intelligence
from services.sleeper_service import get_nfl_state

nfl_intelligence_bp = Blueprint('nfl_intelligence', __name__)


def _verified_current_week(season):
    try:
        state = get_nfl_state()
        if str(state.get('season')) != str(season):
            return None
        week = int(state.get('week') or 0)
        return week if week > 0 else None
    except Exception:
        return None


@nfl_intelligence_bp.get('/nfl-intelligence')
def home():
    season = request.args.get('season', 2026, type=int)
    week = request.args.get('week', type=int)
    if week is None:
        week = _verified_current_week(season) or 1
    intelligence = build_week_intelligence(season, week)
    return render_template(
        'nfl_intelligence.html', title='NFL Intelligence', season=season, week=week,
        intelligence=intelligence, available_weeks=available_weeks(season),
    )
