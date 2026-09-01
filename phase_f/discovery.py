from __future__ import annotations
import argparse, ast, json
from pathlib import Path
KEYWORDS=('recommend','draft','outcome','readiness','roster','sleeper')

def discover(repo):
    rows=[]
    for path in Path(repo).rglob('*.py'):
        if any(x in path.parts for x in ('venv','.git','archive','__pycache__')): continue
        try: tree=ast.parse(path.read_text(encoding='utf-8',errors='ignore'))
        except SyntaxError: continue
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and any(k in node.name.lower() for k in KEYWORDS):
                args=[a.arg for a in node.args.args]
                rows.append({'file':str(path.relative_to(repo)),'function':node.name,'async':isinstance(node,ast.AsyncFunctionDef),'args':args,'line':node.lineno})
    return rows

def main():
    p=argparse.ArgumentParser(); p.add_argument('--repo',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    rows=discover(Path(a.repo).resolve()); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rows,indent=2),encoding='utf-8'); print(f"wrote {len(rows)} candidates to {out}")
if __name__=='__main__': main()
