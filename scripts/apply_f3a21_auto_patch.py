#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import ast, shutil, sys

APP = Path("app.py")
IMPORT_LINE = "from draft_events.runtime import process_runtime_picks\n"
CALL_BLOCK = (
    "\n    # F3-A.2 runtime audit persistence. Existing roster/board sync remains authoritative.\n"
    "    f3a2_event_pipeline = process_runtime_picks(\n"
    "        get_db_connection,\n"
    "        picks,\n"
    "        SLEEPER_LEAGUE_ID,\n"
    "        SLEEPER_DRAFT_ID,\n"
    "        rosters,\n"
    "    )\n"
)

def line_end_offset(text, lineno):
    lines=text.splitlines(keepends=True)
    return sum(len(x) for x in lines[:lineno])

def main():
    if not APP.exists(): raise SystemExit("app.py not found; run from repository root")
    text=APP.read_text(encoding="utf-8")
    if "process_runtime_picks(" in text and IMPORT_LINE.strip() in text:
        print("F3-A.2.1 already applied; no change")
        return
    tree=ast.parse(text)
    funcs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=="sync_sleeper_draft_picks"]
    if len(funcs)!=1: raise SystemExit(f"Expected one sync_sleeper_draft_picks function, found {len(funcs)}; no change")
    fn=funcs[0]
    roster_node=None
    for node in fn.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="rosters" for t in node.targets):
            call=node.value
            if isinstance(call,ast.BoolOp): call=call.values[0]
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=="get_rosters":
                roster_node=node; break
    if roster_node is None: raise SystemExit("Active rosters assignment not found; no change")
    modified=text
    if IMPORT_LINE.strip() not in modified:
        lines=modified.splitlines(keepends=True)
        insert_at=0
        for node in tree.body:
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                insert_at=max(insert_at,node.end_lineno)
        offset=sum(len(x) for x in lines[:insert_at])
        modified=modified[:offset]+IMPORT_LINE+modified[offset:]
        tree=ast.parse(modified)
        fn=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="sync_sleeper_draft_picks"][0]
        for node in fn.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="rosters" for t in node.targets):
                call=node.value
                if isinstance(call,ast.BoolOp): call=call.values[0]
                if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=="get_rosters": roster_node=node; break
    if "process_runtime_picks(" not in modified:
        offset=line_end_offset(modified,roster_node.end_lineno)
        modified=modified[:offset]+CALL_BLOCK+modified[offset:]
    ast.parse(modified)
    if modified==text:
        print("No change required")
        return
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=APP.with_name(f"app.py.before_f3a21_{stamp}")
    shutil.copy2(APP,backup)
    APP.write_text(modified,encoding="utf-8")
    verify=APP.read_text(encoding="utf-8")
    if IMPORT_LINE.strip() not in verify or "f3a2_event_pipeline = process_runtime_picks(" not in verify:
        shutil.copy2(backup,APP); raise SystemExit("Verification failed; backup restored")
    print(f"Patched app.py successfully; backup: {backup}")
    print("Next: python -m py_compile app.py && python -m unittest discover -s tests -v")

if __name__=="__main__": main()
