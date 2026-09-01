#!/usr/bin/env python3
"""Read-only discovery for Batch 4C League Behavior Modeling."""
from __future__ import annotations
import ast,os,subprocess
from pathlib import Path
R=Path.cwd();O=R/'batch4c_league_behavior_discovery.txt'
FILES=['app.py','sleeper_opponent_forecast.py','league_tendencies.py','opponent_model.py','monte_carlo_survival.py','survival_calibration.py','services/sleeper_service.py','templates/draftboard.html']
TOKENS=('league_tendencies','pick_forecast','opponent','position_pressure','projected_gone','teams_needing_position','draft_order','slot_to_roster_id','roster_id')
def env():
 p=R/'.env'
 if p.exists():
  for raw in p.read_text(errors='replace').splitlines():
   x=raw.strip()
   if x and not x.startswith('#') and '=' in x:
    k,v=x.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
def add(parts,rel):
 p=R/rel;parts.append(f'\n===== FILE {rel} =====')
 if not p.exists():parts.append('<missing>');return
 text=p.read_text(errors='replace')
 if rel=='app.py':
  tree=ast.parse(text);lines=text.splitlines()
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
    src='\n'.join(lines[n.lineno-1:n.end_lineno]);low=(n.name+' '+src).lower()
    if any(t in low for t in TOKENS):parts.append(f'\n--- {n.name} {n.lineno}-{n.end_lineno} ---\n{src}')
  for i,l in enumerate(lines,1):
   if any(t in l.lower() for t in TOKENS):parts.append(f'{i}: {l}')
 else:parts.append(text)
def main():
 if not (R/'app.py').exists():raise SystemExit('Run from project root')
 parts=['BATCH 4C LEAGUE BEHAVIOR DISCOVERY','READ ONLY. No files or rows modified.','\n===== GIT =====',subprocess.run(['git','status','--short','--branch'],cwd=R,text=True,capture_output=True).stdout]
 for f in FILES:add(parts,f)
 env();import psycopg2
 cn=psycopg2.connect(host=os.environ['DB_HOST'],port=int(os.environ['DB_PORT']),dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD']);cn.set_session(readonly=True);c=cn.cursor();parts.append('\n===== LIVE SCHEMA =====')
 for t in ['sleeper_draft_picks','sleeper_drafts','league_rosters','league_teams','sleeper_api_snapshots','monte_carlo_runs','player_survival_curves','league_behavior_profiles','owner_tendencies','position_run_history','owner_pick_history','league_pressure_snapshots']:
  parts.append(f'\n--- {t} ---');c.execute('SELECT to_regclass(%s)',(f'public.{t}',));x=c.fetchone()[0]
  if not x:parts.append('<missing>');continue
  c.execute("SELECT column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",(t,));parts.extend(' | '.join('' if v is None else str(v) for v in row) for row in c.fetchall());c.execute(f'SELECT count(*) FROM public."{t}"');parts.append('row_count='+str(c.fetchone()[0]))
 cn.rollback();c.close();cn.close();O.write_text('\n'.join(parts));print('Created:',O);print('Bytes:',O.stat().st_size);print('No files or database rows were modified.')
if __name__=='__main__':main()
