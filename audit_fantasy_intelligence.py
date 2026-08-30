#!/usr/bin/env python3
"""Fantasy Intelligence one-batch architecture audit.
Creates PROJECT_AUDIT.md and project_audit.json without modifying application code.
Run from the repository root with the venv active.
"""
from __future__ import annotations
import ast, json, os, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path.cwd()
EXCLUDE={'.git','venv','__pycache__','backups','node_modules','.pytest_cache'}
REPORT=ROOT/'PROJECT_AUDIT.md'; JSON_OUT=ROOT/'project_audit.json'

def files(ext):
    out=[]
    for p in ROOT.rglob(f'*{ext}'):
        if any(part in EXCLUDE for part in p.parts): continue
        out.append(p)
    return sorted(out)

def rel(p): return str(p.relative_to(ROOT))
def run(cmd):
    x=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    return {'code':x.returncode,'stdout':x.stdout.strip(),'stderr':x.stderr.strip()}

def parse_python(p):
    text=p.read_text(encoding='utf-8',errors='replace')
    try: tree=ast.parse(text); error=None
    except SyntaxError as e: return {'path':rel(p),'error':f'{e.msg} line {e.lineno}','imports':[],'functions':[],'routes':[],'blueprints':[]}
    imports=[]; funcs=[]; routes=[]; bps=[]
    for n in ast.walk(tree):
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            imports.append(ast.get_source_segment(text,n) or '')
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            funcs.append(n.name)
            for d in n.decorator_list:
                s=ast.get_source_segment(text,d) or ''
                if '.route(' in s or '.get(' in s or '.post(' in s:
                    routes.append({'function':n.name,'decorator':s})
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Blueprint':
            bps.append(ast.get_source_segment(text,n) or '')
    return {'path':rel(p),'error':error,'imports':imports,'functions':funcs,'routes':routes,'blueprints':bps}

def feature_hits(text):
    keys={
      'Draft Coach':['draft_coach','build_draft_coach_summary'],
      'Draft Now/Wait':['draft_now_wait','build_draft_now_wait_analysis'],
      'Recommendation Engine':['top_recommendations','draft_score','scarcity_score'],
      'Tier Engine':['tier_bonus','tier_gap','tier_cliff'],
      'Monte Carlo':['monte_carlo','simulation'],
      'Opponent Model':['opponent','position_pressure','teams_before_next_pick'],
      'League Tendencies':['league_tendencies','league_bonus'],
      'Predraft Lab':['def predraft','predraft.html'],
      'Draft Board':['def draftboard','draftboard.html'],
      'Mock Draft Lab':['mock_draft','mockdraft'],
      'Owner Operations':['owner_ops','owner_operations'],
      'Weekly Intelligence':['weekly_intelligence','weekly_score'],
      'Sleeper Hub':['sleeper_hub','sleeper_api_snapshots'],
      'Sleeper Intelligence':['sleeper_intelligence','players_cached'],
      'Waivers':['waivers_page','waivers.html'],
      'Trades':['trades_page','trades.html'],
    }
    return {k:sum(text.lower().count(x.lower()) for x in v) for k,v in keys.items()}

def db_audit():
    try:
        import psycopg2
        pw=os.getenv('DB_PASSWORD')
        if not pw: return {'connected':False,'error':'DB_PASSWORD not set'}
        c=psycopg2.connect(host=os.getenv('DB_HOST','localhost'),port=os.getenv('DB_PORT','5433'),dbname=os.getenv('DB_NAME','fantasy_intelligence'),user=os.getenv('DB_USER','fantasy'),password=pw)
        cur=c.cursor();cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename");tables=[r[0] for r in cur.fetchall()]
        counts={}
        for t in tables:
            if t in {'sleeper_api_snapshots','sleeper_sync_runs','nfl_schedule','bye_weeks','injury_reports','defense_matchups','mock_drafts','mock_picks'}:
                try: cur.execute('SELECT COUNT(*) FROM '+t);counts[t]=cur.fetchone()[0]
                except Exception: c.rollback()
        snapshots=[]
        if 'sleeper_api_snapshots' in tables:
            cur.execute("SELECT resource_type,resource_key,season,week,fetched_at FROM sleeper_api_snapshots ORDER BY resource_type,season,week")
            snapshots=[{'resource':r[0],'key':r[1],'season':r[2],'week':r[3],'fetched_at':str(r[4])} for r in cur.fetchall()]
        cur.close();c.close();return {'connected':True,'tables':tables,'counts':counts,'snapshots':snapshots}
    except Exception as e:return {'connected':False,'error':str(e)}

def main():
    py=files('.py'); html=files('.html'); sql=files('.sql')
    parsed=[parse_python(p) for p in py]
    syntax=[x for x in parsed if x['error']]
    routes=[dict(file=x['path'],**r) for x in parsed for r in x['routes']]
    funcs=defaultdict(list)
    for x in parsed:
        for f in x['functions']: funcs[f].append(x['path'])
    duplicate_funcs={k:v for k,v in funcs.items() if len(v)>1 and k not in {'main','home','status','sync','latest'}}
    route_paths=defaultdict(list)
    for r in routes:
        m=re.search(r"['\"]([^'\"]+)['\"]",r['decorator'])
        if m: route_paths[m.group(1)].append(f"{r['file']}:{r['function']}")
    duplicate_routes={k:v for k,v in route_paths.items() if len(v)>1}
    active_text='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in py+html)
    features=feature_hits(active_text)
    sleeper_files=[x['path'] for x in parsed if 'sleeper' in x['path'].lower()]
    app_imports=[]
    for x in parsed:
        if x['path']=='app.py': app_imports=x['imports']
    migrations=[rel(p) for p in sql if 'migration' in str(p.parent).lower()]
    migration_nums=defaultdict(list)
    for m in migrations:
        z=re.search(r'(\d+)_',Path(m).name)
        if z:migration_nums[z.group(1)].append(m)
    duplicate_migrations={k:v for k,v in migration_nums.items() if len(v)>1}
    git=run(['git','status','--short']) if (ROOT/'.git').exists() else {'code':1,'stdout':'','stderr':'not a git repo'}
    compile_result=run([sys.executable,'-m','compileall','-q','-x','.*(backups|venv|__pycache__).*','.'])
    db=db_audit()
    data={'root':str(ROOT),'summary':{'python_files':len(py),'templates':len(html),'sql_files':len(sql),'routes':len(routes),'syntax_errors':len(syntax)},'features':features,'syntax_errors':syntax,'routes':routes,'duplicate_routes':duplicate_routes,'duplicate_functions':duplicate_funcs,'sleeper_files':sleeper_files,'app_service_imports':[x for x in app_imports if 'sleeper' in x or 'owner' in x or 'weekly' in x],'migrations':migrations,'duplicate_migrations':duplicate_migrations,'git_status':git,'compile':compile_result,'database':db}
    JSON_OUT.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8')
    lines=['# Fantasy Intelligence Project Audit','',f"Generated from `{ROOT}`.",'','## Executive Summary','',f"- Active Python files: **{len(py)}**",f"- Active templates: **{len(html)}**",f"- SQL files: **{len(sql)}**",f"- Discovered routes: **{len(routes)}**",f"- Active syntax errors: **{len(syntax)}**",f"- Database connected: **{db.get('connected')}**",'','## Capability Inventory','']
    for k,v in sorted(features.items()):lines.append(f"- {'✅' if v else '⬜'} **{k}**: {v} code references")
    lines+=['','## Duplicate / Overlap Findings','',f"### Duplicate routes\n```json\n{json.dumps(duplicate_routes,indent=2)}\n```",f"### Duplicate significant function names\n```json\n{json.dumps(duplicate_funcs,indent=2)}\n```",f"### Duplicate migration numbers\n```json\n{json.dumps(duplicate_migrations,indent=2)}\n```",'','## Sleeper Architecture','']
    lines += [f'- `{x}`' for x in sleeper_files] or ['- None']
    lines+=['','### Sleeper-related imports in app.py','```']+[x for x in data['app_service_imports']]+['```','','## Route Inventory','']
    for r in routes:lines.append(f"- `{r['decorator']}` → `{r['file']}:{r['function']}`")
    lines+=['','## Database','']
    if db.get('connected'):
        lines.append('### Key table counts')
        for k,v in db.get('counts',{}).items():lines.append(f'- `{k}`: {v}')
        lines.append('### Sleeper snapshots')
        for x in db.get('snapshots',[]):lines.append(f"- `{x['resource']}` season {x['season']} week {x['week']} fetched {x['fetched_at']}")
    else:lines.append(f"- Database audit unavailable: `{db.get('error')}`")
    lines+=['','## Syntax / Compile Health','',f"- compileall exit code: `{compile_result['code']}`"]
    if syntax:
        for x in syntax:lines.append(f"- `{x['path']}`: {x['error']}")
    if compile_result['stderr']:lines+=['```',compile_result['stderr'],'```']
    lines+=['','## Git State','```',git['stdout'] or '(clean)','```','','## Consolidation Decision Rules','',
      '1. Keep one canonical Sleeper HTTP client. Compatibility aliases may remain in that client.',
      '2. Keep one canonical cached-sync implementation and one user-facing Sleeper Hub.',
      '3. Treat Sleeper Intelligence as a reusable engine; existing Draft HQ, Waivers, Owner Operations, and Weekly pages should consume it rather than duplicate it.',
      '4. Do not build a new Draft War Room until the route inventory proves Draft HQ lacks the required capability.',
      '5. Preserve all numbered migrations and resolve duplicate migration numbers before merge.',
      '6. Do not alter historical backups during active-code cleanup.',
      '','## Next Batch Gate','',
      'Use this audit to define one consolidation patch against the exact active files. Do not apply a blind rewrite before reviewing duplicate routes, existing feature references, and database state.'
    ]
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'PASS: wrote {REPORT.name} and {JSON_OUT.name}')
    print(json.dumps(data['summary'],indent=2))
    if duplicate_routes:print(f'WARNING: {len(duplicate_routes)} duplicate route paths found')
    if duplicate_migrations:print(f'WARNING: {len(duplicate_migrations)} duplicate migration numbers found')
    if syntax:print(f'WARNING: {len(syntax)} active syntax errors found')
if __name__=='__main__':main()
