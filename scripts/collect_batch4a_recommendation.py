#!/usr/bin/env python3
"""Collect exact Batch 4A recommendation inputs. Read-only."""
from __future__ import annotations
import ast, os, subprocess
from pathlib import Path
ROOT=Path.cwd(); OUT=ROOT/'batch4a_recommendation_discovery.txt'
FILES=['app.py','balanced_recommendation_score.py','recommendation_engine_audit.py','draft_decision_plan.py','reconciled_draft_decision.py','draft_coach_sleeper_fusion.py','player_survival_probability.py','sleeper_recommendation_overlay.py','candidate_filter.py','dynamic_need_model.py','scarcity_model.py','templates/draftboard.html']
NAMES={'calculate_balanced_score','audit_recommendation_candidates','build_decision_plan','fuse_decision_plan','reconcile_draft_now_wait','fuse_sleeper_context','estimate_player_survival','build_recommendation_overlay','filter_candidate_pool','calculate_dynamic_need','calculate_dynamic_scarcity'}

def load_env():
 p=ROOT/'.env'
 if p.exists():
  for raw in p.read_text(errors='replace').splitlines():
   x=raw.strip()
   if x and not x.startswith('#') and '=' in x:
    k,v=x.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

def add_file(parts,rel):
 p=ROOT/rel;parts.append(f'\n===== FILE {rel} =====')
 if not p.exists():parts.append('<missing>');return
 text=p.read_text(errors='replace')
 if rel=='app.py':
  tree=ast.parse(text);lines=text.splitlines()
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.name in NAMES or n.name=='draftboard'):
    parts.append(f'\n--- {n.name} lines {n.lineno}-{n.end_lineno} ---');parts.extend(lines[n.lineno-1:n.end_lineno])
  for i,line in enumerate(lines,1):
   if any(x in line for x in ['recommendation_candidates =','top_recommendations =','team_recommendation =','recommendation_engine_audit =','draft_decision_plan =','player_survival =','expected_value_analysis =']):parts.append(f'{i}: {line}')
 else:parts.append(text)

def main():
 if not (ROOT/'app.py').exists():raise SystemExit('Run from project root')
 parts=['BATCH 4A RECOMMENDATION EXPLAINABILITY DISCOVERY','READ ONLY. No secrets included.','\n===== GIT =====',subprocess.run(['git','status','--short','--branch'],cwd=ROOT,text=True,capture_output=True).stdout]
 for f in FILES:add_file(parts,f)
 load_env();import psycopg2
 cn=psycopg2.connect(host=os.environ['DB_HOST'],port=int(os.environ['DB_PORT']),dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD']);cn.set_session(readonly=True);c=cn.cursor()
 parts.append('\n===== LIVE PLAYER/OUTCOME SCHEMA =====')
 for table in ['players','draft_decision_outcomes','recommendation_audit','draft_recommendation_audit','recommendation_explanations']:
  parts.append(f'\n--- {table} ---');c.execute('SELECT to_regclass(%s)',(f'public.{table}',));exists=c.fetchone()[0]
  if not exists:parts.append('<missing>');continue
  c.execute("SELECT column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",(table,));parts.extend(' | '.join('' if x is None else str(x) for x in r) for r in c.fetchall());c.execute(f'SELECT count(*) FROM public."{table}"');parts.append('row_count='+str(c.fetchone()[0]))
 cn.rollback();c.close();cn.close();OUT.write_text('\n'.join(parts));print('Created:',OUT);print('Bytes:',OUT.stat().st_size);print('No files or database rows were modified.')
if __name__=='__main__':main()
