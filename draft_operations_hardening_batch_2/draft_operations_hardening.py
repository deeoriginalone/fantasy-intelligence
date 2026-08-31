import json
from flask import Blueprint,jsonify,redirect,render_template,url_for

def state(c,p):
 c.execute("SELECT drafted,starred FROM draft_board WHERE player_name=%s",(p,));a=c.fetchone();c.execute("SELECT id,team_name,position FROM league_rosters WHERE player_name=%s ORDER BY id",(p,));x=c.fetchall();c.execute("SELECT id,position,slot FROM my_roster WHERE player_name=%s ORDER BY id",(p,));m=c.fetchall();return {"board":a,"league":x,"mine":m}
def audit(c,d,a,p,t,s,b,f,m={}):c.execute("INSERT INTO draft_mutation_history(draft_id,action,player_name,team_name,source,before_state,after_state,metadata) VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)",(str(d),a,p,t,s,json.dumps(b),json.dumps(f),json.dumps(m)))
def invariants(c):
 c.execute("SELECT player_name,array_agg(DISTINCT team_name) FROM league_rosters GROUP BY player_name HAVING count(DISTINCT team_name)>1");a=c.fetchall();c.execute("SELECT lr.player_name FROM league_rosters lr LEFT JOIN draft_board d ON d.player_name=lr.player_name WHERE coalesce(d.drafted,false)=false");b=c.fetchall();c.execute("SELECT d.player_name FROM draft_board d WHERE d.drafted=true AND NOT EXISTS(SELECT 1 FROM league_rosters r WHERE r.player_name=d.player_name)");q=c.fetchall();c.execute("SELECT m.player_name FROM my_roster m WHERE NOT EXISTS(SELECT 1 FROM league_rosters r WHERE r.player_name=m.player_name)");o=c.fetchall();return {"multiple_owners":a,"roster_not_drafted":b,"drafted_without_owner":q,"my_roster_orphans":o,"valid":not(a or b or q or o)}
def track(req,db,available,d):
 e=msg=None
 if req.method=='POST':
  t=(req.form.get('team_name') or '').strip();p=(req.form.get('player_name') or '').strip();cn=db();c=cn.cursor()
  try:
   c.execute("SELECT position FROM players WHERE player_name=%s",(p,));r=c.fetchone();c.execute("SELECT 1 FROM league_teams WHERE team_name=%s",(t,));te=c.fetchone();c.execute("SELECT team_name FROM league_rosters WHERE player_name=%s",(p,));own=c.fetchone()
   if not t or not p:e='Select both a team and a player.'
   elif not r:e='The selected player was not found.'
   elif not te:e='The selected team was not found.'
   elif own:e=f'{p} has already been drafted by {own[0]}.'
   else:
    before=state(c,p);pos=r[0];c.execute("INSERT INTO league_rosters(team_name,player_name,position) VALUES(%s,%s,%s)",(t,p,pos));c.execute("INSERT INTO draft_board(player_name,starred,drafted) VALUES(%s,false,true) ON CONFLICT(player_name) DO UPDATE SET drafted=true",(p,));
    if t=='My Team':c.execute("INSERT INTO my_roster(player_name,position) SELECT %s,%s WHERE NOT EXISTS(SELECT 1 FROM my_roster WHERE player_name=%s)",(p,pos,p))
    after=state(c,p);v=invariants(c)
    if not v['valid']:raise RuntimeError('Invariant violation '+json.dumps(v))
    audit(c,d,'MANUAL_PICK',p,t,'trackdraft',before,after,{'position':pos});cn.commit();msg=f'Recorded {p} to {t}.'
  except Exception as x:cn.rollback();e=str(x)
  finally:c.close();cn.close()
 cn=db();c=cn.cursor();c.execute("SELECT team_name FROM league_teams ORDER BY id");teams=[r[0] for r in c.fetchall()];av=available(c);c.execute("SELECT id,team_name,player_name,position,drafted_at FROM league_rosters ORDER BY drafted_at DESC,id DESC LIMIT 20");recent=c.fetchall();c.close();cn.close();return render_template('trackdraft.html',title='Draft Tracker',teams=teams,available_players=av,recent_picks=recent,message=msg,error=e)
def undo(req,db,d):
 i=(req.form.get('pick_id') or '').strip()
 if not i.isdigit():return redirect(url_for('track_draft'))
 cn=db();c=cn.cursor()
 try:
  c.execute("SELECT team_name,player_name,position FROM league_rosters WHERE id=%s FOR UPDATE",(int(i),));r=c.fetchone()
  if r:
   t,p,pos=r;before=state(c,p);c.execute("DELETE FROM league_rosters WHERE id=%s",(int(i),));c.execute("SELECT 1 FROM league_rosters WHERE player_name=%s",(p,));owned=c.fetchone() is not None;c.execute("UPDATE draft_board SET drafted=%s WHERE player_name=%s",(owned,p));
   if not owned:c.execute("DELETE FROM my_roster WHERE player_name=%s",(p,))
   after=state(c,p);v=invariants(c)
   if not v['valid']:raise RuntimeError('Invariant violation '+json.dumps(v))
   audit(c,d,'UNDO_PICK',p,t,'trackdraft_undo',before,after,{'pick_id':int(i),'position':pos});cn.commit()
 except:cn.rollback();raise
 finally:c.close();cn.close()
 return redirect(url_for('track_draft'))
def blueprint(db,d):
 bp=Blueprint('draft_operations',__name__,url_prefix='/draft-operations')
 @bp.get('/health')
 def health():
  cn=db();c=cn.cursor();v=invariants(c);c.execute("SELECT count(*) FROM draft_mutation_history WHERE draft_id=%s",(str(d),));n=c.fetchone()[0];c.execute("SELECT action,player_name,team_name,source,created_at FROM draft_mutation_history WHERE draft_id=%s ORDER BY id DESC LIMIT 10",(str(d),));r=c.fetchall();c.close();cn.close();return jsonify(draft_id=str(d),invariants=v,mutation_count=n,recent_mutations=r)
 return bp
