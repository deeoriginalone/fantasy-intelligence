from __future__ import annotations
import argparse
from pathlib import Path
from .configuration import load_config
from .integration import VerifiedCallableAdapter
from .simulator import DraftSimulator
from .sources import JsonLinesPickSource
from .snapshots import SnapshotWriter
from .reports import write_reports
from .strategies import get_strategy

def main():
    p=argparse.ArgumentParser(); p.add_argument('--events',required=True); p.add_argument('--teams',type=int,required=True); p.add_argument('--rounds',type=int,required=True); p.add_argument('--config',required=True); p.add_argument('--output-dir',required=True); a=p.parse_args()
    cfg=load_config(a.config); rec=cfg['recommendation']; get_strategy(cfg.get('strategy','balanced'))
    adapter=VerifiedCallableAdapter(rec['target'],read_only=rec['read_only'],synthetic=bool(rec.get('synthetic')))
    simulator=DraftSimulator(a.teams,a.rounds,adapter); result=simulator.replay(JsonLinesPickSource(a.events))
    writer=SnapshotWriter(Path(a.output_dir)/'recommendation_snapshots.jsonl')
    for pick,recommendation in zip(result.state.picks,result.recommendations): writer.append(pick.pick_no,recommendation)
    summary={'status':'complete' if result.state.complete else 'partial','accepted_picks':len(result.state.picks),'recommendations':len(result.recommendations),'strategy':cfg.get('strategy','balanced'),'synthetic':bool(rec.get('synthetic'))}
    write_reports(a.output_dir,summary); print(f"wrote Batch F2 artifacts to {a.output_dir}")
if __name__=='__main__': main()
