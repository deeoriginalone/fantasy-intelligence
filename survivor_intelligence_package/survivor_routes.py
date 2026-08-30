from flask import Blueprint,flash,redirect,render_template,request,url_for
from survivor_intelligence import build_recommendations,summarize
from survivor_store import migrate,ensure_pool,used_teams,current_predictions,all_schedule,future_predictions,save_selection,history,save_run
survivor_bp=Blueprint('survivor',__name__)

def _context(season,week,pool_key,strategy):
    migrate();ensure_pool(pool_key,'My Survivor Pool',season);used=used_teams(pool_key,season);current=current_predictions(season,week,strategy);schedule=all_schedule(season);future=future_predictions(season,strategy);candidates=build_recommendations(current,schedule,used,future,strategy);summary=summarize(candidates);save_run(pool_key,season,week,strategy,summary)
    return {'survivor_season':season,'survivor_week':week,'pool_key':pool_key,'strategy':strategy,'used_teams':used,'candidates':candidates,'survivor_summary':summary,'survivor_history':history(pool_key,season)}
@survivor_bp.get('/survivor')
def home():return render_template('survivor_intelligence.html',**_context(request.args.get('season',2026,type=int),request.args.get('week',1,type=int),request.args.get('pool','default'),request.args.get('strategy','balanced')))
@survivor_bp.post('/survivor/select')
def select():
    season=request.form.get('season',2026,type=int);week=request.form.get('week',1,type=int);pool=request.form.get('pool','default');team=request.form['team'];prob=float(request.form['probability']);score=float(request.form['score']);save_selection(pool,season,week,team,'pending',prob,score,request.form.get('notes',''));flash(f'Saved {team} as Week {week} survivor selection.','success');return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
@survivor_bp.post('/survivor/status')
def status():
    season=request.form.get('season',2026,type=int);week=request.form.get('week',1,type=int);pool=request.form.get('pool','default');team=request.form['team'];save_selection(pool,season,week,team,request.form['status'],request.form.get('probability',type=float),request.form.get('score',type=float),request.form.get('notes',''));return redirect(url_for('survivor.home',season=season,week=week,pool=pool))
