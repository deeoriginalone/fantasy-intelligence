import argparse, json
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from .models import DraftEvent
from .service import DraftEventProcessor
from .store import InMemoryDraftEventStore

def event_from_json(x):
    x=dict(x); x['occurred_at']=datetime.fromisoformat(x['occurred_at'].replace('Z','+00:00'))
    x['raw_payload']=x.get('raw_payload',dict(x)); return DraftEvent(**x)
def show(r): print(json.dumps(asdict(r), sort_keys=True))
def main(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    one=sub.add_parser('one'); one.add_argument('file')
    batch=sub.add_parser('batch'); batch.add_argument('file')
    sub.add_parser('replay-failed')
    a=ap.parse_args(argv); store=InMemoryDraftEventStore(); p=DraftEventProcessor(store)
    if a.cmd=='one': show(p.process(event_from_json(json.loads(Path(a.file).read_text()))))
    elif a.cmd=='batch':
        for x in json.loads(Path(a.file).read_text()): show(p.process(event_from_json(x)))
    else:
        for r in p.replay_failed(): show(r)
if __name__=='__main__': main()
