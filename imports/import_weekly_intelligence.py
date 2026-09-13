from __future__ import annotations
import argparse,csv,json,os
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import psycopg2

TEAMS={
"Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL","Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI","Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL","Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB","Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX","Kansas City Chiefs":"KC","Los Angeles Chargers":"LAC","Los Angeles Rams":"LAR","Las Vegas Raiders":"LV","Miami Dolphins":"MIA","Minnesota Vikings":"MIN","New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG","New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT","San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB","Tennessee Titans":"TEN","Washington Commanders":"WAS"}
ALIASES={"JAC":"JAX","JAX":"JAX","KAN":"KC","KC":"KC","LVR":"LV","LV":"LV","NEP":"NE","NWE":"NE","NE":"NE","NOS":"NO","NOR":"NO","NO":"NO","SFO":"SF","SF":"SF","TAM":"TB","TB":"TB","WSH":"WAS","WAS":"WAS","GNB":"GB","GB":"GB"}

def abbr(v):
    v=(v or '').strip()
    return TEAMS.get(v,ALIASES.get(v.upper(),v.upper()))
def conn():
    return psycopg2.connect(host=os.getenv('DB_HOST','localhost'),port=os.getenv('DB_PORT','5433'),dbname=os.getenv('DB_NAME','fantasy_intelligence'),user=os.getenv('DB_USER','fantasy'),password=os.getenv('DB_PASSWORD'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',default='data'); ap.add_argument('--season',type=int,default=2026); ap.add_argument('--report-date',default=datetime.now().date().isoformat()); args=ap.parse_args()
    d=Path(args.data_dir); c=conn(); cur=c.cursor()
    try:
      for name,a in TEAMS.items(): cur.execute("INSERT INTO nfl_teams(team_abbr,team_name) VALUES(%s,%s) ON CONFLICT(team_abbr) DO UPDATE SET team_name=EXCLUDED.team_name",(a,name))
      with (d/'nfl-2026-UTC.csv').open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
          naive=datetime.strptime(r['Date'],'%d/%m/%Y %H:%M'); utc=naive.replace(tzinfo=timezone.utc); pac=utc.astimezone(ZoneInfo('America/Los_Angeles')).replace(tzinfo=None)
          cur.execute("""INSERT INTO nfl_schedule(season,week,match_number,game_time_utc,game_time_pacific,location,home_team,away_team,result)
                         VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                         ON CONFLICT(season,match_number) DO UPDATE SET week=EXCLUDED.week,game_time_utc=EXCLUDED.game_time_utc,game_time_pacific=EXCLUDED.game_time_pacific,location=EXCLUDED.location,home_team=EXCLUDED.home_team,away_team=EXCLUDED.away_team,result=EXCLUDED.result""",
                      (args.season,int(r['Round Number']),int(r['Match Number']),utc,pac,r['Location'],abbr(r['Home Team']),abbr(r['Away Team']),r.get('Result') or None))
      with (d/'nfl-2026-bye-weeks.csv').open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f): cur.execute("INSERT INTO bye_weeks(season,team,bye_week,source) VALUES(%s,%s,%s,%s) ON CONFLICT(season,team) DO UPDATE SET bye_week=EXCLUDED.bye_week,source=EXCLUDED.source",(args.season,abbr(r['team_abbr']),int(r['bye_week']),r.get('source')))
      with (d/'nfl-injury-report.csv').open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f): cur.execute("""INSERT INTO injury_reports(season,report_date,player_name,team,position,injury,status,estimated_return)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(season,report_date,player_name) DO UPDATE SET team=EXCLUDED.team,position=EXCLUDED.position,injury=EXCLUDED.injury,status=EXCLUDED.status,estimated_return=EXCLUDED.estimated_return""",(args.season,args.report_date,r['Player'],abbr(r['Team']),r['Pos'].upper(),r['Injury'],r['Status'],r.get('Est. Return')))
      with (d/'defense-fp-against-2025.csv').open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
          pos=r['Position'].upper().replace('DST','DEF')
          cur.execute("INSERT INTO defense_matchups(season,position,defense_team,defense_rank,fp_per_game_allowed,source,retrieved_at) VALUES(%s,%s,%s,%s,%s,%s,NOW()) ON CONFLICT(season,position,defense_team) DO UPDATE SET defense_rank=EXCLUDED.defense_rank,fp_per_game_allowed=EXCLUDED.fp_per_game_allowed,source=EXCLUDED.source,retrieved_at=EXCLUDED.retrieved_at",(args.season-1,pos,abbr(r['Team']),int(r['Rank']),float(r['FP / Game Allowed']),'defense-fp-against-2025.csv'))
      cur.execute("INSERT INTO weekly_intelligence_runs(season,week,source_files) VALUES(%s,1,%s::jsonb)",(args.season,json.dumps({'schedule':'nfl-2026-UTC.csv','byes':'nfl-2026-bye-weeks.csv','injuries':'nfl-injury-report.csv','matchups':'defense-fp-against-2025.csv'})))
      c.commit()
      for table in ['nfl_schedule','bye_weeks','injury_reports','defense_matchups']:
        cur.execute(f'SELECT COUNT(*) FROM {table}'); print(table,cur.fetchone()[0])
    except Exception: c.rollback(); raise
    finally: cur.close(); c.close()
if __name__=='__main__': main()
