from flask import Blueprint, redirect, render_template, request, url_for
from weekly_intelligence import current_week,set_current_week
from pickem_pg_context import build_pickem_context

def create_weekly_blueprint(get_db_connection):
    bp=Blueprint('weekly_data',__name__)
    @bp.route('/weekly')
    def weekly_home():
        c=get_db_connection(); cur=c.cursor()
        try:
            week=current_week(cur)
            cur.execute("""SELECT s.week,s.game_time_pacific,h.team_name,a.team_name,s.home_team,s.away_team
                           FROM nfl_schedule s JOIN nfl_teams h ON h.team_abbr=s.home_team JOIN nfl_teams a ON a.team_abbr=s.away_team
                           WHERE s.season=2026 AND s.week=%s ORDER BY s.game_time_pacific""",(week,)); games=cur.fetchall()
            cur.execute("SELECT team,bye_week FROM bye_weeks WHERE season=2026 AND bye_week=%s ORDER BY team",(week,)); byes=cur.fetchall()
        finally: cur.close(); c.close()
        strategy=request.args.get('strategy','balanced')
        pickem_context=build_pickem_context(2026,week,strategy)
        return render_template('weekly.html',title='Weekly Intelligence',week=week,games=games,byes=byes,**pickem_context)
    @bp.route('/weekly/set',methods=['POST'])
    def set_week():
        week=max(1,min(18,int(request.form.get('week',1)))); c=get_db_connection(); cur=c.cursor()
        try: set_current_week(cur,week); c.commit()
        except Exception: c.rollback(); raise
        finally: cur.close(); c.close()
        return redirect(url_for('weekly_data.weekly_home'))
    return bp
