from flask import Blueprint,flash,redirect,render_template,request,url_for
from auth import csrf_required
from survivor_intelligence import build_recommendations,build_status,determine_week_state,next_verified_week,summarize,team_universe
from survivor_store import (migrate,ensure_pool,used_teams,current_predictions,all_schedule,future_predictions,
    save_selection,delete_selection,history,save_run,week_selection,SurvivorConflictError,SurvivorHistoryReadError)
from services.ux_evidence import format_pacific_datetime
from services.sleeper_service import get_nfl_state
survivor_bp=Blueprint('survivor',__name__)

def _verified_current_week(season):
    """Sleeper-verified current NFL week for this season; None (never guessed) if unavailable or mismatched."""
    try:
        state=get_nfl_state()
        if str(state.get('season'))!=str(season): return None
        week=int(state.get('week') or 0)
        return week if week>0 else None
    except Exception:
        return None

def _context(season,week,pool_key,strategy):
    migrate();ensure_pool(pool_key,'My Survivor Pool',season)
    schedule=all_schedule(season)
    schedule_weeks={int(row['week']) for row in schedule}
    try:
        used=used_teams(pool_key,season)
        existing_selection=week_selection(pool_key,season,week)
        history_status='verified'
    except SurvivorHistoryReadError:
        used=[];existing_selection=None;history_status='read_failed'
    week_state,result_label=('BLOCKED',None) if history_status=='read_failed' else determine_week_state(existing_selection,schedule_weeks,week)
    if history_status=='read_failed' or week_state=='UNAVAILABLE':
        current=[];candidates=[];summary=summarize([])
    else:
        current=current_predictions(season,week,strategy)
        future=future_predictions(season,strategy)
        candidates=build_recommendations(current,schedule,used,future,strategy)
        summary=summarize(candidates)
        if week_state=='OPEN':
            save_run(pool_key,season,week,strategy,summary)
    status=build_status(season=season,week=week,history_status=history_status,used_teams=used,
        schedule_rows=schedule,current_rows=current,candidates=candidates,week_state=week_state)
    next_week=next_verified_week(schedule_weeks,week) if history_status=='verified' else None
    eligible_teams=sorted(team_universe(schedule)-set(used)) if history_status=='verified' and week_state=='OPEN' else []
    return {'survivor_season':season,'survivor_week':week,'pool_key':pool_key,'strategy':strategy,
        'used_teams':used,'candidates':candidates,'survivor_summary':summary,'survivor_status':status,
        'existing_selection':existing_selection,'result_label':result_label,'next_week':next_week,
        'eligible_teams':eligible_teams,
        'last_verified_pacific':format_pacific_datetime(status.get('last_verified')),
        'survivor_history':history(pool_key,season) if history_status=='verified' else []}
@survivor_bp.get('/survivor')
def home():
    season=request.args.get('season',2026,type=int)
    week=request.args.get('week',type=int)
    if week is None:
        week=_verified_current_week(season) or 1
    return render_template('survivor_intelligence.html',**_context(season,week,request.args.get('pool','default'),request.args.get('strategy','balanced')))
@survivor_bp.post('/survivor/select')
@csrf_required
def select():
    season=request.form.get('season',2026,type=int);week=request.form.get('week',1,type=int);pool=request.form.get('pool','default');team=(request.form.get('team') or '').strip().upper()
    prob=request.form.get('probability',type=float);score=request.form.get('score',type=float)
    if not team:
        flash('Choose a team before recording a pick.','error')
        return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
    known_teams=team_universe(all_schedule(season))
    if team not in known_teams:
        flash(f'"{team}" is not a recognized NFL team for season {season}; no pick was recorded.','error')
        return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
    notes=request.form.get('notes','') or ('USER_RECORDED: manually selected, not the algorithmic recommendation' if prob is None else '')
    try:
        save_selection(pool,season,week,team,'pending',prob,score,notes)
        flash(f'Saved {team} as Week {week} survivor selection.','success')
    except SurvivorConflictError as e:
        flash(str(e),'error')
    return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
@survivor_bp.post('/survivor/status')
@csrf_required
def status():
    season=request.form.get('season',2026,type=int);week=request.form.get('week',1,type=int);pool=request.form.get('pool','default');team=request.form['team']
    try:
        save_selection(pool,season,week,team,request.form['status'],request.form.get('probability',type=float),request.form.get('score',type=float),request.form.get('notes',''))
    except SurvivorConflictError as e:
        flash(str(e),'error')
    return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
@survivor_bp.post('/survivor/reset')
@csrf_required
def reset():
    season=request.form.get('season',2026,type=int);week=request.form.get('week',1,type=int);pool=request.form.get('pool','default');team=request.form['team']
    deleted=delete_selection(pool,season,week,team)
    if deleted:
        flash(f'Cleared the Week {week} {team} pick. A fresh recommendation will show once evidence is available.','success')
    else:
        flash(f'No recorded Week {week} {team} pick was found to clear.','error')
    return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
