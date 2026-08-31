#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--season',type=int,required=True);p.add_argument('--week',type=int,required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
manifest=json.loads(Path(a.manifest).read_text()); results=[]
for source,file in manifest["sources"].items():
    cmd=[sys.executable,'ingest_weekly_data.py','--source',source,'--file',file,'--season',str(a.season),'--week',str(a.week)]
    if a.dry_run:cmd.append('--dry-run')
    run=subprocess.run(cmd,text=True,capture_output=True);results.append({"source":source,"return_code":run.returncode,"output":run.stdout+run.stderr})
    if run.returncode: print(json.dumps(results,indent=2));raise SystemExit(run.returncode)
print(json.dumps(results,indent=2))
