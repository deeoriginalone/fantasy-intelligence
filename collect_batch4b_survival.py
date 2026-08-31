#!/usr/bin/env python3
"""Read-only discovery for Batch 4B Monte Carlo Survival Engine."""
from __future__ import annotations
import ast, os, subprocess
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'batch4b_survival_discovery.txt'
FILES=['app.py','player_survival_probability.py','monte_carlo.py','expected_value.py','expected_value_analysis.py','draft_now_wait.py','sleeper_opponent_forecast.py','services/sleeper_service.py','templates/draftboard.html','templates/_player_survival_probability.html']
TOKENS=('monte_carlo','survival','availability','expected_value','draft_now_wait','pick_forecast','league_tendencies')
def load_env():
 p=ROOT/'.env'
 if p.exists():
  for raw in p.read_text(errors='replace').splitlines():
   x=raw.strip()
   if x and not x.startswith('#') and '=' in x:
    k,v=x.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
def add(parts,rel):
 p=ROOT/rel;parts.append(f'\n===== FILE {rel} =====')
 if not p.exists():parts.append('<missing>');return
 text=p.read_text(errors='replace')
 if rel=='app.py':
  tree=ast.parse(text);lines=text.splitlines()
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
    src='\n'.join(lines[n.lineno-1:n.end_lineno]);low=(n.name+' '+src).lower()
    if any(t in low for t in TOKENS):parts.append(f'\n--- {n.name} {n.lineno}-{n.end_lineno} ---\n{src}')
  for i,line in enumerate(lines,1):
   if any(t in line.lower() for t in TOKENS):parts.append(f'{i}: {line}')
 else:parts.append(text)
def main():
 if not (ROOT/'app.py').exists():raise SystemExit('Run from project root')
 parts=['BATCH 4B SURVIVAL DISCOVERY','READ ONLY; no files or rows modified.','\n===== GIT =====',subprocess.run(['git','status','--short','--branch'],cwd=ROOT,text=True,capture_output=True).stdout]
 for f in FILES:add(parts,f)
 load_env();import psycopg2
 cn=psycopg2.connect(host=os.environ['DB_HOST'],port=int(os.environ['DB_PORT']),dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD']);cn.set_session(readonly=True);c=cn.cursor();parts.append('\n===== LIVE SCHEMA =====')
 for table in ['players','league_rosters','league_teams','sleeper_draft_picks','sleeper_drafts','draft_decision_outcomes','recommendation_explanations','monte_carlo_runs','player_survival_curves']:
  parts.append(f'\n--- {table} ---');c.execute('SELECT to_regclass(%s)',(f'public.{table}',));x=c.fetchone()[0]
  if not x:parts.append('<missing>');continue
  c.execute("SELECT column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",(table,));parts.extend(' | '.join('' if v is None else str(v) for v in r) for r in c.fetchall());c.execute(f'SELECT count(*) FROM public."{table}"');parts.append('row_count='+str(c.fetchone()[0]))
 cn.rollback();c.close();cn.close();OUT.write_text('\n'.join(parts));print('Created:',OUT);print('Bytes:',OUT.stat().st_size);print('No files or database rows were modified.')
if __name__=='__main__':main()
